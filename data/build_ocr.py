import argparse
import io
import json
import random
import re
import subprocess
import sys
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "data"))

from et.values import Sampler  # noqa: E402

FONTS = ["DejaVuSans.ttf", "DejaVuSerif.ttf", "DejaVuSansMono.ttf", "DejaVuSansCondensed.ttf"]
FORMS = {
    "AVALDUS": ["Töötukassale", ("Ees- ja perekonnanimi", "p1"), ("Isikukood", "ik1"), ("Elukoha aadress", "addr"),
                ("Telefon", "phone"), ("E-post", "email"), ("Arvelduskonto (IBAN)", "iban"),
                "Palun registreerida mind töötuna alates {date}.", ("Kuupäev", "date"), ("Allkiri", "sig")],
    "TAOTLUS": ["Sotsiaalkindlustusametile", ("Taotleja nimi", "p1"), ("Isikukood", "ik1"), ("Postiaadress", "addr"),
                ("Kontaktandmed", "phone"), ("Lapse nimi", "p3"), ("Lapse isikukood", "ik3"),
                ("Toetuse saaja konto", "iban"), ("Kuupäev", "date")],
    "VOLIKIRI": ["Mina, allakirjutanu", ("Volitaja", "p1"), ("Isikukood", "ik1"), ("Volitatu", "p2"), ("Isikukood", "ik2"),
                 ("Isikut tõendava dokumendi nr", "doc"), "Volitan esindama mind kõigis toimingutes.", ("Kuupäev", "date")],
    "KAART": ["EESTI VABARIIK / REPUBLIC OF ESTONIA", ("PEREKONNANIMI / SURNAME", "p1.s"), ("EESNIMED / GIVEN NAMES", "p1.g"),
              ("ISIKUKOOD / PERSONAL CODE", "ik1"), ("DOKUMENDI NR / DOCUMENT NO", "doc"), ("KEHTIV KUNI / DATE OF EXPIRY", "date")],
}


def fold(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s.lower()) if unicodedata.category(c) != "Mn")


def values(s: Sampler, rng):
    p1, p2 = s.person(script="latin"), s.person(script="latin")
    p3 = s.person(origin=p1.origin, script="latin", surname=p1.surname)
    stem, full, abbr = s.street()
    city, prefix = s.city()
    bld, apt = s.building(), s.apartment()
    addr = [(f"{stem} {abbr}", "STREET_NAME"), (" ", None), (bld, "BUILDING_NUMBER"), ("-", None), (apt, "SECONDARY_ADDRESS"),
            (", ", None), (s.zip(prefix), "ZIP_CODE"), (" ", None), (city, "CITY")]
    name = lambda p: [(p.given, "GIVEN_NAME"), (" ", None), (p.surname, "SURNAME")]
    return {"p1": name(p1), "p2": name(p2), "p3": name(p3), "p1.s": [(p1.surname.upper(), "SURNAME")],
            "p1.g": [(p1.given.upper(), "GIVEN_NAME")], "ik1": [(s.isikukood(p1), "ISIKUKOOD")],
            "ik2": [(s.isikukood(p2), "ISIKUKOOD")], "ik3": [(s.isikukood(p3), "ISIKUKOOD")], "addr": addr,
            "phone": [(s.phone(), "PHONE")], "email": [(s.email(p1), "EMAIL")], "iban": [(s.iban(), "BANK_ACCOUNT")],
            "doc": [(s.id_doc(), "GOVERNMENT_ID")], "date": [(s.date_text(), None)], "sig": [(rng.choice(["/allkirjastatud digitaalselt/", "", p1.surname[:3] + "~"]), None)]}


def render(lines, rng):
    font_name = rng.choice(FONTS)
    size = rng.randint(22, 34)
    font = ImageFont.truetype(f"/usr/share/fonts/truetype/dejavu/{font_name}", size)
    img = Image.new("L", (1500, 120 + len(lines) * int(size * 2.1)), 255)
    d = ImageDraw.Draw(img)
    y = 60
    for line in lines:
        d.text((70, y), line, font=font, fill=rng.randint(0, 60))
        if rng.random() < 0.3:
            d.line((60, y + size + 8, 1440, y + size + 8), fill=150, width=1)
        y += int(size * 2.1)
    return img


