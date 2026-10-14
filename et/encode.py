from .deterministic import detect
from .labels import FALLBACK, LABEL2ID
from .normalize import model_view


class NormalizationDrift(RuntimeError):
    pass


def check_normalizer(tokenizer, probes):
    for p in probes:
        folded = model_view(p, ())[0]
        if tokenizer.normalizer.normalize_str(folded) != folded:
            raise NormalizationDrift(f"tokenizer re-normalizes folded text: {folded!r}")


def model_spans(text, gold, det):
    out = []
    for g in gold:
        if any(d.start < g["end"] and g["start"] < d.end for d in det):
            continue
        label = FALLBACK.get(g["label"], g["label"])
        if label in LABEL2ID.keys() or f"B-{label}" in LABEL2ID:
            out.append((g["start"], g["end"], label))
    return sorted(out)


def encode(row, tokenizer, max_len=512, stride=128, translit=True, prefilter=True):
    text = row["text"]
    det = detect(text) if prefilter else []
    view, rs, re_ = model_view(text, [(d.start, d.end, d.label) for d in det], translit)
    gold = model_spans(text, row.get("spans", []), det)
    enc = tokenizer.encode(view, add_special_tokens=False)
    labels, seen = [], set()
    for (a, b) in enc.offsets:
        if b <= a:
            labels.append(LABEL2ID["O"])
            continue
        ra, rb = rs[a], re_[b - 1]
        hit = next((g for g in gold if g[0] < rb and ra < g[1]), None)
        if hit is None:
            labels.append(LABEL2ID["O"])
            continue
        prefix = "I" if hit in seen else "B"
        seen.add(hit)
        labels.append(LABEL2ID[f"{prefix}-{hit[2]}"])
    cls, sep = tokenizer.token_to_id("[CLS]"), tokenizer.token_to_id("[SEP]")
    body = max_len - 2
    ids = enc.ids
    chunks, start = [], 0
    while True:
        piece_ids, piece_lab = ids[start:start + body], labels[start:start + body]
        chunks.append({"input_ids": [cls] + piece_ids + [sep], "labels": [-100] + piece_lab + [-100]})
        if start + body >= len(ids):
            break
        start += body - stride
    return chunks
