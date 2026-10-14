# Handover: rampart-et

Everything decided, found and built in the chat session that produced this repo.
Read this first, then CLAUDE.md for working rules.

## 1. Goal

Bürokratt's anonymizer (github.com/buerokratt/Presidio-Anonymizer) is weak. The US National Design Studio
released Rampart, a tiny on-device PII redactor. Build an Estonian Rampart with the same method, using only
public, pseudonymised and synthetic data. If full training is impossible, do as much preparation as possible.

## 2. Status

| Part | State |
|---|---|
| Data pipeline (lexicon, synthetic, EstNER, OCR forms, court decisions, mixer) | built and tested on samples |
| LLM template workflow (spec, batch generator, validator) | built and tested, no templates generated yet |
| BIO encoder, normalisation guard, vocab trim | built and tested with the real BERT-uncased vocab |
| `train/train.py`, `train/export.py` | written, never executed (no GPU or PyTorch in the build sandbox) |
| Quantisation path (MatMulNBits 4-bit plus Gather UINT8) | verified on a toy ONNX graph |
| Eval suites in OpenPII row format | built and tested |
| TypeScript runtime patch for upstream Rampart | applied to commit 95798af, 41 of 41 tests passing |
| Trained model | none yet |

## 3. Upstream Rampart findings

- Sources: github.com/nationaldesignstudio/rampart (commit 95798af), huggingface.co/nationaldesignstudio/rampart,
  npm `@nationaldesignstudio/rampart`. Licence CC BY 4.0.
- Model: nreimers/MiniLM-L6-H384-uncased with a token-classification head, 35 BIO labels over 17 entity types,
  vocab trimmed to 19,730 pieces, shipped as a 4-bit ONNX file of about 14.7 MB, run with transformers.js.
- Recipe from the model card: 3 epochs, batch 32, lr 5e-5, weight decay 0.01, max length 512, AdamW, eval each epoch.
- Normalisation: training text is pre-folded (lowercase, NFKD, combining marks stripped) so it matches what the
  uncased tokenizer does at runtime.
- Deterministic layer (`src/heuristics.ts`): Luhn cards, structurally valid US SSN, email, URL, IPv4, IPv6, MAC.
  Matches are replaced with sentinel tokens such as `[SSN]` before the model sees the text, in training and at runtime.
- Span merge (`src/policy.ts`): on containment the longer span wins.
- Data: about 250k messy synthetic conversations and an OCR'd document corpus (both in-house, unpublished) plus
  ai4privacy OpenPII 1.4M (no Estonian).
- The repo contains runtime, eval and whitepaper only. There is no training code. The recipe here is reconstructed.
- Upstream fairness suite: Russian names reached 2.4% recall. This is why rampart-et transliterates Cyrillic.
- Bench (`eval/bench/run.ts`) reads OpenPII rows `{uid, language, source_text, privacy_mask: [{label, start, end, value}]}`.
  `eval/bench/labels.ts` maps OpenPII labels to Rampart labels. Unmapped labels count as public (must be kept).
  CLI: `bun eval/bench/run.ts --data <jsonl> --out <dir> --model <path or id>`.
- `model/tokenizer.json` in the repo is a git-lfs pointer. The standard BERT-uncased vocab has md5
  `64800d5d8528ce344256daf115d4965e` (30,522 lines).

## 4. Bürokratt findings

- Presidio with Estonian recognizers. Current NER model `buerokrattRIA/xlm-roberta-NER-syntheticGov`.
- Isikukood regex has no checksum validation.
- `tests/gov_chat_cases.py` (MIT) holds 31 gold-labelled Estonian government-chat cases with traps.
  Gold types: ORGANIZATION 28, PERSON 18, PHONE_NUMBER 11, DATE_TIME 8, LOCATION 7, GPE 7, EE_PERSONAL_CODE 6,
  EMAIL_ADDRESS 5, IBAN_CODE 3, EST_ID_DOC 3, CAR_NUMBER 3, IP_ADDRESS 3, URL 1, CREDIT_CARD 1, CRYPTO 1.
- Their own findings note that Estonian case endings survive outside placeholders and that plate patterns cause false positives.

## 5. Estonian data sources

