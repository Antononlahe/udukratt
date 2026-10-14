# CLAUDE.md

Estonian rebuild of National Design Studio's Rampart PII redactor. Full context in HANDOVER.md.

## Working preferences

- Keep explanations brief and to the point.
- No comments in code unless explicitly asked.
- When in doubt, ask for more context or code rather than guessing.
- Favour clear logic and intent. Don't overengineer, but clever solutions are welcome.
- In prose, avoid em dashes and avoid splitting sentences with semicolons.

## Invariants

- Train/serve parity: any change to `et/deterministic.py`, `et/validators.py` or `et/normalize.py` must be mirrored
  in `runtime/rampart-et.patch`. Then regenerate `fixtures/parity.json` (`python fixtures/make_parity.py`), copy it
  to the patched upstream as `__tests__/fixtures/et-parity.json` and run both test suites.
- Keep `et/labels.py` `ID2LABEL` order identical to upstream (35 labels).
- Templates contain slots only, never real-looking values. Always pass LLM output through `data/validate_templates.py`.
- Held-out name and template partitions must never leak into training data.

## Commands

    pytest tests
    ./run_pipeline.sh
    python data/make_batches.py --batches 400
    python data/validate_templates.py batches/out/*.jsonl --out data/templates_llm.jsonl --rejects batches/rejects.jsonl

## Hardware

Local RTX 3060 12 GB for training. Synthetic templates via Claude Code or another cloud LLM.
