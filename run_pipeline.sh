#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p ext work

[ -d ext/EstNER ] || git clone --depth 1 https://github.com/TartuNLP/EstNER.git ext/EstNER
[ -d ext/EstNER_new ] || git clone --depth 1 https://github.com/TartuNLP/EstNER_new.git ext/EstNER_new
[ -d ext/Presidio-Anonymizer ] || git clone --depth 1 https://github.com/buerokratt/Presidio-Anonymizer.git ext/Presidio-Anonymizer

python data/build_lexicon.py --estner ext/EstNER/EstNER_v1_train.json ext/EstNER_new/EstNER_new_train.json ${ADS_CSV:+--ads-csv "$ADS_CSV"}

TEMPLATES=()
[ -f data/templates_llm.jsonl ] && TEMPLATES=(--templates data/templates_llm.jsonl)
python data/build_synthetic.py --n "${SYNTH_N:-250000}" "${TEMPLATES[@]}" --out work/synth_train.jsonl
python data/build_synthetic.py --n 5000 --split heldout --seed 7 "${TEMPLATES[@]}" --out work/synth_heldout.jsonl

python data/build_estner.py --inputs ext/EstNER/EstNER_v1_train.json ext/EstNER_new/EstNER_new_train.json --out work/estner_train.jsonl
python data/build_estner.py --inputs ext/EstNER/EstNER_v1_test.json ext/EstNER_new/EstNER_new_test.json --rehydrate 0 --split heldout --out work/estner_test.jsonl

python data/build_ocr.py --n "${OCR_N:-20000}" --out work/ocr.jsonl

MIX=(synthetic=work/synth_train.jsonl ocr=work/ocr.jsonl estner=work/estner_train.jsonl)
if [ -n "${COURT_IDS:-}" ]; then
  python data/build_courts.py --fetch-ids "$COURT_IDS" --indir work/courts_raw --out work/courts.jsonl
  MIX+=(courts=work/courts.jsonl)
fi
python data/mix.py --inputs "${MIX[@]}" --val 10000 --outdir work/mix

BASE_DIR=$(python -c "from huggingface_hub import snapshot_download; print(snapshot_download('nreimers/MiniLM-L6-H384-uncased'))")
python train/trim_vocab.py --vocab "$BASE_DIR/vocab.txt" --corpus work/mix/train.jsonl --outdir work/tok
python train/train.py --train work/mix/train.jsonl --val work/mix/val.jsonl --tokenizer-dir work/tok --out work/run
python train/export.py --model work/run/best --out work/rampart-et --val work/mix/val.jsonl

python eval/build_suites.py --synth-heldout work/synth_heldout.jsonl --estner-test work/estner_test.jsonl \
  --gov-cases ext/Presidio-Anonymizer/tests/gov_chat_cases.py --outdir eval/data
echo "model: work/rampart-et   suites: eval/data   next: apply runtime/rampart-et.patch and run eval/bench"
