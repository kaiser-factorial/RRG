---
name: vp-robustness
description: >
  Prepare a Stage-2 (Robustness) run of the validation pipeline: assemble the
  package and the staged method-free prompt for a given validator model, so it
  designs its OWN methodology, blind to the original methods and results. Use
  when running the robustness stage (second rung of the ladder).
---

# vp-robustness — Stage 2 (Robustness) run preparation

Robustness tests whether a finding survives a *different defensible method*. The validator **designs its own approach** per question (it is not handed a protocol), blind to both the original **methods and results**. Convergence — a different method reaching the same conclusion — is the strong signal here.

This skill runs in the operator's environment to prepare one robustness run; the human executes it in the validator's native agent app.

## Inputs

- `MODEL` — the validator model (from the `robustness` roster in `vp_config.yaml`, e.g. `GPT-5.5`, `DeepSeek`).
- Derived: `OUTPUT_FOLDER = {MODEL}/`, `REPORT_NAME = {MODEL}_Report.docx`.

## Stage invariants (must hold)

- **Methodology: HIDDEN.** No methodology protocol may be in the package — not `ANALYSIS_PROTOCOL_OG.md`, not `_arm2`, not `ORIGINAL_METHODOLOGY.md`. The model must design its own.
- **Results: BLIND.** Never include `origin_Fable-5/`, `SCORECARD_*`, or anything in `HIDDEN/`.
- **Payload identical across models** — do not tailor the prompt to the model (that would confound the comparison).
- **Method choice is free and unsteered.** Never tell the model to use a different method, avoid the original's approach, or "think of something else." Independent convergence on the same method is a valid and informative outcome (method consensus + reproducibility), **not** a failure to test robustness — and forcing divergence makes any resulting change uninterpretable (you can't tell a fragile finding from a model using a method it judged inferior).
- **Gate:** run only after the replication stage is graded.

## Procedure

1. **Confirm the model** is in the `robustness` roster (type/license recorded). If two models run this stage, confirm ≥1 is open-weights.
2. **Assemble the send list** (per `vp_config.yaml` → stages.robustness.send): the `_all` files + the whole `validation_subset/` folder (hash-locked). **No methodology protocol.**
3. **Run the blinding linter** (`vp-blinding-lint`). For this stage it must confirm **no protocol of any kind is present** (the rule that keeps "design your own" honest), plus the standard withheld-file checks. Block until PASS.
4. **Deliver the staged turns** from `METHOD_FREE_PROMPT.md`, substituting `{MODEL}`, `{OUTPUT_FOLDER}`, `{REPORT_NAME}`:
   - Turn 1 — orient (context + data; method is the model's choice).
   - Turn 2 — propose methods per question (two passes) → `INVEST_METH.md`.
   - Turn 3 — discuss → `DISCUSS_METH.md`.
   - Turn 4 — discuss interactively. **Operator note (not for the model):** raise any alternative from your own judgment, *not* from `ORIGINAL_METHODOLOGY.md` — importing the originals re-anchors the model and breaks the blind.
   - Turn 5 — lock the agreed approach → `APPROACH.md`.
   - Turn 6 — execute (per-question pipeline, `RAW.md`, `DYFA.md`, `{REPORT_NAME}`, `SUMMARY.md`).
   - Turn 7 — QA self-check.
5. **Create the output folder** `{MODEL}/`.
6. **Record the chosen method per question** (from `APPROACH.md` and the reported "method you chose") — this feeds the cross-model method-choice distribution compiled in `vp-scorecard`.
7. **Write the provenance entry** (stage, model, files sent + hashes, prompt version, timestamp, lint result).

## Deliverable shape (returned into `{MODEL}/`)

`INVEST_METH.md`, `DISCUSS_METH.md`, `APPROACH.md`; then the per-question pipeline `Q1_analysis.py → Q1_raw.csv → Q1_fig.py → Q1_fig.png` (Q1–Q13); `RAW.md`; `DYFA.md`; `{MODEL}_Report.docx`; `SUMMARY.md`. Each question reports N + subgroup Ns, descriptive inputs, test statistic + effect size + 95% CI, and a one-sentence conclusion.

## Grading

Grade against `origin_Fable-5/` via `vp-scorecard` → a Stage-2 scorecard. Expect a **mix of REPRODUCED (same method chosen) and CONVERGED (different method, same conclusion)**; a DIVERGED result triggers the localize-second-pass (re-run that one question with the original method pinned). Record exact model name + license.

## Notes

- The defining difference from `vp-replication`: **no protocol is sent.** If a protocol ever appears in a robustness package, the linter must hard-fail.
- Two method-free models (e.g., GPT-5.5 + DeepSeek) give an inter-model agreement signal within the robustness stage.
- **Convergence is information.** Robustness is read *conditional on divergence*: where independent models choose *different* defensible methods, you test whether the conclusion survives; where they *converge*, you instead get a method-consensus + reproducibility result. Both are wins. The cross-model **method-choice distribution** (compiled in `vp-scorecard`) shows which questions are method-settled vs. method-ambiguous — a first-class finding. For fuller method coverage, use a *pre-specified multiverse arm* (operator-enumerated methods), never model coercion.
- A model that can't follow the clear, identical instructions is a *finding* — never hand-tune the prompt per model to "help" it.
