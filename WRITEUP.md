# Write-up: dispatch gate tool

## What it does

`./run.sh` reads three files in `data/` (52 interview quotes, the October gate register, the output schema) and writes `output/result.json`. Two data paths. `gatepass/register.py` analyses the register in pure code and produces every number. `gatepass/interviews.py` makes one real LLM call (gemini-3.5-flash, temperature 0) that turns the quotes into requirements, conflicts, constraints, budget, plan and open questions, each citing quote references. `gatepass/build.py` then verifies the draft before anything is written: every cited quote must exist, no requirement may rest only on deflection quotes ("ask him", "money is someone's desk"), a confirmed requirement cannot have the persona "assumed", and the final file is validated against the schema with `jsonschema`. If validation fails, nothing is written.

## The one LLM call

The LLM step is the interview extraction, because reading a guard's evasion and an owner's blanket claim is judgment, not arithmetic. The register was never sent as raw rows; the model only sees findings that code computed, so it cannot invent a number that matters. All counts, duplicates, times and gaps come from `register.py`, and the tests recompute them independently.

## Decisions

- Register analysis is deterministic code; only the messy human answers go through the model.
- The cache (`data/llm_cache.json`) holds one real model run and is committed, so the tool reproduces its result without a key. The output file states whether the run was live or from cache.
- A claim that contradicts the register is marked `conflicting` and the register itself is named as the second party in the conflict.
- Column names for the register are read from `config/site.json`, not from the code, and the deflection patterns name no person, so a second factory's data can drop into `data/` unchanged.

## What we rejected

- A live Tally integration: no data release is authorised, the gate cabin has no network, and the budget is Rs 75,000 all-in.
- Letting the model compute register numbers: it would invent some.
- Enforcing the e-way rule: the register has no value column, so the tool can only state the rule as a requirement and flag that it is unverifiable from this data.
- Asking the three people more questions: every planned question was already answered in the quotes or is answered by the register, so no question budget was spent.

## Where it breaks

- The e-way rule cannot be enforced, only stated; there is no value, weight or e-way column in the register.
- Whether the 17 night-chit trucks were ever invoiced is unknown; the register shows only 1 of 17 chits later carrying an invoice number.
- The register was copied by hand and all 123 vehicle numbers are distinct, which is implausible; transcription reliability is an open question.
- The deflection filter is a fixed pattern list and will miss new phrasings. It also refuses the one quote where a refusal is itself the fact being reported ("I don't hand out the sales list"), which costs one constraint that the conflict entry still carries.
- Model output varies slightly between runs despite temperature 0; the committed cache pins one real run.
- The offline design is proposed, not tested on a real gate device.
