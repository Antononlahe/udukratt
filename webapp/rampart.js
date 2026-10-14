export const ENTITY_TYPES = ["GIVEN_NAME", "SURNAME", "EMAIL", "PHONE", "URL", "TAX_ID", "BANK_ACCOUNT", "ROUTING_NUMBER",
  "GOVERNMENT_ID", "PASSPORT", "DRIVERS_LICENSE", "BUILDING_NUMBER", "STREET_NAME", "SECONDARY_ADDRESS", "CITY", "STATE", "ZIP_CODE"];
export const ID2LABEL = ["O", ...ENTITY_TYPES.flatMap(t => [`B-${t}`, `I-${t}`])];

const W1 = [1, 2, 3, 4, 5, 6, 7, 8, 9, 1], W2 = [3, 4, 5, 6, 7, 8, 9, 1, 2, 3];
const CENTURY = { 1: 1800, 2: 1800, 3: 1900, 4: 1900, 5: 2000, 6: 2000, 7: 2100, 8: 2100 };

export function luhn(d) {
  let total = 0, dbl = false;
  for (let i = d.length - 1; i >= 0; i--) {
    let x = +d[i];
    if (dbl) x = x > 4 ? x * 2 - 9 : x * 2;
    total += x; dbl = !dbl;
  }
  return total % 10 === 0;
}

function checkDigit(first10) {
  for (const w of [W1, W2]) {
    let r = 0;
    for (let i = 0; i < w.length; i++) r += +first10[i] * w[i];
    r %= 11;
    if (r < 10) return r;
  }
  return 0;
}

export function isValidIsikukood(c) {
  if (!/^\d{11}$/.test(c)) return false;
  const base = CENTURY[+c[0]];
  if (!base) return false;
  const y = base + +c.slice(1, 3), m = +c.slice(3, 5), d = +c.slice(5, 7);
  const dt = new Date(Date.UTC(2000, 0, 1)); dt.setUTCFullYear(y, m - 1, d);
  if (m < 1 || m > 12 || d < 1 || dt.getUTCMonth() !== m - 1 || dt.getUTCDate() !== d) return false;
  return checkDigit(c.slice(0, 10)) === +c[10];
}

export function isValidIban(v) {
  const s = v.replaceAll(" ", "").toUpperCase();
  if (s.length < 15 || s.length > 34 || !/^[A-Z]{2}\d{2}[A-Z0-9]+$/.test(s)) return false;
  if (s.startsWith("EE") && s.length !== 20) return false;
  const moved = s.slice(4) + s.slice(0, 4);
  let r = 0;
  for (const ch of moved) for (const dg of String(parseInt(ch, 36))) r = (r * 10 + +dg) % 97;
  return r === 1;
}

const DIGIT_RULES = [["CREDIT_CARD", [16, 15, 14], luhn], ["ISIKUKOOD", [11], isValidIsikukood]];
const DIGIT_RUN = /\d(?:[ .-]?\d)*/g;
const WS = "[ \\t\\n\\r\\f\\v]";
const TEXT_RULES = [
  ["EMAIL", /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b/g],
  ["URL", new RegExp(`\\bhttps?://[^\\t\\n\\r\\f\\v <>"'\\])}]+`, "g")],
  ["URL", new RegExp(`\\bwww\\.[A-Za-z0-9.-]+\\.[A-Za-z]{2,}(?:/[^\\t\\n\\r\\f\\v <>"'\\])}]*)?`, "g")],
  ["IP_ADDRESS", /\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b/g],
  ["IP_ADDRESS", new RegExp("(?<![:.\\w])(?:(?:[0-9A-Fa-f]{1,4}:){7}[0-9A-Fa-f]{1,4}|(?:[0-9A-Fa-f]{1,4}:){1,7}:|(?:[0-9A-Fa-f]{1,4}:){1,6}:[0-9A-Fa-f]{1,4}"
    + "|(?:[0-9A-Fa-f]{1,4}:){1,5}(?::[0-9A-Fa-f]{1,4}){1,2}|(?:[0-9A-Fa-f]{1,4}:){1,4}(?::[0-9A-Fa-f]{1,4}){1,3}"
    + "|(?:[0-9A-Fa-f]{1,4}:){1,3}(?::[0-9A-Fa-f]{1,4}){1,4}|(?:[0-9A-Fa-f]{1,4}:){1,2}(?::[0-9A-Fa-f]{1,4}){1,5}"
    + "|[0-9A-Fa-f]{1,4}:(?::[0-9A-Fa-f]{1,4}){1,6}|::(?:[0-9A-Fa-f]{1,4}:){0,6}[0-9A-Fa-f]{1,4})(?![:.\\w])", "g")],
  ["IP_ADDRESS", /\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b/g],
];
const IBAN = /\b[A-Za-z]{2}\d{2}(?: ?[A-Za-z0-9]{4}){2,7}(?: ?[A-Za-z0-9]{1,3})?\b/g;

