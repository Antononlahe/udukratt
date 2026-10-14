import json, sys, numpy as np
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2] / "webapp/test"))
import ref
from ref import load, detect, model_view, decide, snap, ID2LABEL, NEVER, BODY
R = ref.ROOT
mdir = sys.argv[1] if len(sys.argv) > 1 else "work4/rampart-et"
tok, sess = load(mdir)
rows = [json.loads(l) for l in open(R / "work4/mix/val.jsonl")] + [json.loads(l) for l in open(R / "work4/docs_dev.jsonl")][:500]
TAUS = [None, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
cache = []
for r in rows:
    t = r["text"]; det = detect(t)
    view, rs, re_ = model_view(t, [(d.start, d.end, d.label) for d in det], True)
    enc = tok.encode(view, add_special_tokens=False); ids = enc.ids
    L = []
    for st in range(0, len(ids), BODY):
        a = np.array([[2] + ids[st:st + BODY] + [3]], dtype=np.int64)
        L.append(sess.run(None, {"input_ids": a, "attention_mask": np.ones_like(a), "token_type_ids": np.zeros_like(a)})[0][0][1:-1])
    cache.append((t, det, rs, re_, enc.offsets, np.concatenate(L) if L else np.zeros((0, 35)), r["spans"]))
res = {}
for tau in TAUS:
    tp = fn = fp = 0
    for t, det, rs, re_, offs, lg, gold in cache:
        ents, cur = [], None
        for (a, b), x in zip(offs, lg):
            lab = ID2LABEL[decide(x, tau)]
            if lab == "O" or b <= a: cur = None; continue
            p, ty = lab.split("-", 1); s, e = rs[a], re_[b - 1]
            if p == "I" and cur and cur[2] == ty: cur[1] = e
            else: cur = [s, e, ty]; ents.append(cur)
        ents = snap(t, ents)
        allr = [[d.start, d.end, d.label] for d in det]
        ents = [x for x in ents if not any(q[0] < x[1] and x[0] < q[1] for q in allr)]
        pred = [q for q in allr if q[2] not in NEVER] + ents
        for g in gold:
            chars = [i for i in range(g["start"], g["end"]) if not t[i].isspace()]
            ok = all(any(p[0] <= i < p[1] for p in pred) for i in chars)
            tp += ok; fn += not ok
        fp += sum(1 for p in pred if not any(g["start"] < p[1] and p[0] < g["end"] for g in gold))
    rec, prec = tp / (tp + fn), (tp) / max(1, tp + fp)
    res[str(tau)] = dict(recall=round(rec, 4), precision=round(prec, 4), f1=round(2 * rec * prec / (rec + prec), 4), fp_per_doc=round(fp / len(cache), 3))
    print(tau, res[str(tau)], flush=True)
best = max(res, key=lambda k: res[k]["f1"])
json.dump({"dev_rows": len(cache), "results": res, "best": best}, open(R / "work4/eval/tau.json", "w"), indent=1)
print("best", best)
