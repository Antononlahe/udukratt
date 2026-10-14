import argparse
import json
import random
import re
import sys
import time
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "data"))

from et.morph import inflect_word  # noqa: E402
from et.values import Sampler  # noqa: E402

API = "https://www.riigiteataja.ee/public-api/api/v1/kohtuteave/kohtulahendid/{id}/file"
SUFFIX_CASE = {"": "n", "i": "g", "a": "g", "d": "p", "t": "p", "le": "all", "l": "ad", "lt": "abl", "ga": "kom",
               "ks": "tr", "ni": "ter", "na": "es", "ta": "ab", "s": "in", "st": "el", "sse": "ill", "ile": "all",
               "il": "ad", "ilt": "abl", "iga": "kom", "is": "in", "ist": "el", "isse": "ill", "ni": "ter"}
PSEUDO = re.compile(r"(?<![\w§.])([A-ZÕÄÖÜ])(?:-?(" + "|".join(sorted((k for k in SUFFIX_CASE if k), key=len, reverse=True)) + r"))?(?![\w.])")
INITIALS = re.compile(r"(?<!\w)([A-ZÕÄÖÜ])\. ?([A-ZÕÄÖÜ])\.(?!\w)")
MASKED = re.compile(r"(?<!\w)[Xx]{3,}(?:[ ,.-]+[Xx]{2,})*")
NOT_NAME_BEFORE = re.compile(r"(?:§|lg|lõige|lõike|p|punkt|punkti|nr|osa|art|lisa|tabel|klass|kategooria)\s*$", re.I)
HEADER = re.compile(r"^(Kohus|Kohtunik|Kohtukoosseis|Kohtuasja number|Tsiviilasja number|Haldusasja number|Kriminaalasja number|Määruse tegemise|Otsuse tegemise|Istungi)", re.M)
CONTEXT = [(re.compile(r"isikukood\w*\W*$", re.I), "ik"), (re.compile(r"(elukoh\w*|aadress\w*)\W*$", re.I), "addr"),
           (re.compile(r"e-?(post|mail)\w*\W*$", re.I), "email"), (re.compile(r"tel(efon)?\w*\W*$", re.I), "phone")]


def fetch(ids, outdir: Path, delay: float):
    outdir.mkdir(parents=True, exist_ok=True)
    for i in ids:
        dst = outdir / f"{i}.pdf"
        if dst.exists():
            continue
        req = urllib.request.Request(API.format(id=i), headers={"User-Agent": "rampart-et research (contact in README)"})
        with urllib.request.urlopen(req, timeout=60) as r:
            dst.write_bytes(r.read())
        time.sleep(delay)


