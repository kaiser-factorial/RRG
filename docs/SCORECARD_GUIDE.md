# Scorecard — Guide (how to produce and read it)

*Operator-only companion to `VALIDATION_PIPELINE.md`. The scorecard is the concrete output of **Stage 6 (Grading)** of the pipeline: it turns the validator's run into a per-question verdict against the original. This guide explains how to build one, how to read it, and how it versions across refinement rounds.*

## Where it sits in the pipeline report

`VALIDATION_PIPELINE.md` describes the protocol and (in its Results section) summarizes the outcome at a high level. The scorecard is the **evidence table behind that summary** — one row per question, with the verdict and the side-by-side numbers. Read order: pipeline doc (what we did and why) → scorecard (how each question landed) → this guide (how the scorecard was produced).

## Inputs you need

1. **Validator outputs** — the independent run (here `DataAnal/PANEL/Codex/`): `DYFA.md`/`SUMMARY.md` for conclusions, `raw/Q*_summary.json` + `raw/*.csv` for numbers, `docs/APPROACH.md` for the method it chose, and `V2_UPDATES.md` for any refinement round.
2. **Original results** — `origin_Fable-5/` (the `q*_results.txt`, `INVESTIGATION_SUMMARY.md`) = the answer key.
3. **The rubric** — `HIDDEN/REPLICATION_RUBRIC.md` for the verdict definitions and tolerances.
4. **The question map** — `HIDDEN/ORIGINAL_METHODOLOGY.md` translates the new 1–13 numbering to the original report's labels (the original ran Q1 then Q4–Q15).

## How to build a row

For each of the 13 questions:

1. **Map the number** (new Q → original label) so you're comparing like with like.
2. **Pull the headline statistic** from both sides — the same quantity where possible (effect size, key coefficient, accuracy, correlation), plus the N.
3. **Note the method each used** and whether they match.
4. **Assign a verdict** (below), applying the rubric's tolerances: direction must match; magnitude within the stated bands; relative orderings preserved.
5. **Write a one-line note** capturing any caveat (fragile, data-limited, reference-group sensitivity).

## Verdict definitions (from the rubric)

- **REPRODUCED** — same method, numbers match within tolerance.
- **CONVERGED** — a different but defensible method reaching the same conclusion. A pass, and stronger robustness evidence than a same-method match.
- **DIVERGED** — conclusion or key number disagrees.
- **INCOMPLETE** — the intended analysis wasn't run (method gap or data limitation).
- Tag **FRAGILE** where the original flagged the result as tentative, so a miss is expected, not damning.

## Handling divergences (the second-pass rule)

A **DIVERGED** or **INCOMPLETE** verdict is not the end state. Per the rubric:

- If the validator used a *different method*, re-run that one question with the original method pinned. Matches → it was a method difference (record as the method note); still differs → a genuine implementation/data discrepancy to investigate.
- If it was a *method gap* (e.g., an over-broad reading of a constraint), clarify the instruction and re-run.

Either way, the refinement produces the next version of the scorecard. (Q12 in this run is the worked example: DIVERGED at v1 → REPRODUCED at v2 once the specification matched.)

## Versioning

- Name each snapshot `SCORECARD_{stage}_{model}_v{n}.md`. `v1` is the first full pass; each refinement round bumps the version.
- Keep a **"What changed from v{n-1}"** table so the progression (and *why* each verdict moved) is auditable — this is itself a result for the paper.
- Earlier versions are kept, not overwritten: the v1 → v2 trajectory is evidence that the pipeline's localization step works.

## Current status

- `SCORECARD_robustness_GPT-5.5_v1.md` — first pass: 4 reproduced, 6 converged, 2 incomplete, 1 diverged.
- `SCORECARD_robustness_GPT-5.5_v2.md` — after refinements: 6 reproduced, 7 converged, 0 incomplete, 0 diverged (all 13 agree).
