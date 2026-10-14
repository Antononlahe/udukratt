# Udukratt vs Bürokratt Presidio-Anonymizer

All numbers come from one box, measured on 2026-10-14 (EEST). All test data is synthetic, except EstNER, which is public news.

## What was compared
- **Udukratt v0.1:** run 4 model, MiniLM-L6, 4-bit ONNX, ~10 MB, τ = 0.5, plus the rule layer. This is the configuration the webapp ships.
- **Bürokratt:** [buerokratt/Presidio-Anonymizer](https://github.com/buerokratt/Presidio-Anonymizer) @ `48f0381`, run as intended.
  - Setup: its own Python setup with `app.py --config config/presidio-spacy-estbert.yml`. Docker isn't available on the box.
  - Model: `buerokrattRIA/xlm-roberta-NER-syntheticGov` (XLM-RoBERTa), with Estonian recognizers for isikukood, document numbers, car plates and phones.
  - Threads: ONNX 2 inter / 2 intra, as in its compose file.
  - Scored two ways:
    - **as shipped:** every entity it returns.
    - **PII-only:** ORGANIZATION, DATE_TIME and CRYPTO dropped. This is fairer, because our gold data doesn't count organisations as PII.
- **Plain Presidio** 2.2.364 with `xx_ent_wiki_sm`, as a floor.

## Metric
- **Caught:** % of gold PII values that were fully redacted, meaning every character was covered.
- **False alarms per doc:** predicted spans that touch no gold PII.
- **Public kept:** % of tagged public/non-PII items (company names, products, ids) that stayed readable.

## Accuracy

| Suite (what it is) | Udukratt caught | Bürokratt caught (as shipped / PII-only) | Presidio caught | False alarms per doc, U / B-PII |
|---|---|---|---|---|
| corp_suite: 418 fake corporate docs (CSV, JSON, logs, mail, Confluence) | **97.5%** | 73.5% / 72.5% | 56.6% | 6.11 / 2.34 |
| synth_heldout: 3,000 held-out synthetic sentences | **96.1%** | 85.2% / 82.8% | 46.1% | 0.48 / 0.12 |
| EstNER news: 452 real news paragraphs | 66.8% | **94.8%** / 90.7% | 76.6% | 1.30 / 1.70 |
| gov_chats: 31 public-service-style chats | 89.0% | **100%** / 100% | 59.8% | 0.35 / 0.00 |
| fairness: 2,250 name-swap sentences (et/ru/foreign names) | 71.0% | **90.3%** / 80.3% | 60.3% | 0.26 / 0.15 |

Raw numbers, including partial catches and public kept, are in `bench/scores_vs_buerokratt.json`.

**Plain reading:**
- Udukratt wins clearly on structured corporate text: tables, payloads, logs, ids next to names.
- Bürokratt wins clearly on natural prose: news, chats, and names it hasn't seen.
- Bürokratt also raises fewer false alarms everywhere except news. Udukratt's corp_suite false alarms are mostly log tokens and markup.
- Run as shipped, Bürokratt also redacts organisations and places, which hurts readability (public kept: 20–66%).

## Speed

Same 870 texts (corp_suite plus EstNER), one document per call, warm, startup excluded. The box has 4 vCPUs, shared with other jobs.

| | Median per doc | p95 | Slowest | Throughput | Startup | Memory | On disk |
|---|---|---|---|---|---|---|---|
| Udukratt Python ONNX q4, 2 threads | 38 ms | 88 ms | 211 ms | 23.4 docs/s | ~0.2–0.5 s | ~115 MB RSS | ~10 MB model |
| Udukratt Python ONNX q4, 4 threads | 28 ms | 57 ms | 128 ms | 34.3 docs/s | | | |
| Udukratt browser wasm, 1 thread | 50–120 ms short texts | | ~1.3 s (3.2 k chars) | | model download ~10 MB | | |
| Bürokratt warm, HTTP, 2×2 ONNX threads | 256 ms | 804 ms | 2,747 ms | 3.0 docs/s | ~53 s (cache warm) | ~3.1 GB RSS | 2.2 GB model cache |

At equal threads, Udukratt is about **6.7× faster** at the median, **~9× faster** at p95, and **~7.8× faster** on throughput.

## Caveats
- Bürokratt was called over local HTTP. That adds a few ms per call, which is small next to 256 ms.
- Browser numbers come from earlier Playwright runs, not this exact 870-text loop.
- The model was trained on synthetic data from the same generator family as corp_suite and synth_heldout. Those two suites therefore favour Udukratt. EstNER, gov_chats and fairness are fairer tests.
- Bürokratt's model was trained on synthetic government dialogues, so gov_chats may favour it.
- Definitions differ. EstNER tags public figures and organisations-as-places. Udukratt deliberately keeps some public entities.

## Verdict
"Much faster" holds: about 7–9×, with ~300× less disk and ~25× less RAM. "Same accuracy" does **not** hold.
- Udukratt is better on corporate and structured text.
- Bürokratt is clearly better on news prose, chats and varied names.

Reproduce: `bench/pred_buerokratt.py`, `bench/score2.py`, `bench/bench.py` (paths assume the dev box layout).
