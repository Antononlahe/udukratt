import * as ort from "./vendor/ort.wasm.min.mjs";
import { WordPiece, redact, maskText } from "./rampart.js";

ort.env.wasm.wasmPaths = new URL("./vendor/", import.meta.url).href;
ort.env.wasm.numThreads = 1;

const TAU = 0.45;

const EXAMPLES = {
  "Avaldus": "Tere! Minu nimi on Mari Tamm, isikukood 49403136526. Elan Tartus, Riia tn 15-7, 51004. Palun kandke toetus kontole EE382200221020145685.",
  "Kontakt": "Kirjutage mulle aadressil jaan.kask@gmail.com või helistage +372 5123 4567. Olen kodus pärast kella 17.",
  "Vene nimi": "Pöördun ema Елена Смирнова nimel, ta elab Narvas, Joala 8. Tema telefon on 5555 1234.",
  "JSON payload": '{"requestId": "694baad6-db4c-9492-bf5f-85e231d06d9c", "eesnimi": "Kadri", "perekonnanimi": "Saar", "isikukood": "49403136526", "telefon": "+372 5512 3456", "linn": "Pärnu", "version": "v2.4.1"}',
  "Dokumendid": "Passi number K1234567, juhiluba ET123456. Auto number 123 ABC. Kaardi number 4111 1111 1111 1111.",
};
const COLORS = { GIVEN_NAME: "#ffd7a8", SURNAME: "#ffc28a", EMAIL: "#c7e3ff", PHONE: "#d4f1c5", URL: "#c7e3ff", TAX_ID: "#e8d4ff",
  BANK_ACCOUNT: "#ffd1dc", GOVERNMENT_ID: "#e8d4ff", ISIKUKOOD: "#f3b6c9", PASSPORT: "#e8d4ff", DRIVERS_LICENSE: "#e8d4ff",
  CREDIT_CARD: "#ffd1dc", IP_ADDRESS: "#c7e3ff", BUILDING_NUMBER: "#cdeee9", STREET_NAME: "#b8e6df", SECONDARY_ADDRESS: "#cdeee9",
  CITY: "#fff1a8", STATE: "#fff1a8", ZIP_CODE: "#cdeee9", ROUTING_NUMBER: "#ffd1dc" };

const $ = id => document.getElementById(id);
const esc = s => s.replace(/[&<>]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" })[c]);
const input = $("input"), go = $("go"), status = $("status");

for (const [name, text] of Object.entries(EXAMPLES)) {
  const b = document.createElement("button");
  b.textContent = name;
  b.onclick = () => { input.value = text; run(); };
  $("examples").append(b);
}
input.value = Object.values(EXAMPLES)[0];

let tok, sess;
async function infer(ids) {
  const t = a => new ort.Tensor("int64", BigInt64Array.from(a.map(BigInt)), [1, a.length]);
  const out = await sess.run({ input_ids: t(ids), attention_mask: t(ids.map(() => 1)), token_type_ids: t(ids.map(() => 0)) });
  const L = out.logits.data, res = [];
  for (let i = 1; i < ids.length - 1; i++) res.push(L.subarray(i * 35, i * 35 + 35));
  return res;
}

async function run() {
  if (!sess) return;
  const text = input.value, t0 = performance.now();
  go.disabled = true;
  const r = await redact(text, tok, infer, { tau: TAU });
  const spans = [...r.rules.map(s => [...s, "rule"]), ...r.model.map(s => [...s, "model"])].sort((a, b) => a[0] - b[0]);
  let html = "", pos = 0;
  const used = new Set();
  for (const [s, e, l, src] of spans) {
    if (s < pos) continue;
    used.add(l);
    html += esc(text.slice(pos, s)) + `<mark style="background:${COLORS[l] || "#eee"}" title="${l} (${src})">${esc(text.slice(s, e))}<small>${l}</small></mark>`;
    pos = e;
  }
  $("highlight").innerHTML = html + esc(text.slice(pos));
  $("legend").innerHTML = [...used].map(l => `<span style="background:${COLORS[l] || "#eee"}">${l}</span>`).join("");
  $("masked").textContent = maskText(text, spans);
  $("results").hidden = false;
  status.textContent = `${spans.length} spans (${r.rules.length} by rules, ${r.model.length} by model, ${r.never.length} ids ignored), ${Math.round(performance.now() - t0)} ms`;
  go.disabled = false;
}

go.onclick = run;
(async () => {
  try {
    const [vocab, model] = await Promise.all([
      fetch("model/vocab.json").then(r => r.json()),
      fetch("model/model_q4.onnx").then(r => r.arrayBuffer()),
    ]);
    tok = new WordPiece(vocab.vocab);
    sess = await ort.InferenceSession.create(model, { executionProviders: ["wasm"] });
    go.textContent = "Redact"; go.disabled = false;
    run();
  } catch (e) { status.textContent = "Failed to load model: " + e.message; }
})();
