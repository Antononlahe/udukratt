import argparse
import hashlib
import json
import random
from pathlib import Path


def read(path):
    with open(path) as fh:
        for line in fh:
            yield json.loads(line)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", nargs="+", required=True, help="source=path[:limit] in cumulative order")
    ap.add_argument("--val", type=int, default=10_000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--outdir", required=True)
    a = ap.parse_args()
    rows, seen = [], set()
    for spec in a.inputs:
        name, _, rest = spec.partition("=")
        path, _, limit = rest.partition(":")
        n = 0
        for r in read(path):
            h = hashlib.sha1(r["text"].encode()).hexdigest()
            if h in seen:
                continue
            seen.add(h)
            r["mix"] = name
            rows.append(r)
            n += 1
            if limit and n >= int(limit):
                break
        print(f"{name}: {n}")
    random.Random(a.seed).shuffle(rows)
    out = Path(a.outdir)
    out.mkdir(parents=True, exist_ok=True)
    for split, chunk in (("val", rows[: a.val]), ("train", rows[a.val:])):
        with open(out / f"{split}.jsonl", "w") as fh:
            for r in chunk:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(split, len(chunk))


if __name__ == "__main__":
    main()
