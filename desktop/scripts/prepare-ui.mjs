// Copies the webapp (UI, model, onnxruntime-web wasm) into dist/ and adds the desktop file I/O layer.
import { existsSync, cpSync, rmSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
const W = new URL("../../webapp/", import.meta.url), D = new URL("../dist/", import.meta.url);
rmSync(D, { recursive: true, force: true }); mkdirSync(D);
for (const f of ["app.js", "rampart.js", "style.css", "model"]) cpSync(new URL(f, W), new URL(f, D), { recursive: true });
if (!existsSync(new URL("model/model_q4.onnx", D))) throw new Error("webapp/model/model_q4.onnx missing (download it from the v0.1 release)");
// onnxruntime-web runtime files, from this package's pinned dependency
const ORT = new URL("../node_modules/onnxruntime-web/dist/", import.meta.url);
mkdirSync(new URL("vendor/", D));
for (const f of ["ort.wasm.min.mjs", "ort-wasm-simd-threaded.mjs", "ort-wasm-simd-threaded.wasm"]) cpSync(new URL(f, ORT), new URL("vendor/" + f, D));
cpSync(new URL("../ui-extra/desktop.js", import.meta.url), new URL("desktop.js", D));
cpSync(new URL("../ui-extra/desktop.css", import.meta.url), new URL("desktop.css", D));
let html = readFileSync(new URL("index.html", W), "utf8")
  .replace("</head>", '<link rel="stylesheet" href="desktop.css">\n</head>')
  .replace('<textarea id="input"', `<div class="files"><input type="file" id="file" accept=".txt,.md,.csv,.json,.xml,.yaml,.yml,.html,.htm,.log,.sql,.docx" hidden><button id="open">Open file…</button><button id="save" disabled>Save redacted file…</button><span id="fname">or drop a file onto the text box</span></div>\n  <textarea id="input"`)
  .replace("in your browser", "on your computer").replace("this browser, there is no server", "this computer. The app has no network access")
  .replace('<script type="module" src="app.js"></script>', '<script type="module" src="app.js"></script>\n<script type="module" src="desktop.js"></script>');
writeFileSync(new URL("index.html", D), html);
console.log("dist ready");