| Source | Use | Licence or access |
|---|---|---|
| github.com/TartuNLP/EstNER and EstNER_new | real text, PER/GPE/LOC relabelled, names rehydrated | CC BY 4.0 |
| Riigi Teataja API `https://www.riigiteataja.ee/public-api/api/v1/kohtuteave/kohtulahendid/{id}/file` | pseudonymised decisions refilled with fake values | public, fetch slowly (site has a robot trap) |
| ADS address extract, xgis.maaamet.ee/adsavalik | street and village lists | open data, column names unverified |
| Faker `et_EE`, `ru_RU`, `uk_UA` and others | names, fairness suite | MIT |
| EstNLTK 1.7.5 Vabamorf | name declension | pip `estnltk` |
| tartuNLP/EstBERT_NER_v2 | possible teacher for unmasked names in court text | not used yet |

EstNER `ner_1` label counts (v1 plus new, train): PER 9,304, ORG 7,022, GPE 5,035, DATE 3,657, PROD 3,545,
TITLE 2,261, LOC 1,161, MONEY 989, TIME 815, EVENT 640, PERCENT 409.

Court decisions replace parties with letters or initials, often with a case ending glued on (`Xi` genitive,
`Yle` allative, `Yga` comitative), and mask fields with `xxxx`. Judges and some defendants appear with real names.

## 6. Design decisions

- **Head unchanged.** The 35-label head keeps the same order, so the upstream TS runtime works with a small patch.
- **Isikukood is deterministic.** It gets its own label `ISIKUKOOD` (birth date plus two-pass mod-11 checksum) and is premasked like SSN upstream.
- **IBAN is deterministic.** It's validated with mod 97, and EE must be exactly 20 characters. It's labelled `BANK_ACCOUNT`, and a trailing word is backed off on failure.
- **US SSN rule removed.** It would fire on Estonian 9-digit numbers such as KMKR digits and reference numbers.
- **Digit runs are split into separator-aligned windows.** This catches `38001085718 51234567`, which upstream misses, without matching inside a longer unbroken number.
- **Premasking runs the detector on training text.** Whatever the detector misses falls back to a model label, for example an invalid-checksum isikukood becomes `GOVERNMENT_ID`. Training and runtime are symmetric by construction.
- **Cyrillic is transliterated first.** It uses the Estonian standard (Елена Смирнова becomes Jelena Smirnova) before folding. As a side effect, Cyrillic look-alike letters inside Latin words fold to Latin.
- **Plates and ROUTING_NUMBER.** Licence plates map to `GOVERNMENT_ID`. `ROUTING_NUMBER` stays in the head but is unused.
- **Case numbers are redacted.** They are redacted as `GOVERNMENT_ID` (Rampart semantics), so the Bürokratt trap `3-21-1234` is dropped from retention scoring.
- **Synthetic data is slot-first.** PII values are sampled, names are declined with Vabamorf (noun synthesis first, proper-noun fallback) and labels come from the slots. Only the last name component is declined, matching Estonian usage (`Jaan Tammele`).
- **The LLM writes templates, never values.** Any LLM, including cloud ones, is safe because nothing it writes is real PII.
- **Held-out splits.** 10% of every name, street and village list is reserved for evaluation. One in seven templates (by hash) is reserved.
- **Vocab trim happens before training** (`keep_ids.json`), so training and runtime tokenisation are identical. Upstream may have trimmed at export.

## 7. Hardware conclusions

- **RTX 3060 12 GB is enough.** Training in bf16 needs a few GB, and about 300k rows over 3 epochs (about 100M tokens) should take well under an hour.
- **Local LLM on the 3060.** Only 8 to 12B models in 4-bit fit (EuroLLM-9B-Instruct, Gemma), and their Estonian is mediocre. That was superseded: templates will be written with Claude Code or another cloud LLM.
- **CPU training is possible.** It needs under 4 GB RAM, and more RAM does not help. Expect half a day to two days on an 8 to 16 core desktop.
  - Use `--group-by-length`.
  - Set `OMP_NUM_THREADS` to physical cores.
  - Do a pilot run first.
  - bf16 on CPUs with AMX or AVX-512 BF16 needs a small flag in `train.py`, which is not added yet.
- **Free cloud GPU.** A Kaggle or Colab T4 would finish the full run in 1 to 2 hours. The data is non-sensitive.

