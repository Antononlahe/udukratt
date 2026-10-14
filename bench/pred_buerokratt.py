import json, sys, time, urllib.request
sys.path.insert(0, "/workspace/eval")
from suites import load, R
URL = "http://127.0.0.1:8811/anonymize"
ENTS = ["PERSON", "ORGANIZATION", "LOCATION", "GPE", "EMAIL_ADDRESS", "URL", "IP_ADDRESS", "IBAN_CODE", "DATE_TIME", "CRYPTO",
        "CREDIT_CARD", "CAR_NUMBER", "EE_PERSONAL_CODE", "PHONE_NUMBER", "EST_ID_DOC", "DENYLIST_MATCH"]
BAD = []
KEEP = {e: {"type": "keep"} for e in ENTS}
def call(texts):
    req = urllib.request.Request(URL, data=json.dumps({"texts": texts, "language": "xx", "anonymizers": KEEP}).encode(), headers={"Content-Type": "application/json"})
    out = json.load(urllib.request.urlopen(req, timeout=600))["results"]
    for k, (t, r) in enumerate(zip(texts, out)):
        if r["text"] != t:
            BAD.append((t[:80], r["text"][:80]))
    return [[[i["start"], i["end"], i["entity_type"]] for i in r["items"]] for r in out]
if __name__ == "__main__":
    out = {}
    for s, docs in load().items():
        t0 = time.time(); res = []
        for i in range(0, len(docs), 16):
            res += call([d["text"] for d in docs[i:i + 16]])
        out[s] = res; print(s, len(docs), round(time.time() - t0, 1), "s", flush=True)
    print("text-changed docs:", len(BAD), BAD[:3])
    json.dump(out, open(R / "work4/eval/preds_buerokratt.json", "w"))
    pii = {s: [[p for p in doc if p[2] not in ("ORGANIZATION", "DATE_TIME", "CRYPTO")] for doc in v] for s, v in out.items()}
    json.dump(pii, open(R / "work4/eval/preds_buerokratt_pii.json", "w"))
