const { invoke } = window.__TAURI__.core;
const $ = id => document.getElementById(id);
const input = $("input"), go = $("go"), save = $("save");
let name = "text.txt";
async function load(file) {
  name = file.name;
  if (/\.docx$/i.test(name)) input.value = await invoke("docx_text", { bytes: Array.from(new Uint8Array(await file.arrayBuffer())) });
  else input.value = await file.text();
  $("fname").textContent = `${name} (${input.value.length.toLocaleString()} chars)`;
  if (!go.disabled) go.click();
}
$("open").onclick = () => $("file").click();
$("file").onchange = e => e.target.files[0] && load(e.target.files[0]);
for (const ev of ["dragenter", "dragover"]) document.addEventListener(ev, e => { e.preventDefault(); input.classList.add("drag"); });
document.addEventListener("dragleave", () => input.classList.remove("drag"));
document.addEventListener("drop", e => { e.preventDefault(); input.classList.remove("drag"); const f = e.dataTransfer.files[0]; if (f) load(f); });
new MutationObserver(() => { save.disabled = $("results").hidden; }).observe($("results"), { attributes: true });
save.onclick = async () => {
  const dot = name.lastIndexOf("."), ext = /\.docx$/i.test(name) ? ".txt" : (dot > 0 ? name.slice(dot) : ".txt");
  const suggested = (dot > 0 ? name.slice(0, dot) : name) + ".redacted" + ext;
  const where = await invoke("save_text", { suggested, text: $("masked").textContent });
  if (where) $("status").textContent = "Saved " + where;
};
window.__udukratt_load = load; // used by smoke test

const smoke = await invoke("smoke_input");
if (smoke) {
  await new Promise(r => { const t = setInterval(() => { if (!go.disabled) { clearInterval(t); r(); } }, 100); });
  await load(new File([smoke[1]], smoke[0]));
  await new Promise(r => { const t = setInterval(() => { if (!go.disabled && !$("results").hidden) { clearInterval(t); r(); } }, 100); });
  save.click();
}
