import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tokenizers import BertWordPieceTokenizer, Tokenizer  # noqa: E402

from et.deterministic import detect  # noqa: E402
from et.normalize import model_view  # noqa: E402

SPECIAL = ["[PAD]", "[UNK]", "[CLS]", "[SEP]", "[MASK]"]


def is_single(piece: str) -> bool:
    core = piece[2:] if piece.startswith("##") else piece
    return len(core) == 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vocab", required=True)
    ap.add_argument("--corpus", nargs="+", required=True)
    ap.add_argument("--target", type=int, default=19_730)
    ap.add_argument("--min-freq", type=int, default=2)
    ap.add_argument("--outdir", required=True)
    a = ap.parse_args()
    vocab = [l.rstrip("\n") for l in open(a.vocab)]
    tok = BertWordPieceTokenizer(a.vocab, lowercase=True, strip_accents=True)
    freq = Counter()
    for path in a.corpus:
        for line in open(path):
            text = json.loads(line)["text"]
            view = model_view(text, [(d.start, d.end, d.label) for d in detect(text)])[0]
            freq.update(tok.encode(view, add_special_tokens=False).tokens)
    keep = {p for p in vocab if p in SPECIAL or is_single(p)}
    budget = max(0, a.target - len(keep))
    ranked = [p for p, c in freq.most_common() if c >= a.min_freq and p not in keep]
    keep.update(ranked[:budget])
    old_ids = [i for i, p in enumerate(vocab) if p in keep]
    out = Path(a.outdir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "vocab.txt").write_text("\n".join(vocab[i] for i in old_ids) + "\n")
    json.dump(old_ids, open(out / "keep_ids.json", "w"))
    BertWordPieceTokenizer(str(out / "vocab.txt"), lowercase=True, strip_accents=True).save(str(out / "tokenizer.json"))
    covered = sum(c for p, c in freq.items() if p in keep) / max(1, sum(freq.values()))
    print(f"kept {len(old_ids)} of {len(vocab)} (singles {sum(map(is_single, keep))}), token coverage {covered:.4%}")
    t = Tokenizer.from_file(str(out / "tokenizer.json"))
    probe = "Jüri Mägi elab Pärnu mnt 12-5, Tallinn. Елена Смирнова"
    print(t.encode(fold := model_view(probe, ())[0]).tokens, fold)


if __name__ == "__main__":
    main()
