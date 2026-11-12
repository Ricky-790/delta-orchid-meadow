# Dispatch gate tool

`./run.sh` reads 52 interview quotes, the October gate register, and the output schema. It writes a schema-valid `output/result.json`. The tool is an evidence and planning prototype. It does not run the factory gate.

## How it works

`gatepass/register.py` calculates every count, date gap, duplicate, and time range from the register. `gatepass/interviews.py` contains the structured Gemini extraction step for the judgment work: turning answers into requirements, conflicts, constraints, and open questions. The model receives quotes and computed findings, never raw register rows. It retries an HTTP 503 twice with exponential backoff and random jitter, then tries Gemini 3.8 Flash and Gemini 2.5 Flash. If all calls fail, the tool stops without replacing the result.

`gatepass/build.py` rejects missing or deflection-only evidence for requirements, conflicts, constraints, and budget. It also rejects a conflicting requirement when no retained conflict names that source persona. Finally, it validates the result with `jsonschema` before replacing the output file. The tests cover representative register calculations, evidence rejection, and output validation.

## Decisions and rejected options

- Keep register analysis in code. A model should not calculate 123 movements, 17 chits, or a duplicate invoice number.
- Treat night chits as first-class, invoice-pending records. The register shows 17 chits, and only one carries an invoice number.
- Keep the prototype offline-first. The gate cabin has no network, and the budget is Rs 75,000 including hardware.
- Do not build a Tally integration. No invoice export or Tally access was supplied or authorised.
- Do not enforce the Rs 1,00,000 e-way rule from this register. It has no value, weight, or e-way bill column. The prototype can record or flag the rule only when authorised invoice data exists.
- Do not guess unanswered facts. The result lists them as open questions.

## Limits

A live run may word the interview extraction differently, although the code checks its evidence. The register was copied by hand, covers one month, and gives every vehicle a unique number. It cannot prove that the 17 chit movements were later invoiced. The fixed deflection list can miss new ways people avoid a question. The suggested offline workflow still needs a real gate device and authorised invoice data before anyone should treat it as a production system.
