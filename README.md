# Udukratt

Udukratt is a small on-device redactor for Estonian personal data. It is an Estonian rebuild of National Design Studio's
[Rampart](https://github.com/nationaldesignstudio/rampart): a MiniLM-L6 token classifier (about 10 MB as 4-bit ONNX) behind a
deterministic checksum layer, trained only on public, pseudonymised and synthetic data. Everything runs locally, including in the browser.

**Live demo:** https://webapp-pi-two-63.vercel.app (fully client-side, no text leaves the browser)

**Status:** experimental research model (v0.1). Do not rely on it as the only safeguard for real redaction.

## What it catches

| Layer | Types |
|---|---|
| Rules (checksums and patterns) | isikukood (birth date plus mod-11), IBAN (mod 97), Luhn cards, email, URL, IPv4/IPv6/MAC |
| Never-PII premask (masked so the model ignores them, never redacted) | UUIDs, hex hashes, Slack ids, version strings, `#123` references |
| Model | first names, surnames, phones, street, house, flat, city, county, postcode, plates and ID cards, passports, driving licences, tax ids |

Cyrillic is transliterated with the Estonian standard before folding, so Russian and Ukrainian names in either script reach the model the same way.
Model spans are snapped to whole words, and a confidence threshold (0.5 in the demo) decides when a token counts as PII.

## Results (v0.1, model "run 4")

Share of PII values fully redacted, end to end (rules plus model), with false alarms per document. Presidio is
`presidio-analyzer` 2.2.364 with spaCy `xx_ent_wiki_sm` and its pattern recognizers (email, phone EE, IBAN, card, IP, URL), configured for Estonian.

| Suite | Docs | Udukratt v0.1 | Previous model (run 3) | Presidio |
|---|---|---|---|---|
| corp_suite: 418 fake corporate docs, 19 formats | 418 | 97.5% caught, 6.1 false alarms per doc | 82.3%, 4.3 | 56.6%, 4.5 |
| Held-out synthetic chats (unseen names, streets, templates) | 3000 | 96.1%, 0.5 | 95.6%, 0.5 | 46.1%, 0.2 |
| EstNER test (real Estonian news, names and places) | 452 | 66.8%, 1.3 | 60.0%, 1.1 | 76.6%, 4.7 |
| Bürokratt gov chat cases | 31 | 89.0%, 0.35 | 75.6%, 0.13 | 59.8%, 0.7 |
| Fairness (names from 18 traditions) | 2250 | 71.0% | 69.6% | 60.3% |

Highlights on corp_suite: isikukood and IBAN 100%, street, house, city and postcode 98 to 100%, surnames 96%, first names 89%.
Presidio has no isikukood or Estonian address support (isikukood 5%, streets 0%), but finds more names in news prose.
Full numbers per suite, type and format are in `results/scores.json`. The threshold sweep on the dev split is in `results/tau.json`.

## Benchmarks vs Bürokratt

On the same box and texts, Udukratt runs **~7× faster** than [Bürokratt Presidio-Anonymizer](https://github.com/buerokratt/Presidio-Anonymizer): 38 ms vs 256 ms median per document, 23 vs 3 docs/s. Its model is ~10 MB, against 2.2 GB.

Accuracy is mixed. Udukratt catches more PII in corporate and structured text (97.5% vs 73.5%). Bürokratt is better on news (94.8% vs 66.8%), chats and varied names.

Details: [BENCHMARKS.md](BENCHMARKS.md). Side-by-side examples: [SHOWCASE.md](SHOWCASE.md).

## Limitations

- Names in real prose are the weak spot: about a third of names in news text are missed.
- False alarms on technical text: bracketed or key-like words in logs (`[gateway-3]`, `WARN`), Confluence markup and CSV row ids
  are sometimes flagged. Logs average about 30 false alarms per document.
- Non-Latin scripts other than Cyrillic (Arabic, CJK, Hindi) are rarely caught.
- Training data is mostly synthetic, so in-distribution scores overstate real-world accuracy. corp_suite is synthetic too.
- The upstream session table keys placeholders on the raw string, so `Tamm` and `Tammele` get different placeholders.
- Passport and driving licence formats are assumptions.

## Repository

| Path | Purpose |
|---|---|
| `et/` | normalisation, transliteration, validators, deterministic and never-PII layer, encoder |
| `data/` | corpus builders: lexicon, synthetic chats, doc-style records (`build_docs.py`), EstNER, OCR forms, mixer |
| `train/` | vocab trim, training, ONNX 4-bit export |
| `eval/` | OpenPII-format suites and the scoring harness (`eval/harness`) |
| `work3/corp_suite/` | corporate document suite generator, scorer and data |
| `runtime/rampart-et.patch` | patch for upstream Rampart (commit 95798af): isikukood, IBAN, translit, never-PII, word snapping |
| `webapp/` | static browser demo (onnxruntime-web, JS port of the pipeline, parity tests) |
| `results/` | scores for v0.1 |

Model files are in the GitHub release, not in the repo.

## Run

    pip install -r requirements.txt
    apt install tesseract-ocr tesseract-ocr-est fonts-dejavu-core fonts-dejavu-extra
    ./run_pipeline.sh

Optional inputs: `ADS_CSV=<ADS address extract>` widens street and village lists. `COURT_IDS` adds court decisions; note that
Riigi Teataja's robots.txt disallows automated access to court decisions, so only use it with permission.
`SYNTH_N` and `OCR_N` set corpus sizes. Doc-style data: `python data/build_docs.py --n 20000 --out work/docs_train.jsonl`.

Webapp: copy `model_q4.onnx` and a `vocab.json` (the `model.vocab` of `tokenizer.json`) into `webapp/model/`, and the onnxruntime-web
wasm files into `webapp/vendor/`, then serve the folder statically. Parity: `python webapp/test/ref.py 0.5 && node webapp/test/parity.mjs`.

## Recipe parity

| Step | Upstream | rampart-et |
|---|---|---|
| Base model | nreimers/MiniLM-L6-H384-uncased | same |
| Head | 35 BIO labels, 17 types | same labels, same order |
| Normalisation | lowercase, NFKD, strip marks | same, plus Estonian-standard Cyrillic transliteration first |
| Deterministic layer | Luhn cards, US SSN, email, URL, IP | Luhn cards, isikukood (date and checksum), IBAN (mod 97), email, URL, IP. SSN removed |
| Premask | sentinels at train and serve time | same, decided by running the detector on the training text |
| Synthetic chats | 250k in-house, unpublished | slot-first generator, built-in and LLM-written templates |
| OCR documents | in-house, unpublished | rendered Estonian forms, degraded, Tesseract `est`, fuzzy-aligned |
| Public corpus | OpenPII 1.4M (no Estonian) | EstNER v1 and new (CC BY 4.0), court decisions (optional) |
| Vocab trim | 19,730 pieces | same algorithm, recomputed on the Estonian corpus |
| Training | 3 epochs, bs 32, lr 5e-5, wd 0.01, len 512, AdamW, best eval loss | same |
| Export | 4-bit MatMul plus INT8 embedding ONNX | same (MatMulNBits block 32 plus Gather UINT8) |
| Eval | upstream `eval/bench` on OpenPII rows | same harness, suites emitted in OpenPII row format |

## Attribution

Udukratt is derived from Rampart by National Design Studio (CC BY 4.0). Only a patch against upstream is included here, not upstream code.

Rampart model, runtime and eval: National Design Studio, CC BY 4.0. EstNER: TartuNLP, CC BY 4.0.
Bürokratt gov chat cases: buerokratt/Presidio-Anonymizer, MIT. Court decisions: Riigi Teataja public API.
`lexicon/lexicon.json` contains name lists harvested from EstNER (CC BY 4.0, TartuNLP) and Faker (MIT).
`samples/estner.jsonl` contains EstNER text (CC BY 4.0, TartuNLP). Comparison baseline: Microsoft Presidio (MIT).
