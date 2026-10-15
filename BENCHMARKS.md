# Udukratt vs Bürokratt Presidio-Anonymizer

Accuracy for the shipped v0.2 model was measured on 2026-10-15 (EEST). Speed numbers and the Bürokratt baseline are from 2026-10-14 on the same box. All test data is synthetic, except EstNER, which is public news.

## What was compared
- **Udukratt v0.2 (shipped):** improvement-pass p2 model, MiniLM-L6, 4-bit ONNX, ~10 MB, τ = 0.45, plus the rule layer. This is the configuration the webapp ships. Threshold was chosen on the DEV suites only (docs_dev, synth_dev, estner_dev).
- **Udukratt v0.1:** previous shipped run 4 model, same architecture, τ = 0.5. Shown so the gain is clear.
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

| Suite (what it is) | Udukratt v0.2 | Udukratt v0.1 (run 4) | Bürokratt (as shipped / PII-only) | False alarms per doc, v0.2 / v0.1 / B-PII |
|---|---|---|---|---|
| corp_suite: 418 fake corporate docs (CSV, JSON, logs, mail, Confluence) | **97.6%** | 97.5% | 73.5% / 72.5% | 3.34 / 6.11 / 2.34 |
| synth_heldout: 3,000 held-out synthetic sentences | **97.2%** | 96.1% | 85.2% / 82.8% | 0.50 / 0.48 / 0.12 |
| EstNER news: 452 real news paragraphs | 76.3% | 66.8% | **94.8%** / 90.7% | 1.26 / 1.30 / 1.70 |
| gov_chats: 31 public-service-style chats | 91.5% | 89.0% | **100%** / 100% | 0.19 / 0.35 / 0.00 |
| fairness: 2,250 name-swap sentences (et/ru/foreign names) | **99.1%** | 71.0% | 90.3% / 80.3% | 0.22 / 0.26 / 0.15 |

Presidio floor (caught only): corp 56.6%, synth 46.1%, EstNER 76.6%, gov 59.8%, fairness 60.3%.

Raw numbers, including partial catches and public kept, are in `bench/scores_vs_buerokratt.json` (v0.1-era) and the work5 eval scores for v0.2.

**Plain reading:**
- v0.2 keeps the corporate win and roughly halves corp_suite false alarms versus v0.1 (6.11 → 3.34).
- News catch rose a lot versus v0.1 (66.8% → 76.3%), and name fairness jumped from 71% to 99%.
- Bürokratt still wins clearly on news prose and government chats. That gap is smaller than in v0.1, but it is still there.
- Bürokratt still raises fewer false alarms on structured text and chats. On news, Udukratt now has fewer false alarms than Bürokratt PII-only.
- Run as shipped, Bürokratt also redacts organisations and places, which hurts readability (public kept: 20–66%).

## Speed

Same 870 texts (corp_suite plus EstNER), one document per call, warm, startup excluded. The box has 4 vCPUs, shared with other jobs. Model size and runtime path are unchanged from v0.1, so these numbers still apply.

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
- The v0.2 threshold (0.45) was tuned only on DEV suites. Test numbers above were measured once at that chosen threshold.

## Verdict
"Much faster" still holds: about 7–9×, with ~300× less disk and ~25× less RAM. "Same accuracy" still does **not** hold, but the gap is narrower than in v0.1.
- Udukratt is better on corporate and structured text, and now also on name fairness.
- Bürokratt is still clearly better on news prose and chats.

Reproduce: `bench/pred_buerokratt.py`, `bench/score2.py`, `bench/bench.py` (paths assume the dev box layout). For v0.2, use `work5/p2/rampart-et` with τ = 0.45.