function detectDigits(raw) {
  const spans = [];
  for (const m of raw.matchAll(DIGIT_RUN)) {
    const groups = [];
    let cur = "", idx = [];
    for (let i = 0; i < m[0].length; i++) {
      const ch = m[0][i];
      if (ch >= "0" && ch <= "9") { cur += ch; idx.push(m.index + i); }
      else if (cur) { groups.push([cur, idx]); cur = ""; idx = []; }
    }
    if (cur) groups.push([cur, idx]);
    const taken = new Set();
    for (const [label, lengths, validate] of DIGIT_RULES) {
      const max = Math.max(...lengths);
      for (let i = 0; i < groups.length; i++) {
        let total = 0, j = i;
        while (j < groups.length && total < max) {
          total += groups[j][0].length; j++;
          let free = true;
          for (let k = i; k < j; k++) if (taken.has(k)) free = false;
          if (lengths.includes(total) && free) {
            const digits = groups.slice(i, j).map(g => g[0]).join("");
            if (validate(digits)) {
              spans.push([groups[i][1][0], groups[j - 1][1].at(-1) + 1, label]);
              for (let k = i; k < j; k++) taken.add(k);
              break;
            }
          }
        }
      }
    }
  }
  return spans;
}

function detectIban(raw) {
  const spans = [];
  for (const m of raw.matchAll(IBAN)) {
    let text = m[0];
    while (text.replaceAll(" ", "").length >= 15) {
      if (isValidIban(text)) { spans.push([m.index, m.index + text.length, "BANK_ACCOUNT"]); break; }
      const cut = text.lastIndexOf(" ");
      if (cut < 0) break;
      text = text.slice(0, cut);
    }
  }
  return spans;
}

function merge(spans) {
  const out = [];
  for (const s of [...spans].sort((a, b) => a[0] - b[0] || b[1] - a[1])) {
    const p = out.at(-1);
    if (p && s[0] < p[1]) {
      const win = (s[1] - s[0]) > (p[1] - p[0]) ? s : p;
      const contains = (p[0] <= s[0] && p[1] >= s[1]) || (s[0] <= p[0] && s[1] >= p[1]);
      out[out.length - 1] = contains ? win : [Math.min(p[0], s[0]), Math.max(p[1], s[1]), win[2]];
    } else out.push(s);
  }
  return out;
}

