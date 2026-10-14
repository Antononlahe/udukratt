import json, sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent)); sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2] / "webapp/test"))
from suites import load, R
name, mode = sys.argv[1], sys.argv[2]
tau = float(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3] != "none" else None
if mode == "run3_old":
    from ref_run3 import run
    f = lambda t: run(t)
else:
    from ref import run
    mdir = {"run3_new": "work3/rampart-et", "run4": "work4/rampart-et"}[mode]
    f = lambda t: run(t, mdir=mdir, tau=tau)
out = {}
for s, docs in load().items():
    out[s] = []
    for d in docs:
        r = f(d["text"]); out[s].append([[a, b, l] for a, b, l in r["rules"] + r["model"]])
json.dump(out, open(R / f"work4/eval/preds_{name}.json", "w"))
print("done", name)
