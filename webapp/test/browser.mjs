import { chromium } from "playwright";
const url = process.argv[2];
const b = await chromium.launch();
const p = await b.newPage();
const errs = [], reqs = [];
p.on("pageerror", e => errs.push(e.message));
p.on("console", m => m.type() === "error" && errs.push(m.text()));
p.on("request", r => reqs.push(r.url()));
await p.goto(url);
await p.waitForFunction(() => document.getElementById("go").textContent === "Redact" && !document.getElementById("results").hidden, null, { timeout: 60000 });
const out = {};
for (const name of ["Avaldus", "Kontakt", "Vene nimi", "JSON payload", "Dokumendid"]) {
  await p.click(`text=${name}`);
  await p.waitForFunction(() => !document.getElementById("go").disabled);
  out[name] = { masked: await p.textContent("#masked"), status: await p.textContent("#status") };
}
const long = (await import("node:fs")).readFileSync("/tmp/longdoc.txt", "utf8");
const times = [];
for (let k = 0; k < 3; k++) { await p.fill("#input", long); await p.click("#go"); await p.waitForFunction(() => !document.getElementById("go").disabled); times.push(await p.textContent("#status")); }
out.longdoc = { chars: long.length, runs: times };
await p.screenshot({ path: "test/screenshot.png", fullPage: true });
console.log(JSON.stringify({ errors: errs, external: reqs.filter(u => !u.startsWith(url.replace(/\/$/, ""))), out }, null, 1));
await b.close();
