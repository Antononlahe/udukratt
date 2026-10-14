import json, sys, collections, random
from pathlib import Path
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parents[1] / "webapp/test"))
from ref import run

docs = [json.loads(l) for l in open(HERE / "corp_suite.jsonl")]
byfmt = collections.defaultdict(collections.Counter); bytype = collections.defaultdict(collections.Counter)
fa_kind = collections.Counter(); misses, fas, preds_out = [], [], []
for d in docs:
    t = d["text"]; r = run(t)
    pred = [(a, b, l, "rule") for a, b, l in r["rules"]] + [(a, b, l, "model") for a, b, l in r["model"]]
    preds_out.append({"uid": d["uid"], "pred": pred})
    f = byfmt[d["format"]]; f["docs"] += 1; f["chars"] += len(t)
    for g in d["spans"]:
        chars = [i for i in range(g["start"], g["end"]) if not t[i].isspace()]
        hit = [p for p in pred if p[0] < g["end"] and g["start"] < p[1]]
        full = all(any(p[0] <= i < p[1] for p in hit) for i in chars)
        res = "full" if full else ("partial" if hit else "miss")
        for c in (f, bytype[g["label"]]): c["n"] += 1; c[res] += 1
        if res != "full": misses.append((d["format"], g["label"], res, g["value"], t[max(0, g["start"] - 40):g["end"] + 30], [p[2] for p in hit]))
    for p in pred:
        if not any(g["start"] < p[1] and p[0] < g["end"] for g in d["spans"]):
            k = next((n["kind"] for n in d["negatives"] if n["start"] < p[1] and p[0] < n["end"]), "other")
            f["fa"] += 1; fa_kind[k] += 1
            fas.append((d["format"], p[2], p[3], k, t[p[0]:p[1]], t[max(0, p[0] - 40):p[1] + 30]))
pct = lambda c, k: round(100 * c[k] / max(1, c["n"]), 1)
res = {"formats": {k: dict(docs=c["docs"], avg_chars=c["chars"] // c["docs"], n=c["n"], full=pct(c, "full"), partial=pct(c, "partial"), miss=pct(c, "miss"), fa_per_doc=round(c["fa"] / c["docs"], 2)) for k, c in byfmt.items()},
       "types": {k: dict(n=c["n"], full=pct(c, "full"), partial=pct(c, "partial"), miss=pct(c, "miss")) for k, c in sorted(bytype.items(), key=lambda x: -x[1]["n"])},
       "fa_by_kind": dict(fa_kind.most_common()), "total_fa": sum(fa_kind.values())}
tot = collections.Counter()
for c in bytype.values(): tot.update(c)
res["overall"] = dict(n=tot["n"], full=pct(tot, "full"), partial=pct(tot, "partial"), miss=pct(tot, "miss"), fa_per_doc=round(sum(fa_kind.values()) / len(docs), 2))
json.dump(res, open(HERE / "results.json", "w"), indent=1, ensure_ascii=False)
json.dump({"misses": misses, "false_alarms": fas}, open(HERE / "errors.json", "w"), indent=1, ensure_ascii=False)
json.dump(preds_out, open(HERE / "predictions.json", "w"), ensure_ascii=False)
print(json.dumps(res, ensure_ascii=False))
rr = random.Random(1)
print("MISS by type/format:", collections.Counter((m[1], m[0]) for m in misses).most_common(25))
print("FA by fmt/label/kind:", collections.Counter((x[0], x[1], x[3]) for x in fas).most_common(25))
print("FA texts:", collections.Counter(x[4] for x in fas).most_common(40))
