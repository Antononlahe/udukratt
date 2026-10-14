import json, sys, time, statistics, urllib.request, os, resource
sys.path.insert(0, "/workspace/eval"); sys.path.insert(0, "/workspace/projects/rampart-et/webapp/test")
from suites import load, R
S = load(); texts = [d["text"] for s in ("corp_suite", "estner_test") for d in S[s]]
json.dump(texts, open("/workspace/eval/bench_texts.json", "w"))
which = sys.argv[1]
if which == "uk":
    t0 = time.time(); from ref import run; run("Tere Mari"); start = time.time() - t0
    f = lambda t: run(t, mdir="work4/rampart-et", tau=0.5); f("soojendus")
else:
    start = None
    def f(t):
        req = urllib.request.Request("http://127.0.0.1:8811/anonymize", data=json.dumps({"texts": [t], "language": "xx"}).encode(), headers={"Content-Type": "application/json"})
        return json.load(urllib.request.urlopen(req))
    for t in texts[:5]: f(t)
lat = []; T0 = time.time()
for t in texts:
    a = time.perf_counter(); f(t); lat.append((time.perf_counter() - a) * 1000)
tot = time.time() - T0; lat.sort(); chars = sum(map(len, texts))
r = dict(which=which, threads=os.environ.get("UK_THREADS"), n=len(texts), median_ms=round(statistics.median(lat), 1), p95_ms=round(lat[int(.95 * len(lat))], 1), max_ms=round(lat[-1], 1), docs_per_s=round(len(texts) / tot, 2), kchars_per_s=round(chars / tot / 1000, 1), startup_s=start, rss_mb=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1024)
print(json.dumps(r)); open("/workspace/eval/bench.jsonl", "a").write(json.dumps(r) + "\n")