export const NEVER = new Set(["UUID", "HASH", "SLACK_ID", "VERSION", "REF"]);
const NEVER_RULES = [
  ["UUID", /\b[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}\b/g],
  ["SLACK_ID", /\b[UWCT]0[A-Z0-9]{6,10}\b/g],
  ["HASH", /\b(?=[0-9a-f]*[a-f])(?=[0-9a-f]*[0-9])[0-9a-f]{7,64}\b/g],
  ["VERSION", /\bv\d+(?:\.\d+){1,3}\b|(?<![\d.])\d{1,2}\.\d{1,3}\.\d{1,3}(?![\d.])/g],
  ["REF", /#\d{2,}\b/g],
];
const findAll = (raw, rules) => rules.flatMap(([l, re]) => [...raw.matchAll(re)].map(m => [m.index, m.index + m[0].length, l]));

export function detect(raw, never = true) {
  const pii = merge([...detectDigits(raw), ...detectIban(raw), ...findAll(raw, TEXT_RULES)]);
  if (!never) return pii;
  const nv = merge(findAll(raw, NEVER_RULES).filter(s => !pii.some(p => p[0] < s[1] && s[0] < p[1])));
  return [...pii, ...nv].sort((a, b) => a[0] - b[0]);
}

const VOWELS = new Set("аеёиоуыэюяaeiouõäöüy");
const BASE = { "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "ж": "ž", "з": "z", "и": "i", "к": "k", "л": "l", "м": "m",
  "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "h", "ц": "ts", "ч": "tš", "ш": "š",
  "щ": "štš", "ъ": "", "ы": "õ", "ь": "", "э": "e", "ю": "ju", "я": "ja", "і": "i", "ї": "ji", "є": "je", "ґ": "g", "ў": "u" };
const ALPHA = /^[\p{Lu}\p{Ll}\p{Lt}\p{Lm}\p{Lo}]$/u;

function translitChar(cps, i) {
  const c = cps[i], low = c.toLowerCase();
  const prev = i > 0 ? cps[i - 1].toLowerCase() : " ";
  const nxt = i + 1 < cps.length ? cps[i + 1].toLowerCase() : " ";
  let out;
  if (low === "е") out = (!ALPHA.test(prev) || VOWELS.has(prev) || "ъь".includes(prev)) ? "je" : "e";
  else if (low === "ё") out = "жчшщ".includes(prev) ? "o" : "jo";
  else if (low === "й") out = VOWELS.has(nxt) ? "j" : "i";
  else if (low in BASE) out = BASE[low];
  else return c;
  return c !== low && out ? out[0].toUpperCase() + out.slice(1) : out;
}

const MN = /\p{Mn}/u;
const foldChar = ch => [...ch.toLowerCase().normalize("NFKD")].filter(d => !MN.test(d)).join("").toLowerCase();

export function modelView(raw, sentinels) {
  const cps = [], u16 = [];
  let u = 0;
  for (const ch of raw) { cps.push(ch); u16.push(u); u += ch.length; }
  u16.push(u);
  const out = [], starts = [], ends = [];
  const emit = (s, a, b) => { for (const ch of s) for (const f of foldChar(ch)) { out.push(f); starts.push(a); ends.push(b); } };
  const cpOf = new Map(u16.map((x, i) => [x, i]));
  let cursor = 0;
  for (const [s16, e16, label] of [...sentinels].sort((a, b) => a[0] - b[0])) {
    const s = cpOf.get(s16), e = cpOf.get(e16);
    if (s < cursor) continue;
    for (let i = cursor; i < s; i++) emit(translitChar(cps, i), u16[i], u16[i + 1]);
    emit(`[${label}]`, s16, e16);
    cursor = e;
  }
  for (let i = cursor; i < cps.length; i++) emit(translitChar(cps, i), u16[i], u16[i + 1]);
  return { chars: out, starts, ends };
}

const isCtl = c => c !== "\t" && c !== "\n" && c !== "\r" && /[\p{Cc}\p{Cf}\p{Cn}\p{Co}]/u.test(c);
const isWs = c => /\s/u.test(c);
const isPunct = c => { const o = c.codePointAt(0); return (o >= 33 && o <= 47) || (o >= 58 && o <= 64) || (o >= 91 && o <= 96) || (o >= 123 && o <= 126) || /\p{P}/u.test(c); };
const isCjk = o => (o >= 0x4E00 && o <= 0x9FFF) || (o >= 0x3400 && o <= 0x4DBF) || (o >= 0x20000 && o <= 0x2A6DF) || (o >= 0x2A700 && o <= 0x2CEAF) || (o >= 0xF900 && o <= 0xFAFF) || (o >= 0x2F800 && o <= 0x2FA1F);

export class WordPiece {
  constructor(vocab) { this.vocab = vocab; this.unk = vocab["[UNK]"]; }
  encode(chars) {
    const norm = [];
    for (let i = 0; i < chars.length; i++) {
      const c = chars[i];
      if (c === "\0" || c === "\ufffd" || isCtl(c)) continue;
      if (isWs(c)) { norm.push([" ", i]); continue; }
      const cjk = isCjk(c.codePointAt(0));
      if (cjk) norm.push([" ", i]);
      for (const f of foldChar(c)) norm.push([f, i]);
      if (cjk) norm.push([" ", i]);
    }
    const words = [];
    let w = [];
    const flush = () => { if (w.length) words.push(w); w = []; };
    for (const p of norm) {
      if (isWs(p[0])) flush();
      else if (isPunct(p[0])) { flush(); words.push([p]); }
      else w.push(p);
    }
    flush();
    const ids = [], offsets = [];
    for (const word of words) {
      const s = word.map(p => p[0]);
      const span = (a, b) => [word[a][1], word[b - 1][1] + 1];
      if (s.length > 100) { ids.push(this.unk); offsets.push(span(0, s.length)); continue; }
      const pieces = [];
      let start = 0, bad = false;
      while (start < s.length) {
        let end = s.length, id;
        while (start < end) {
          const sub = (start > 0 ? "##" : "") + s.slice(start, end).join("");
          if (sub in this.vocab) { id = this.vocab[sub]; break; }
          end--;
        }
        if (id === undefined) { bad = true; break; }
        pieces.push([id, span(start, end)]); start = end;
      }
      if (bad) { ids.push(this.unk); offsets.push(span(0, s.length)); }
      else for (const [id, o] of pieces) { ids.push(id); offsets.push(o); }
    }
    return { ids, offsets };
  }
}

function decide(row, tau) {
  let b = 1;
  for (let j = 2; j < row.length; j++) if (row[j] > row[b]) b = j;
  if (tau == null) return row[0] >= row[b] ? 0 : b;
  let mx = -Infinity;
  for (const x of row) mx = Math.max(mx, x);
  let z = 0;
  for (const x of row) z += Math.exp(x - mx);
  return 1 - Math.exp(row[0] - mx) / z >= tau ? b : 0;
}

const WORD = /[\p{L}\p{N}]/u;
function snap(text, ents) {
  const cps = [], at = new Map();
  let u = 0;
  for (const ch of text) { at.set(u, cps.length); cps.push([u, ch]); u += ch.length; }
  const out = [];
  for (let [s, e, t] of ents) {
    let i = at.get(s), j = at.get(e) ?? cps.length;
    while (i > 0 && WORD.test(cps[i - 1][1])) i--;
    while (j < cps.length && WORD.test(cps[j][1])) j++;
    s = cps[i][0]; e = j < cps.length ? cps[j][0] : text.length;
    if (out.length && s < out.at(-1)[1]) out.at(-1)[1] = Math.max(out.at(-1)[1], e);
    else out.push([s, e, t]);
  }
  return out;
}

export async function redact(text, tok, infer, { tau = null, useSnap = true, body = 126 } = {}) {
  const all = detect(text);
  const v = modelView(text, all);
  const { ids, offsets } = tok.encode(v.chars);
  const labels = [];
  for (let st = 0; st < ids.length; st += body) for (const row of await infer([2, ...ids.slice(st, st + body), 3])) labels.push(decide(row, tau));
  let ents = [], cur = null;
  offsets.forEach(([a, b], k) => {
    const lab = ID2LABEL[labels[k]];
    if (lab === "O" || b <= a) { cur = null; return; }
    const [p, t] = [lab.slice(0, 1), lab.slice(2)];
    const s = v.starts[a], e = v.ends[b - 1];
    if (p === "I" && cur && cur[2] === t) cur[1] = e;
    else { cur = [s, e, t]; ents.push(cur); }
  });
  if (useSnap) ents = snap(text, ents);
  const model = ents.filter(x => !all.some(r => r[0] < x[1] && x[0] < r[1]));
  return { rules: all.filter(r => !NEVER.has(r[2])), never: all.filter(r => NEVER.has(r[2])), model, view: v.chars.join(""), ids, labels };
}

export function maskText(text, spans) {
  let out = "", pos = 0;
  for (const [s, e, l] of [...spans].sort((a, b) => a[0] - b[0])) {
    if (s < pos) continue;
    out += text.slice(pos, s) + `[${l}]`; pos = e;
  }
  return out + text.slice(pos);
}
