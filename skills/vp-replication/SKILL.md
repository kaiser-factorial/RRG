---
name: vp-replication
description: >
  Prepare a Stage-1 (Replication) run of the validation pipeline: assemble the
  blinded package and the fixed-method prompt for a given validator model, so it
  executes the ORIGINAL methodology exactly. Use when running or setting up the
  replication stage (the first rung of the degrees-of-freedom ladder).
---

# vp-replication — Stage 1 (Replication) run preparation

Replication tests whether the **original** analysis pipeline reproduces on a different model + software stack. The validator is **given** the original methodology and must **execute it exactly** (it does not design methods). It is blind only to the original **results**.

This skill runs in the operator's environment to prepare one replication run. It does **not** execute the analysis — the human runs the prepared prompt in the validator's native agent app.

## Inputs

- `MODEL` — the validator model name (from the `replication` roster in `vp_config.yaml`, e.g. `Gemini`, `Nemotron`).
- Derived: `OUTPUT_FOLDER = REPLICATE_{MODEL}/`, `REPORT_NAME = {MODEL}_Report.docx`.

## Stage invariants (must hold)

- **Methodology: REVEALED.** The fixed protocol `ANALYSIS_PROTOCOL_OG.md` (original methods) is *required* in the package — it is what's being replicated.
- **Results: BLIND.** Never include `origin_Fable-5/`, any `SCORECARD_*`, `ORIGINAL_METHODOLOGY.md`, the `_arm2` protocol, or anything in `factor_tooling/`.
- **Methodology payload is model-agnostic and identical across models** — do not tailor the prompt to the model (that would confound the comparison).
- Gate: only run after the prior ladder stage is graded (replication is stage 1, so no upstream gate; downstream robustness waits on this).

## Procedure

1. **Confirm the model** is in the `replication` roster and tagged with its type/license. If two models are run for this stage, confirm at least one is open-weights.
2. **Assemble the send list** (per `vp_config.yaml` → stages.replication.send):
   - the `_all` files: `STUDY_OVERVIEW_all.md`, `INVEST_Qs_OG_all.md`, `DYFA_Guidelines_all.pdf`
   - the whole `validation_subset/` folder (hash-locked — verify unmodified)
   - `ANALYSIS_PROTOCOL_OG.md`
3. **Run the blinding linter** (`vp-blinding-lint`) on the assembled package. It must PASS — in particular, confirm no withheld files and that `ANALYSIS_PROTOCOL_OG.md` is present (required) while no other protocol is. Block until PASS.
4. **Fill the prompt** from `STAGE1_REPLICATION_PROMPT.md`, substituting `{MODEL}`, `{OUTPUT_FOLDER}`, `{REPORT_NAME}`. Keep the wording identical across models.
5. **Create the output folder** `REPLICATE_{MODEL}/` for the validator's scripts, raw outputs, figures, and report.
6. **Write the provenance entry**: stage, model, files sent (+ hashes), prompt version, timestamp, lint result.
7. **Hand off**: deliver Turn 1 (orient) → Turn 2 (execute) → Turn 3 (QA) to the validator's agent app; the human pastes and attaches the package.

## Deliverable shape (what the validator returns, into `REPLICATE_{MODEL}/`)

Per-question pipeline `Q1_analysis.py → Q1_raw.csv → Q1_fig.py → Q1_fig.png` (Q1–Q13); `RAW.md`; `DYFA.md` (per `DYFA_Guidelines_all.pdf`); `{MODEL}_Report.docx`; `SUMMARY.md`. Each question reports N + subgroup Ns, descriptive inputs, test statistic + effect size + 95% CI, and a one-sentence conclusion.

## Grading

Grade the returned outputs against `origin_Fable-5/` via `vp-scorecard` → a Stage-1 scorecard. Methodology is fixed, so expect **REPRODUCED**; any miss localizes a model/stack difference (the finding). Record exact model name + license.

## Notes

- This skill's *orchestration* runs in the operator's Claude/Cowork environment (model-agnostic by construction). The *payload* it produces is the prompt + package the validator receives — keep that identical across all replication models.
- Do not let `ANALYSIS_PROTOCOL_OG.md` leak into a robustness (Stage 2) package; that stage forbids all protocols.
