import json, sys, random
from pathlib import Path
import numpy as np, onnxruntime as ort
from tokenizers import Tokenizer
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from et.deterministic import detect, NEVER
from et.normalize import model_view
from et.labels import ID2LABEL

BODY = 126
_cache = {}

def load(mdir):
    if mdir not in _cache:
        m = ROOT / mdir
        so = ort.SessionOptions(); so.intra_op_num_threads = 4
        _cache[mdir] = (Tokenizer.from_file(str(m / "tokenizer.json")), ort.InferenceSession(str(m / "onnx/model_q4.onnx"), so))
    return _cache[mdir]

def cp2u16(text):
    m, u = [], 0
    for ch in text:
        m.append(u); u += 2 if ord(ch) > 0xFFFF else 1
    m.append(u); return m

def decide(lg, tau):
    if tau is None:
        return int(lg.argmax())
    e = np.exp(lg - lg.max()); p = e / e.sum()
    return int(1 + p[1:].argmax()) if 1 - p[0] >= tau else 0

def snap(text, ents):
    out = []
    for s, e, t in ents:
        while s > 0 and text[s - 1].isalnum(): s -= 1
        while e < len(text) and text[e].isalnum(): e += 1
        if out and s < out[-1][1]:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e, t])
    return out

import os
MDIR = os.environ.get("MDIR", "work4/rampart-et")

def run(text, mdir=None, tau=None, use_snap=True, never=True):
    tok, sess = load(mdir or MDIR)
    det = detect(text, never=never)
    view, rs, re_ = model_view(text, [(d.start, d.end, d.label) for d in det], True)
    enc = tok.encode(view, add_special_tokens=False)
    ids, offs = enc.ids, enc.offsets
    labs = []
    for st in range(0, len(ids), BODY):
        ch = [2] + ids[st:st + BODY] + [3]
        a = np.array([ch], dtype=np.int64)
        lg = sess.run(None, {"input_ids": a, "attention_mask": np.ones_like(a), "token_type_ids": np.zeros_like(a)})[0][0]
        labs += [decide(x, tau) for x in lg[1:-1]]
    ents, cur = [], None
    for (a, b), l in zip(offs, labs):
        lab = ID2LABEL[l]
        if lab == "O" or b <= a:
            cur = None; continue
        p, t = lab.split("-", 1)
        s, e = rs[a], re_[b - 1]
        if p == "I" and cur and cur[2] == t:
            cur[1] = e
        else:
            cur = [s, e, t]; ents.append(cur)
    if use_snap:
        ents = snap(text, ents)
    allr = [[d.start, d.end, d.label] for d in det]
    ents = [x for x in ents if not any(r[0] < x[1] and x[0] < r[1] for r in allr)]
    rules = [r for r in allr if r[2] not in NEVER]
    m = cp2u16(text)
    conv = lambda xs: [[m[a], m[b], l] for a, b, l in xs]
    return {"text": text, "rules": conv(rules), "never": conv([r for r in allr if r[2] in NEVER]), "view": view, "ids": ids, "labels": labs, "model": conv(ents)}

if __name__ == "__main__":
    tau = float(sys.argv[1]) if len(sys.argv) > 1 else None
    texts = [r["text"] for r in json.load(open(ROOT / "fixtures/parity.json"))]
    val = [json.loads(l)["text"] for l in open(ROOT / "work4/mix/val.jsonl")]
    random.Random(0).shuffle(val)
    texts += val[:300]
    texts += ["Елена Смирнова, ул. Ленина 5, тел 5123 4567 😀 Jüri Mägi", "名前 王伟 email wang@test.cn\tİstanbul ß ﬁnants 1½ €",
              "Tere\u200b Mari\x07 Tamm 🇪🇪 IK 49403136526, IBAN EE382200221020145685", "Ёлка Йыги Жёлтый объём Щукин",
              "id 694baad6-db4c-9492-bf5f-85e231d06d9c build=a3f9c21 <@U0A3F9K2L> v1.8.0 #8852 ip 10.0.0.1 konto ee382200221020145685 12.05.2026"]
    texts += [json.loads(l)["text"] for l in open(ROOT / "work3/corp_suite/corp_suite.jsonl")][::40]
    json.dump({"tau": tau, "rows": [run(t, tau=tau) for t in texts]}, open(Path(__file__).parent / "ref.json", "w"), ensure_ascii=False)
    print(len(texts))
