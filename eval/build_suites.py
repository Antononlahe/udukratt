import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from faker import Faker  # noqa: E402

from et.labels import TO_OPENPII  # noqa: E402
from et.morph import inflect_word  # noqa: E402
from et.normalize import transliterate  # noqa: E402

GOV_MAP = {"PERSON": "PERSON", "EE_PERSONAL_CODE": "SOCIALNUM", "PHONE_NUMBER": "TELEPHONENUM", "EMAIL_ADDRESS": "EMAIL",
           "IBAN_CODE": "IBAN", "EST_ID_DOC": "IDCARDNUM", "CAR_NUMBER": "IDCARDNUM", "IP_ADDRESS": "IP", "URL": "URL",
           "CREDIT_CARD": "CREDITCARDNUMBER", "ORGANIZATION": "ORG", "DATE_TIME": "DATE", "LOCATION": "LOC", "GPE": "LOC"}
GOV_TRAPS_REDACTED_BY_DESIGN = {"3-21-1234"}

TRADITIONS = [
    ("estonian", "et_EE", "est"), ("russian_latin", "ru_RU", "translit"), ("russian_cyrillic", "ru_RU", "cyr"),
    ("ukrainian_latin", "uk_UA", "translit"), ("ukrainian_cyrillic", "uk_UA", "cyr"), ("finnish", "fi_FI", "latin"),
    ("latvian", "lv_LV", "latin"), ("lithuanian", "lt_LT", "latin"), ("anglo", "en_US", "latin"),
    ("hispanic", "es_ES", "latin"), ("germanic", "de_DE", "latin"), ("turkic", "tr_TR", "latin"),
    ("vietnamese", "vi_VN", "latin"), ("japanese", "ja_JP", "native"), ("korean", "ko_KR", "native"),
    ("han_chinese", "zh_CN", "native"), ("hindi", "hi_IN", "native"), ("arabic", "ar_AA", "native"),
]
FAIR_ET = [("Tere, minu nimi on {g} {s}.", "n"), ("Palun saatke otsus {g} {s}.", "all"),
           ("Kas {g} {s} avaldus on menetluses?", "g"), ("Rääkisin eile {g} {s} telefonis.", "kom"),
           ("Nimi: {S} {g}\nVanus: 42", "n")]
FAIR_RU = [("Здравствуйте, меня зовут {g} {s}.", "n"), ("Заявитель: {g} {s}, город Нарва.", "n"),
           ("Пишу за маму, {g} {s}, ей 70 лет.", "n"), ("Можно записаться? {g} {s}", "n"), ("Фамилия: {S}\nИмя: {g}", "n")]


def mask(label, start, value):
    return {"label": label, "start": start, "end": start + len(value), "value": value}


def from_rows(path, language_key):
    out = []
    for i, line in enumerate(open(path)):
        r = json.loads(line)
        pm = [mask(TO_OPENPII.get(s["label"], s["label"]), s["start"], r["text"][s["start"]:s["end"]]) for s in r["spans"]]
        pm += [mask(p["label"], p["start"], r["text"][p["start"]:p["end"]]) for p in r.get("public", [])]
        out.append({"uid": i, "language": language_key(r), "source_text": r["text"], "privacy_mask": pm})
    return out


def gov_chats(cases_py):
    spec = importlib.util.spec_from_file_location("gov_cases", cases_py)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    rows = []
    for i, case in enumerate(mod.DETECTION_CASES):
        text, pm = case["text"], []
        for gold in case["gold"]:
            surface = gold[0]
            occ = gold[2] if len(gold) > 2 else 0
            start = -1
            for _ in range(occ + 1):
                start = text.index(surface, start + 1)
            kind = next((GOV_MAP[e] for e in sorted(gold[1]) if e in GOV_MAP), None)
            if kind == "PERSON":
                toks = list(re.finditer(r"\S+", surface))
                for j, m in enumerate(toks):
                    pm.append(mask("SURNAME" if j == len(toks) - 1 else "GIVENNAME", start + m.start(), m.group()))
            elif kind == "LOC":
                m = re.match(r"^(.*\D)\s+(\d+\w*)$", surface)
                if m:
                    pm.append(mask("STREET", start, m.group(1)))
                    pm.append(mask("BUILDINGNUM", start + m.start(2), m.group(2)))
                else:
                    pm.append(mask("CITY", start, surface))
            elif kind:
                pm.append(mask(kind, start, surface))
        for trap in case["traps"]:
            if trap not in GOV_TRAPS_REDACTED_BY_DESIGN and trap in text:
                pm.append(mask("TRAP", text.index(trap), trap))
        rows.append({"uid": i, "language": case["group"].split(".")[0], "source_text": text, "privacy_mask": pm, "case_id": case["id"]})
    return rows


def fairness(per_tradition):
    rows, uid = [], 0
    for name, loc, mode in TRADITIONS:
        fk = Faker(loc)
        Faker.seed(1234)
        for k in range(per_tradition):
            g, s = (fk.first_name_est(), fk.last_name_est()) if loc == "et_EE" else (fk.first_name(), fk.last_name())
            if mode == "translit":
                g, s = transliterate(g), transliterate(s)
            templates = FAIR_RU if mode == "cyr" else FAIR_ET
            tpl, case = templates[k % len(templates)]
            s_out = inflect_word(s, case) if mode not in ("cyr", "native") else s
            text = tpl.replace("{S}", s.upper()).replace("{g}", g).replace("{s}", s_out)
            pm = []
            gi = text.index(g)
            pm.append(mask("GIVENNAME", gi, g))
            sv = s.upper() if "{S}" in tpl else s_out
            pm.append(mask("SURNAME", text.index(sv), sv))
            rows.append({"uid": uid, "language": name, "source_text": text, "privacy_mask": pm, "case": case})
            uid += 1
    return rows


def write(rows, path):
    with open(path, "w") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"{path}: {len(rows)} rows")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--synth-heldout")
    ap.add_argument("--estner-test")
    ap.add_argument("--gov-cases")
    ap.add_argument("--fairness-per-tradition", type=int, default=125)
    ap.add_argument("--outdir", default=str(ROOT / "eval/data"))
    a = ap.parse_args()
    out = Path(a.outdir)
    out.mkdir(parents=True, exist_ok=True)
    if a.synth_heldout:
        write(from_rows(a.synth_heldout, lambda r: r["lang"]), out / "synth_heldout.jsonl")
    if a.estner_test:
        write(from_rows(a.estner_test, lambda r: "et_news"), out / "estner_test.jsonl")
    if a.gov_cases:
        write(gov_chats(a.gov_cases), out / "gov_chats.jsonl")
    write(fairness(a.fairness_per_tradition), out / "fairness.jsonl")


if __name__ == "__main__":
    main()