def read_text(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        from pypdf import PdfReader
        text = "\n".join(p.extract_text() or "" for p in PdfReader(str(path)).pages)
    else:
        text = path.read_text(encoding="utf-8", errors="ignore")
    text = re.sub(r"-\n(?=[a-zõäöü])", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n{2,}", "\n\n", text)


def pseudonym_letters(text: str):
    counts = Counter()
    for m in PSEUDO.finditer(text):
        if not NOT_NAME_BEFORE.search(text[max(0, m.start() - 12):m.start()]):
            counts[m.group(1)] += 1
    return {k for k, c in counts.items() if c >= 2}


class Rehydrator:
    def __init__(self, sampler: Sampler, rng: random.Random):
        self.s, self.rng = sampler, rng

    def document(self, text: str):
        letters = pseudonym_letters(text)
        people = {}
        pieces, pos = [], 0
        events = []
        for m in INITIALS.finditer(text):
            events.append((m.start(), m.end(), "initials", m))
        for m in PSEUDO.finditer(text):
            if m.group(1) in letters and not NOT_NAME_BEFORE.search(text[max(0, m.start() - 12):m.start()]):
                events.append((m.start(), m.end(), "letter", m))
        for m in MASKED.finditer(text):
            events.append((m.start(), m.end(), "masked", m))
        events.sort(key=lambda e: (e[0], -e[1]))
        for start, end, kind, m in events:
            if start < pos:
                continue
            pieces.append((text[pos:start], None))
            key = m.group(0).replace(" ", "") if kind == "initials" else m.group(1) if kind == "letter" else None
            if kind in ("initials", "letter"):
                p = people.setdefault(key, self.s.person(origin=self.rng.choice(["est", "est", "rus"]), script="latin"))
                case = SUFFIX_CASE.get(m.group(2) or "", "n") if kind == "letter" else "n"
                pieces += [(p.given, "GIVEN_NAME"), (" ", None), (inflect_word(p.surname, case, self.rng.choice), "SURNAME")]
            else:
                ctx = text[max(0, start - 30):start]
                what = next((w for rx, w in CONTEXT if rx.search(ctx)), None)
                if what == "ik":
                    pieces.append((self.s.isikukood(), "ISIKUKOOD"))
                elif what == "phone":
                    pieces.append((self.s.phone(), "PHONE"))
                elif what == "email":
                    pieces.append((self.s.email(self.s.person()), "EMAIL"))
                elif what == "addr":
                    stem, _, abbr = self.s.street()
                    city, prefix = self.s.city()
                    pieces += [(f"{stem} {abbr}", "STREET_NAME"), (" ", None), (self.s.building(), "BUILDING_NUMBER"),
                               (", ", None), (city, "CITY")]
                else:
                    pieces.append((m.group(0), None))
            pos = end
        pieces.append((text[pos:], None))
        out, spans = "", []
        for t, lab in pieces:
            if lab:
                spans.append({"start": len(out), "end": len(out) + len(t), "label": lab})
            out += t
        return out, spans


def chunks(text, spans, max_words, keep_empty, rng, names):
    paras = [(m.start(), m.end()) for m in re.finditer(r"[^\n]+(?:\n(?!\n)[^\n]+)*", text)]
    buf_start, words = None, 0
    blocks = []
    for a, b in paras:
        if HEADER.match(text[a:b]):
            continue
        buf_start = a if buf_start is None else buf_start
        words += len(text[a:b].split())
        if words >= max_words:
            blocks.append((buf_start, b))
            buf_start, words = None, 0
    if buf_start is not None:
        blocks.append((buf_start, paras[-1][1]))
    for a, b in blocks:
        inner = [{"start": s["start"] - a, "end": s["end"] - a, "label": s["label"]} for s in spans if a <= s["start"] and s["end"] <= b]
        chunk = text[a:b]
        labelled = {chunk[s["start"]:s["end"]] for s in inner}
        stray = [w for w in re.findall(r"(?<=\s)[A-ZÕÄÖÜ][a-zõäöü]+", chunk) if w in names and w not in labelled]
        if stray:
            continue
        if inner or rng.random() < keep_empty:
            yield chunk, inner


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch-ids")
    ap.add_argument("--indir", required=True)
    ap.add_argument("--delay", type=float, default=3.0)
    ap.add_argument("--lexicon", default=str(ROOT / "lexicon/lexicon.json"))
    ap.add_argument("--max-words", type=int, default=110)
    ap.add_argument("--keep-empty", type=float, default=0.1)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    indir = Path(a.indir)
    if a.fetch_ids:
        fetch([l.strip() for l in open(a.fetch_ids) if l.strip()], indir, a.delay)
    rng = random.Random(a.seed)
    sampler = Sampler(a.lexicon, "train", a.seed)
    names = {n for k in ("given_est", "given_rus") for sp in ("train", "heldout") for n in sampler.lex["names"][k][sp]}
    reh = Rehydrator(sampler, rng)
    n = 0
    with open(a.out, "w") as out:
        for path in sorted(indir.glob("*")):
            if path.suffix.lower() not in (".pdf", ".txt"):
                continue
            text, spans = reh.document(read_text(path))
            for i, (chunk, inner) in enumerate(chunks(text, spans, a.max_words, a.keep_empty, rng, names)):
                out.write(json.dumps({"id": f"courts:{path.stem}:{i}", "source": "courts", "lang": "et", "text": chunk,
                                      "spans": inner, "public": []}, ensure_ascii=False) + "\n")
                n += 1
    print(n, "rows")


if __name__ == "__main__":
    main()