def degrade(img, rng):
    img = img.rotate(rng.uniform(-1.8, 1.8), expand=True, fillcolor=255)
    if rng.random() < 0.7:
        img = img.filter(ImageFilter.GaussianBlur(rng.uniform(0.2, 1.3)))
    scale = rng.uniform(0.45, 0.9)
    w, h = img.size
    img = img.resize((int(w * scale), int(h * scale))).resize((w, h))
    px = img.load()
    for _ in range(int(w * h * rng.uniform(0, 0.004))):
        px[rng.randrange(w), rng.randrange(h)] = rng.choice((0, 255))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=rng.randint(20, 70))
    return Image.open(io.BytesIO(buf.getvalue()))


def ocr(img, psm):
    buf = io.BytesIO()
    img.save(buf, "PNG")
    r = subprocess.run(["tesseract", "-", "stdout", "-l", "est", "--psm", str(psm)], input=buf.getvalue(), capture_output=True)
    return r.stdout.decode("utf-8", "ignore")


def align(text, golds, threshold):
    words = [(m.start(), m.end()) for m in re.finditer(r"\S+", text)]
    used, spans, missed = [], [], 0
    for value, label in golds:
        exact = next((m for m in re.finditer(r"(?<![\w])" + re.escape(value) + r"(?![\w])", text)
                      if not any(m.start() < ub and ua < m.end() for ua, ub in used)), None)
        if exact:
            used.append((exact.start(), exact.end()))
            spans.append({"start": exact.start(), "end": exact.end(), "label": label})
            continue
        n = max(1, len(value.split()))
        best = (0.0, None)
        for i in range(len(words)):
            for k in (n - 1, n, n + 1):
                if k < 1 or i + k > len(words):
                    continue
                a, b = words[i][0], words[i + k - 1][1]
                cand = text[a:b].strip(".,;:()")
                a = a + text[a:b].find(cand) if cand else a
                b = a + len(cand)
                if any(a < ub and ua < b for ua, ub in used):
                    continue
                r = SequenceMatcher(None, fold(cand), fold(value)).ratio()
                if r > best[0]:
                    best = (r, (a, b))
        if best[1] and best[0] >= threshold:
            used.append(best[1])
            spans.append({"start": best[1][0], "end": best[1][1], "label": label})
        else:
            missed += 1
    return sorted(spans, key=lambda s: s["start"]), missed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20000)
    ap.add_argument("--lexicon", default=str(ROOT / "lexicon/lexicon.json"))
    ap.add_argument("--threshold", type=float, default=0.72)
    ap.add_argument("--save-images")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rng = random.Random(a.seed)
    s = Sampler(a.lexicon, "train", a.seed)
    tot_missed = tot_gold = 0
    with open(a.out, "w") as out:
        for i in range(a.n):
            form = rng.choice(list(FORMS))
            vals = values(s, rng)
            lines, golds = [form], []
            for item in FORMS[form]:
                if isinstance(item, str):
                    lines.append(item.replace("{date}", vals["date"][0][0]))
                    continue
                label, key = item
                value = "".join(t for t, _ in vals[key])
                golds += [(t, lab) for t, lab in vals[key] if lab]
                lines.append(f"{label}: {value}" if rng.random() < 0.7 else label)
                if not lines[-1].endswith(value):
                    lines.append(f"    {value}")
            img = degrade(render(lines, rng), rng)
            if a.save_images:
                Path(a.save_images).mkdir(parents=True, exist_ok=True)
                img.save(Path(a.save_images) / f"{i:06d}.jpg")
            text = ocr(img, rng.choice([4, 6]))
            spans, missed = align(text, golds, a.threshold)
            tot_missed += missed
            tot_gold += len(golds)
            out.write(json.dumps({"id": f"ocr:{a.seed}:{i}", "source": "ocr", "lang": "et", "text": text.strip(),
                                  "spans": spans, "public": [], "meta": {"form": form, "missed": missed}}, ensure_ascii=False) + "\n")
    print(f"{a.n} rows, aligned {tot_gold - tot_missed}/{tot_gold} gold values")


if __name__ == "__main__":
    main()
