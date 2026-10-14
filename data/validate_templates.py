import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from et.deterministic import detect  # noqa: E402
from et.morph import CASES  # noqa: E402
from et.synth import CASED_SLOTS, KEEP_SLOTS, PERSON_PARTS, PERSON_SLOTS, PRIVATE_SLOTS, PUBLIC_SLOTS  # noqa: E402

LANGS = {"et", "et_public", "ru", "en", "mixed"}
SLOT = re.compile(r"\{([^{}]*)\}")
LONG_DIGITS = re.compile(r"\d[\d ]{4,}\d")


def check(rec, names):
    text, lang = rec.get("text", ""), rec.get("lang")
    if lang not in LANGS:
        return f"bad lang {lang!r}"
    if not 15 <= len(text) <= 1500:
        return "length"
    if text.count("{") != text.count("}"):
        return "unbalanced braces"
    private = 0
    for raw in SLOT.findall(text):
        name, _, case = raw.partition(":")
        base, _, part = name.partition(".")
        if base in PERSON_SLOTS:
            if part not in PERSON_PARTS:
                return f"bad person part {raw}"
            private += 1
        elif part:
            return f"part on non-person slot {raw}"
        elif base in PRIVATE_SLOTS:
            private += 1
        elif base not in KEEP_SLOTS | PUBLIC_SLOTS:
            return f"unknown slot {raw}"
        if case and (base not in CASED_SLOTS or case not in CASES or lang not in ("et", "et_public", "mixed")):
            return f"bad case {raw}"
    if lang == "et_public" and private:
        return "private slot in et_public"
    if lang != "et_public" and not private:
        return "no private slot"
    bare = SLOT.sub(" X ", text)
    if detect(bare):
        return "raw structured PII outside slots"
    if LONG_DIGITS.search(bare):
        return "raw digit run outside slots"
    for i, w in enumerate(re.findall(r"[\w'-]+", bare)):
        if i and w[:1].isupper() and w in names:
            return f"possible raw name {w!r}"
    return None


def skeleton(text):
    return re.sub(r"\s+", " ", SLOT.sub("{}", text.lower())).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inputs", nargs="+")
    ap.add_argument("--lexicon", default=str(ROOT / "lexicon/lexicon.json"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--rejects")
    a = ap.parse_args()
    lex = json.load(open(a.lexicon))["names"]
    names = {n for k in ("given_est", "given_rus", "given_cyr_m", "given_cyr_f") for sp in ("train", "heldout") for n in lex[k][sp]}
    seen, reasons, kept = set(), Counter(), Counter()
    rej = open(a.rejects, "w") if a.rejects else None
    with open(a.out, "w") as out:
        for path in a.inputs:
            for ln, line in enumerate(open(path), 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    why = check(rec, names)
                except (json.JSONDecodeError, AttributeError):
                    rec, why = {"raw": line}, "invalid json"
                if why is None:
                    sk = skeleton(rec["text"])
                    why = "duplicate" if sk in seen else None
                    seen.add(sk)
                if why:
                    reasons[why.split(" {")[0].split(" '")[0]] += 1
                    if rej:
                        rej.write(json.dumps({"file": path, "line": ln, "reason": why, **rec}, ensure_ascii=False) + "\n")
                    continue
                kept[rec["lang"]] += 1
                out.write(json.dumps({"lang": rec["lang"], "text": rec["text"], "scenario": rec.get("scenario")}, ensure_ascii=False) + "\n")
    print("kept", dict(kept), "total", sum(kept.values()))
    print("rejected", dict(reasons.most_common()))


if __name__ == "__main__":
    main()
