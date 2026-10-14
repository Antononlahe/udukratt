import fs from "node:fs";
import * as ort from "onnxruntime-web";
import { WordPiece, redact, detect } from "../rampart.js";
ort.env.wasm.numThreads = 1;
const R = JSON.parse(fs.readFileSync(new URL("./ref.json", import.meta.url))); const ref = R.rows;
const fix = JSON.parse(fs.readFileSync(new URL("../../fixtures/parity.json", import.meta.url)));
const tok = new WordPiece(JSON.parse(fs.readFileSync(new URL("../model/vocab.json", import.meta.url))).vocab);
const sess = await ort.InferenceSession.create(fs.readFileSync(new URL("../model/model_q4.onnx", import.meta.url)), { executionProviders: ["wasm"] });
const infer = async ids => {
  const t = a => new ort.Tensor("int64", BigInt64Array.from(a.map(BigInt)), [1, a.length]);
  const out = await sess.run({ input_ids: t(ids), attention_mask: t(ids.map(() => 1)), token_type_ids: t(ids.map(() => 0)) });
  const L = out.logits.data, res = [];
  for (let i = 1; i < ids.length - 1; i++) res.push(L.subarray(i * 35, i * 35 + 35));
  return res;
};
const eq = (a, b) => JSON.stringify(a) === JSON.stringify(b);
let fixOk = 0;
for (const f of fix) {
  const got = detect(f.text).map(([s, e, l]) => [s, e, l]);
  if (eq(got, f.spans)) fixOk++; else console.log("FIXTURE MISMATCH", f.text, JSON.stringify(got), JSON.stringify(f.spans));
}
const c = { rules: 0, view: 0, ids: 0, labels: 0, model: 0, all: 0 }; let tokTot = 0, tokSame = 0;
for (const r of ref) {
  const g = await redact(r.text, tok, infer, { tau: R.tau });
  const ok = { rules: eq(g.rules, r.rules) && eq(g.never, r.never), view: g.view === r.view, ids: eq(g.ids, r.ids), labels: eq(g.labels, r.labels), model: eq(g.model, r.model) };
  for (const k in ok) c[k] += ok[k];
  c.all += Object.values(ok).every(Boolean);
  if (ok.ids) { tokTot += r.labels.length; tokSame += r.labels.filter((x, i) => x === g.labels[i]).length; }
  if (!ok.view || !ok.ids || !ok.rules) console.log("MISMATCH", JSON.stringify(ok), JSON.stringify(r.text.slice(0, 120)));
}
console.log(JSON.stringify({ fixtures: `${fixOk}/${fix.length}`, rows: ref.length, ...c, token_label_agreement: (tokSame / tokTot).toFixed(5) }));
