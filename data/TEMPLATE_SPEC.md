# Template spec for LLM-written chat templates

You write user messages that Estonian residents send to a public-sector chatbot or helpdesk.
Every piece of personal data is a slot in curly braces. The pipeline fills slots with fake values,
declines Estonian names into the requested case, and derives exact labels from the slots.
Never write a real-looking name, code, number, address or e-mail as plain text.

## Output

One JSON object per line, written to the file named in your batch:

    {"lang": "et", "scenario": "<scenario id from the batch>", "text": "<message with slots>"}

`lang` is one of `et`, `ru`, `en`, `mixed`, `et_public`. Use `\n` for line breaks inside `text`.

## Slots

| Slot | Value | Case suffix |
|---|---|---|
| `{p1}` `{p2}` `{p3}` | full name of person 1, 2, 3 (p3 is p1's child, same surname) | yes |
| `{p1.g}` `{p1.s}` | given name only, surname only | yes |
| `{p1.rev}` | official order, e.g. `TAMM Jaan` or `Tamm, Jaan` | no |
| `{ik1}` `{ik2}` `{ik3}` | isikukood of p1, p2, p3 | no |
| `{phone}` `{phone2}` | phone number, any common Estonian format | no |
| `{email}` `{email2}` | e-mail of p1, p2 | no |
| `{iban}` `{card}` | bank account (IBAN), payment card | no |
| `{doc}` `{pass}` `{dl}` | ID-card number, passport number, driving licence number | no |
| `{kmkr}` `{plate}` | VAT number, vehicle registration plate | no |
| `{addr}` | complete address in a random Estonian format | no |
| `{st}` `{bld}` `{apt}` `{zip}` | street, building number, apartment number, postal code | `st` only |
| `{farm}` `{village}` `{vald}` | farm name (write `{farm} talu`), village, rural municipality | no |
| `{city}` `{city2}` `{county}` `{cityru}` | town, second town, county, town in Cyrillic | `city`, `city2` |
| `{agency}` `{date}` `{amount}` `{age}` `{rel}` | agency name, date, money amount, age, relation word | `agency` only |

Case suffixes are Estonian only and apply to the last word of the value:
`:g :p :ill :in :el :all :ad :abl :tr :ter :es :ab :kom`.
Example: `Kas {p2:all} saab toetust maksta?` becomes `Kas Mari Tammele saab toetust maksta?`.
In Russian and English use slots without a suffix and phrase the sentence so the nominative fits.

## Rules

1. Every template except `et_public` contains at least one person or identifier slot. `et_public` templates contain none.
2. No digits longer than four characters outside slots. No capitalised first names outside slots.
3. Write like real users: typos, missing õäöü, all lowercase, run-on sentences, voice-dictation phrasing,
   pasted form fields (`Nimi: {p1}\nIsikukood: {ik1}`), corrections (`vabandust, õige number on {phone2}`),
   values in the wrong field, repeated values, mixed languages.
4. Vary length from four words to several paragraphs. Vary who is writing (the person, a relative, a representative).
5. Include non-PII context the model must keep: agencies, amounts, dates, ages, statute references (`§ 12 lg 3`), case-unrelated numbers under five digits.
6. Do not copy a template already in the file. Change structure, not just words.

## Batch files

Each `batches/batch_NNN.md` names a language, scenario, writing styles and a count.
Write exactly that many lines to `batches/out/batch_NNN.jsonl`, then validate:

    python data/validate_templates.py batches/out/*.jsonl --out data/templates_llm.jsonl --rejects batches/rejects.jsonl
