# corp_suite

418 synthetic Estonian corporate documents (19 formats x 22), held-out lexicon split, exact gold spans plus hard negatives.

    python work3/corp_suite/gen.py     # writes corp_suite.jsonl (seed 2026)
    python work3/corp_suite/score.py   # run-3 q4 ONNX, rules + model, 126-token chunks; writes results.json, errors.json, predictions.json

Row: {uid, format, text, spans:[{start,end,label,value}], negatives:[{start,end,kind,value}]}. Offsets are code points.