## 8. Verified in the build sandbox

- `pytest tests`: 5 passed. These cover parity fixture, checksums, transliteration, offset maps and span integrity.
- Patched upstream: heuristics, premask and new parity tests, 41 of 41 passed. Python and TypeScript produce identical spans and masked text on `fixtures/parity.json`.
- **Synthetic generator:** about 600 rows per second on one core.
- **EstNER builder:** 2,938 train, 479 dev and 452 test rows.
- **OCR builder:** 68 of 68 gold values aligned on a 6-form sample.
- **Court refiller:** works on a pseudonymised sample. The header is dropped and case endings are preserved.
- **Vocab trim on a 6k-row sample:** 6,867 pieces kept with 99.8% token coverage. The full corpus will need the 19,730 target.
- **Toy quantisation:** MatMul became MatMulNBits and Gather became DequantizeLinear, with the file shrinking from 2.1 MB to 0.48 MB.

## 9. Next steps

1. `pip install -r requirements.txt`, `apt install tesseract-ocr tesseract-ocr-est`, then `pytest tests`.
2. Templates: `python data/make_batches.py --batches 400`. Have Claude Code process `batches/batch_*.md` per
   `data/TEMPLATE_SPEC.md`, then `python data/validate_templates.py batches/out/*.jsonl --out data/templates_llm.jsonl --rejects batches/rejects.jsonl`.
3. Pilot: `SYNTH_N=30000 OCR_N=2000 ./run_pipeline.sh` with `--epochs 1` in the train step. Check per-label recall printed by `train.py`.
4. Full run: `./run_pipeline.sh`. On first failure in `train.py` or `export.py`, fix against the traceback (these were never executed).
5. Runtime: clone upstream, `git checkout 95798af`, `git apply runtime/rampart-et.patch`, then run `eval/bench/run.ts` on each suite in `eval/data`.
6. Compare with Bürokratt on `gov_chats.jsonl` by running their service on the same 31 cases.
7. Open decisions:
   - A stem-aware session-table key, so that `Tamm` and `Tammele` share a placeholder.
   - Verify the passport (assumed `K` plus 7 digits) and driving licence formats.
   - Verify the ADS CSV columns.
   - Add a CPU bf16 flag.
   - Optionally use EstBERT_NER_v2 as a teacher for real names in court text.

## 10. Known limitations

- **Name lists.** EstNER-harvested lists include foreign public figures and a few mis-lemmatised surnames, so `origin=est` is loose. The fairness suite uses Faker lists only.
- **Russian templates.** They use nominative names only, and verb gender may not match the name.
- **Court chunks are filtered.** Chunks with an unlabelled lexicon first name are skipped rather than relabelled.
- **Offsets differ by language.** Python offsets are code points and JS offsets are UTF-16 units. Each side is internally consistent.
- **Library versions.** `train.py` needs transformers 4.46 or newer (`processing_class`, `eval_strategy`). `export.py` passes `dynamo=False` to `torch.onnx.export` when supported.

## 11. Repo map

| Path | Purpose |
|---|---|
| `et/normalize.py` | transliteration, folding, premask view with raw offset maps |
| `et/validators.py`, `et/deterministic.py` | Estonian deterministic layer (Python mirror of the TS patch) |
| `et/morph.py` | Vabamorf declension |
| `et/values.py`, `data/seed.py` | PII samplers and gazetteers |
| `et/templates.py`, `et/synth.py` | built-in templates, slot-first generator with noise |
| `et/labels.py`, `et/encode.py` | label schema, BIO encoding with premask and drift guard |
| `data/build_*.py`, `data/mix.py` | corpus builders and cumulative mixer |
| `data/TEMPLATE_SPEC.md`, `data/make_batches.py`, `data/validate_templates.py` | LLM template workflow |
| `train/trim_vocab.py`, `train/train.py`, `train/export.py` | vocab trim, training, ONNX q4 export |
| `eval/build_suites.py` | synth_heldout, estner_test, gov_chats, fairness suites |
| `runtime/rampart-et.patch` | upstream TS runtime changes and tests |
| `fixtures/` | Python/TS parity cases |
| `samples/` | small outputs of each builder for inspection |
