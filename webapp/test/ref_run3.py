import json, sys, random
from pathlib import Path
import numpy as np, onnxruntime as ort
from tokenizers import Tokenizer
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from et.deterministic import detect
from et.normalize import model_view
from et.labels import ID2LABEL

M = ROOT / "work3/rampart-et"
tok = Tokenizer.from_file(str(M / "tokenizer.json"))
sess = ort.InferenceSession(str(M / "onnx/model_q4.onnx"))
BODY = 126

def cp2u16(text):
    m, u = [], 0
    for ch in text:
        m.append(u); u += 2 if ord(ch) > 0xFFFF else 1
    m.append(u); return m

def run(text):
    det = detect(text)
    view, rs, re_ = model_view(text, [(d.start, d.end, d.label) for d in det], True)
    enc = tok.encode(view, add_special_tokens=False)
    ids, offs = enc.ids, enc.offsets
    labs = []
    for st in range(0, len(ids), BODY):
        ch = [2] + ids[st:st + BODY] + [3]
        a = np.array([ch], dtype=np.int64)
        lg = sess.run(None, {"input_ids": a, "attention_mask": np.ones_like(a), "token_type_ids": np.zeros_like(a)})[0][0]
        labs += lg.argmax(-1).tolist()[1:-1]
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
    rules = [[d.start, d.end, d.label] for d in det]
    ents = [x for x in ents if not any(r[0] < x[1] and x[0] < r[1] for r in rules)]
    m = cp2u16(text)
    conv = lambda xs: [[m[a], m[b], l] for a, b, l in xs]
    return {"text": text, "rules": conv(rules), "view": view, "ids": ids, "labels": labs, "model": conv(ents)}

if __name__ == "__main__":
    texts = [r["text"] for r in json.load(open(ROOT / "fixtures/parity.json"))]
    val = [json.loads(l)["text"] for l in open(ROOT / "work3/mix/val.jsonl")]
    random.Random(0).shuffle(val)
    texts += val[:300]
    texts += ["Елена Смирнова, ул. Ленина 5, тел 5123 4567 😀 Jüri Mägi", "名前 王伟 email wang@test.cn\tİstanbul ß ﬁnants 1½ €", "Tere\u200b Mari\x07 Tamm 🇪🇪 IK 49403136526, IBAN EE382200221020145685", "Ёлка Йыги Жёлтый объём Щукин"]
    json.dump([run(t) for t in texts], open(Path(__file__).parent / "ref.json", "w"), ensure_ascii=False)
    print(len(texts))
