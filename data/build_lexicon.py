import argparse
import sys
import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from faker import Faker

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from seed import COUNTIES, VALDS, VILLAGES, STREET_STEMS

NAME_RE = re.compile(r"^[A-ZÕÄÖÜŠŽ][a-zõäöüšžA-ZÕÄÖÜŠŽ'-]+$")


def faker_names():
    out = {"given_est": set(), "sur_est": set(), "given_rus": set(), "sur_rus": set(), "given_other": set(), "sur_other": set(),
           "given_cyr_m": set(), "given_cyr_f": set(), "sur_cyr_m": set(), "sur_cyr_f": set()}
    from faker.providers.person.et_EE import Provider as Et
    out["given_est"].update(Et.first_names_est)
    out["sur_est"].update(Et.last_names_est)
    out["given_rus"].update(Et.first_names_rus)
    out["sur_rus"].update(Et.last_names_rus)
    from et.normalize import transliterate
    for loc in ("ru_RU", "uk_UA"):
        f = Faker(loc)
        for i in range(4000):
            Faker.seed(i)
            out["given_cyr_m"].add(f.first_name_male())
            out["given_cyr_f"].add(f.first_name_female())
            out["sur_cyr_m"].add(f.last_name_male())
            out["sur_cyr_f"].add(f.last_name_female())
    for k in ("given_cyr_m", "given_cyr_f"):
        out["given_rus"].update(transliterate(x) for x in out[k])
    for k in ("sur_cyr_m", "sur_cyr_f"):
        out["sur_rus"].update(transliterate(x) for x in out[k])
    for loc in ("fi_FI", "lv_LV", "lt_LT", "en_US", "de_DE", "pl_PL", "en_GB", "tr_TR"):
        f = Faker(loc)
        for i in range(800):
            Faker.seed(i)
            out["given_other"].add(f.first_name())
            out["sur_other"].add(f.last_name())
    return out


def harvest_estner(paths):
    from estnltk.vabamorf.morf import Vabamorf
    vm = Vabamorf.instance()
    mentions = Counter()
    for p in paths:
        for d in json.load(open(p))["documents"]:
            for s in d["sentences"]:
                cur = []
                for w in s["words"] + [{"word": "", "ner_1": "O"}]:
                    t = w["ner_1"]
                    if t == "I-PER" and cur:
                        cur.append(w["word"])
                        continue
                    if len(cur) >= 2:
                        mentions[tuple(cur)] += 1
                    cur = [w["word"]] if t == "B-PER" else []
    given, sur = Counter(), Counter()
    lasts = sorted({m[-1] for m in mentions})
    lemmas = {}
    surfaces = set(lasts)
    for res in vm.analyze(lasts, disambiguate=False, guess=True, propername=True):
        hs = [a for a in res["analysis"] if a["partofspeech"] == "H"]
        if any(a["form"] == "sg n" and a["root"].replace("_", "").replace("=", "") == res["text"] for a in hs):
            lemmas[res["text"]] = res["text"]
            continue
        roots = [a["root"].replace("_", "").replace("=", "") for a in hs]
        known = [r for r in roots if r in surfaces]
        lemmas[res["text"]] = known[0] if known else None
    for m, c in mentions.items():
        for g in m[:-1]:
            if NAME_RE.match(g):
                given[g] += c
        s = lemmas.get(m[-1])
        if s and NAME_RE.match(s):
            sur[s[:1].upper() + s[1:]] += c
    return given, sur


def load_ads(path):
    streets, villages = Counter(), Counter()
    with open(path, encoding="utf-8-sig") as fh:
        sample = fh.read(4096)
        fh.seek(0)
        reader = csv.DictReader(fh, dialect=csv.Sniffer().sniff(sample, delimiters=";,\t"))
        for row in reader:
            keys = {k.upper(): v for k, v in row.items() if k}
            s = keys.get("TASE5_NIMETUS") or keys.get("TASE5") or ""
            v = keys.get("TASE3_NIMETUS") or keys.get("TASE3") or ""
            if s:
                streets[s.strip()] += 1
            if v:
                villages[v.strip()] += 1
    return streets, villages


def split_of(name: str, salt: str) -> str:
    return "heldout" if int(hashlib.md5(f"{salt}:{name}".encode()).hexdigest(), 16) % 10 == 0 else "train"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--estner", nargs="*", default=[])
    ap.add_argument("--ads-csv")
    ap.add_argument("--wikidata-json")
    ap.add_argument("--out", default="lexicon/lexicon.json")
    a = ap.parse_args()

    names = faker_names()
    if a.estner:
        g, s = harvest_estner(a.estner)
        names["given_est"].update(x for x, c in g.items() if c >= 1)
        names["sur_est"].update(x for x, c in s.items() if c >= 1)
    if a.wikidata_json:
        wd = json.load(open(a.wikidata_json))
        names["given_est"].update(wd.get("given", []))
        names["sur_est"].update(wd.get("family", []))

    streets = {f"{s}": 1 for s in STREET_STEMS}
    villages = set(VILLAGES)
    if a.ads_csv:
        st, vi = load_ads(a.ads_csv)
        streets.update({k: v for k, v in st.items()})
        villages.update(vi)

    lex = {"names": {}, "streets": {}, "villages": {}}
    for key, vals in names.items():
        vals = sorted(v for v in vals if v and len(v) > 1)
        lex["names"][key] = {sp: [v for v in vals if split_of(v, key) == sp] for sp in ("train", "heldout")}
    st = sorted(streets)
    lex["streets"] = {sp: [v for v in st if split_of(v, "street") == sp] for sp in ("train", "heldout")}
    vi = sorted(villages)
    lex["villages"] = {sp: [v for v in vi if split_of(v, "village") == sp] for sp in ("train", "heldout")}
    lex["counties"] = COUNTIES
    lex["valds"] = VALDS
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    json.dump(lex, open(a.out, "w"), ensure_ascii=False, indent=1)
    for k, v in lex["names"].items():
        print(k, len(v["train"]), len(v["heldout"]))
    print("streets", len(lex["streets"]["train"]), len(lex["streets"]["heldout"]))


if __name__ == "__main__":
    main()
