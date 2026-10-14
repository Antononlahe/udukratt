import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "data"))

from et.synth import Generator  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=250_000)
    ap.add_argument("--split", default="train", choices=["train", "heldout"])
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--lexicon", default=str(ROOT / "lexicon/lexicon.json"))
    ap.add_argument("--templates", nargs="*", default=[])
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    g = Generator(a.lexicon, a.split, a.seed, a.templates)
    with open(a.out, "w") as fh:
        for i in range(a.n):
            r = g.row()
            fh.write(json.dumps({"id": f"synth:{a.split}:{a.seed}:{i}", "source": "synthetic", "lang": r.meta["lang"],
                                 "text": r.text, "spans": r.spans, "public": r.public, "meta": r.meta}, ensure_ascii=False) + "\n")
    print(a.n, "rows ->", a.out)


if __name__ == "__main__":
    main()
