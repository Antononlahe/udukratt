import json, sys, re, collections, random
sys.path[:0] = ["/workspace/eval", "webapp/test"]
from suites import load, R
from tokenizers import Tokenizer
docs = load()["estner_test"]
U = json.load(open(R / "work4/eval/preds_run4t05.json"))["estner_test"]
B = json.load(open(R / "work4/eval/preds_buerokratt_pii.json"))["estner_test"]
tok = Tokenizer.from_file(str(R / "work4/rampart-et/tokenizer.json"))
def full(g, t, pred):
    ch = [i for i in range(g["start"], g["end"]) if not t[i].isspace()]
    return all(any(p[0] <= i < p[1] for p in pred) for i in ch)
vals = collections.Counter(); docsof = collections.defaultdict(set)
for k, d in enumerate(docs):
    for g in d["gold"]: vals[g["value"]] += 1; docsof[g["value"].lower()].add(k)
allv = {g["value"].lower() for d in docs for g in d["gold"]}
FAMOUS = set("""putin jeltsin clinton bush obama gorbatšov merkel meri rüütel ilves savisaar laar kallas siimann ansip parts lennart arnold kohl chirac blair kennedy lenin stalin hitler napoleon jesus jeesus mandela arafat netanyahu milošević saddam hussein madonna jackson beatles elvis presley tõnis mägi kreutzwald koidula tammsaare""".split())
END = re.compile(r"(ile|ilt|iga|ist|isse|ina|iks|ini|le|lt|ga|st|sse|ks|ni|na|ta|ile|l|s|d|i|t)$")
def foreign(v):
    return bool(re.search(r"[cqwxyfzåøæéèçñ]|[а-я]", v.lower())) or bool(re.search(r"(ov|ova|ev|eva|in|ina|ski|sky|sson|ich|vitš|ovitš|enko)$", v.lower()))
def inflected(v):
    m = END.search(v.lower()); 
    if not m or len(v) < 4: return False
    stem = v.lower()[: -len(m.group(1))]
    return any(o != v.lower() and len(o) >= 3 and (o == stem or (o.startswith(stem) and len(o) - len(stem) <= 2)) for o in allv)
rows = []
for k, d in enumerate(docs):
    t = d["text"]; enc = tok.encode(t, add_special_tokens=False)
    for g in d["gold"]:
        if full(g, t, U[k]): continue
        ti = [i for i, (a, b) in enumerate(enc.offsets) if a < g["end"] and g["start"] < b]
        edge = any(i % 126 in (0, 125) for i in ti) or (ti and ti[0] // 126 != ti[-1] // 126)
        v = g["value"]; lv = v.lower()
        if g["label"] in ("CITY", "STREET") and g["label"] == "CITY" or lv in FAMOUS or len(docsof[lv]) >= 3: b = "public/place (definition mismatch)"
        elif edge: b = "chunk edge"
        elif v.islower() or (v.isupper() and len(v) > 1): b = "lowercase/caps-only"
        elif inflected(v): b = "inflected form"
        elif foreign(v): b = "foreign name"
        else: b = "genuine miss"
        ctx = t[max(0, g["start"] - 40): g["end"] + 40].replace("\n", " ")
        rows.append(dict(bucket=b, label=g["label"], value=v, bk=full(g, t, B[k]), ctx=ctx))
n = sum(len(d["gold"]) for d in docs); caught = n - len(rows)
c = collections.Counter(r["bucket"] for r in rows); bkc = collections.Counter(r["bucket"] for r in rows if r["bk"])
print("gold", n, "udukratt full", caught, round(100 * caught / n, 1), "misses", len(rows))
for b, m in c.most_common(): print(f"{b}: {m} (Bürokratt catches {bkc[b]})")
mm = c["public/place (definition mismatch)"]; print("excl. definition mismatch:", round(100 * caught / (n - mm), 1))
# Bürokratt excluding the same items
random.seed(0)
for b in c:
    print("\n##", b)
    for r in random.sample([r for r in rows if r["bucket"] == b], min(10, c[b])): print(f"  [{r['label']}] {r['value']!r} BK={'Y' if r['bk'] else 'n'} … {r['ctx']}")
json.dump(rows, open(R / "work4/eval/estner_misses.json", "w"), ensure_ascii=False, indent=1)
