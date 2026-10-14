import json, sys, collections
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from suites import load, R
def score(preds, S):
    res = {}
    for s, docs in S.items():
        bt, bf = collections.defaultdict(collections.Counter), collections.defaultdict(collections.Counter)
        tot = collections.Counter()
        for d, pred in zip(docs, preds[s]):
            t = d["text"]; f = bf[d["fmt"]]; f["docs"] += 1
            for g in d["gold"]:
                chars = [i for i in range(g["start"], g["end"]) if not t[i].isspace()]
                hit = [p for p in pred if p[0] < g["end"] and g["start"] < p[1]]
                full = all(any(p[0] <= i < p[1] for p in hit) for i in chars)
                k = "full" if full else ("partial" if hit else "miss")
                for c in (bt[g["label"]], f, tot): c["n"] += 1; c[k] += 1
            for p in pred:
                if not any(g["start"] < p[1] and p[0] < g["end"] for g in d["gold"]): f["fa"] += 1; tot["fa"] += 1
            for g in d["public"]:
                tot["pub"] += 1; tot["pub_kept"] += not any(p[0] < g["end"] and g["start"] < p[1] for p in pred)
        pc = lambda c, k: round(100 * c[k] / max(1, c["n"]), 1)
        res[s] = {"overall": dict(n=tot["n"], full=pc(tot, "full"), partial=pc(tot, "partial"), miss=pc(tot, "miss"), fa_per_doc=round(tot["fa"] / len(docs), 2), public_kept=round(100 * tot["pub_kept"] / max(1, tot["pub"]), 1)),
                  "types": {k: dict(n=c["n"], full=pc(c, "full"), miss=pc(c, "miss")) for k, c in sorted(bt.items(), key=lambda x: -x[1]["n"])},
                  "formats": {k: dict(n=c["n"], full=pc(c, "full"), miss=pc(c, "miss"), fa_per_doc=round(c["fa"] / c["docs"], 2)) for k, c in bf.items()} if s == "corp_suite" else {}}
    return res
if __name__ == "__main__":
    S = load(); allr = {}
    for n in sys.argv[1:]:
        allr[n] = score(json.load(open(R / f"work4/eval/preds_{n}.json")), S)
    json.dump(allr, open(R / "work4/eval/scores.json", "w"), indent=1)
    for s in S:
        print(s, {n: allr[n][s]["overall"] for n in allr})
