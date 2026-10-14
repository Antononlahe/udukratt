import argparse
import json
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "data"))

from estnltk.vabamorf.morf import Vabamorf  # noqa: E402

from et.morph import CASES, inflect_word  # noqa: E402
from et.values import Sampler  # noqa: E402
from seed import CITIES, VALDS, VILLAGES  # noqa: E402

NO_SPACE_BEFORE = re.compile(r"^[.,!?:;)\]%”“»]$")
NO_SPACE_AFTER = re.compile(r"^[(\[„«]$")
STREET_SUFFIX = re.compile(r"(tänav|tn|mnt|maantee|puiestee|pst|tee|talu)\w*$", re.I)
FORM_TO_CASE = {v: k for k, v in CASES.items()}
PLACES = set(CITIES) | set(VALDS) | set(VILLAGES) | {"Tallinn", "Lasnamäe", "Mustamäe", "Nõmme", "Pirita", "Kopli", "Kristiine", "Haabersti"}


class Analyzer:
    def __init__(self):
        self.vm = Vabamorf.instance()
        self.cache = {}

    def best(self, word):
        if word not in self.cache:
            res = self.vm.analyze([word], disambiguate=False, guess=True, propername=True)[0]["analysis"]
            hs = [a for a in res if a["partofspeech"] == "H"] or res
            a = hs[0] if hs else {"root": word, "form": "sg n"}
            self.cache[word] = (a["root"].replace("_", "").replace("=", ""), a["form"])
        return self.cache[word]


def entities(words):
    ents, cur = [], None
    for i, w in enumerate(words):
        tag = w["ner_1"]
        if tag.startswith("B-") or (tag.startswith("I-") and (cur is None or cur[0] != tag[2:])):
            if cur:
                ents.append(cur)
            cur = [tag[2:], i, i + 1]
        elif tag.startswith("I-"):
            cur[2] = i + 1
        else:
            if cur:
                ents.append(cur)
            cur = None
    if cur:
        ents.append(cur)
    return ents


def relabel(words, an: Analyzer, sampler: Sampler, rng: random.Random, rehydrate: float, given_set):
    surface = [w["word"] for w in words]
    labels = [None] * len(words)
    public = [None] * len(words)
    group = [None] * len(words)
    for gid, (kind, a, b) in enumerate(entities(words)):
        for i in range(a, b):
            group[i] = gid
        if kind == "PER":
            toks = surface[a:b]
            if rng.random() < rehydrate:
                p = sampler.person(origin="est" if rng.random() < 0.7 else None, script="latin")
                root, form = an.best(toks[-1])
                case = FORM_TO_CASE.get(form, "n")
                if len(toks) == 1:
                    is_given = root in given_set
                    new = [inflect_word(p.given if is_given else p.surname, case, rng.choice)]
                else:
                    gs = p.given.split(" ")
                    while len(gs) < len(toks) - 1:
                        gs.append(sampler.person(origin=p.origin, script="latin").given.split(" ")[0])
                    new = gs[: len(toks) - 1] + [inflect_word(p.surname, case, rng.choice)]
                surface[a:b] = new
            if b - a == 1:
                root, _ = an.best(surface[a])
                labels[a] = "GIVEN_NAME" if root in given_set else "SURNAME"
            else:
                for i in range(a, b - 1):
                    labels[i] = "GIVEN_NAME"
                labels[b - 1] = "SURNAME"
        elif kind == "GPE":
            roots = {an.best(t)[0] for t in surface[a:b]}
            if roots & PLACES or " ".join(surface[a:b]) in PLACES:
                for i in range(a, b):
                    labels[i] = "CITY"
        elif kind == "LOC" and STREET_SUFFIX.search(surface[b - 1]):
            for i in range(a, b):
                labels[i] = "STREET_NAME"
        elif kind in ("ORG", "DATE", "MONEY"):
            for i in range(a, b):
                public[i] = {"MONEY": "AMOUNT"}.get(kind, kind)
    return surface, labels, public, group


def detok(surface, labels, public, group):
    text, spans, pubs = "", [], []
    for i, w in enumerate(surface):
        if i and not NO_SPACE_BEFORE.match(w) and not NO_SPACE_AFTER.match(surface[i - 1]):
            text += " "
        start = len(text)
        text += w
        for coll, labs in ((spans, labels), (pubs, public)):
            lab = labs[i]
            if lab is None:
                continue
            if coll and i and labs[i - 1] == lab and group[i - 1] == group[i]:
                coll[-1]["end"] = len(text)
            else:
                coll.append({"start": start, "end": len(text), "label": lab})
    return text, spans, pubs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", nargs="+", required=True)
    ap.add_argument("--lexicon", default=str(ROOT / "lexicon/lexicon.json"))
    ap.add_argument("--split", default="train")
    ap.add_argument("--rehydrate", type=float, default=0.6)
    ap.add_argument("--max-words", type=int, default=90)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rng = random.Random(a.seed)
    sampler = Sampler(a.lexicon, a.split, a.seed)
    given_set = set(sampler.lex["names"]["given_est"]["train"]) | set(sampler.lex["names"]["given_est"]["heldout"])
    an = Analyzer()
    n = 0
    with open(a.out, "w") as out:
        for path in a.inputs:
            for di, doc in enumerate(json.load(open(path))["documents"]):
                buf = []
                sents = doc["sentences"]
                for si, s in enumerate(sents):
                    buf.extend(s["words"])
                    if len(buf) >= a.max_words or si == len(sents) - 1:
                        text, spans, pubs = detok(*relabel(buf, an, sampler, rng, a.rehydrate, given_set))
                        out.write(json.dumps({"id": f"estner:{Path(path).stem}:{di}:{si}", "source": "estner", "lang": "et",
                                              "text": text, "spans": spans, "public": pubs}, ensure_ascii=False) + "\n")
                        n += 1
                        buf = []
    print(n, "rows")


if __name__ == "__main__":
    main()
