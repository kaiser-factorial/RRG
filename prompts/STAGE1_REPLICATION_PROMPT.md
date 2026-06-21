# Stage 1 — Replication Prompt (reusable)

*Operator-only. The prompt for **Stage 1 of the DoF ladder: Replication.** The model is given the **original** methodology (`ANALYSIS_PROTOCOL_OG.md`) and asked to **execute it exactly** on the same data — testing whether the original pipeline reproduces on a different model + software stack. Methodology is **revealed** here (it's the thing being replicated); the model is blind only to the original **results**. Run across several models (≥1 frontier + ≥1 open). Per the roster: **Gemini** (frontier) + **Nemotron** (open).*

## Fill in before running

- `{MODEL}` — the validator model (e.g., `Gemini`, `Nemotron`).
- `{OUTPUT_FOLDER}` — a per-model output folder: **`REPLICATE_{MODEL}/`** (e.g., `REPLICATE_Gemini/`, `REPLICATE_Nemotron/`).
- `{REPORT_NAME}` — the final report filename: **`{MODEL}_Report.docx`** (e.g., `Gemini_Report.docx`, `Nemotron_Report.docx`).

## Setup before the run

Share: the all-arms package (`STUDY_OVERVIEW_all.md`, `INVEST_Qs_OG_all.md`, `DYFA_Guidelines_all.pdf`, `validation_subset/`), **plus `ANALYSIS_PROTOCOL_OG.md`** (the fixed original methodology to replicate). Do **not** share `origin_Fable-5/`, `SCORECARD_*`, `ORIGINAL_METHODOLOGY.md`, `ANALYSIS_PROTOCOL_arm2.md`, or anything else in `HIDDEN/`.

> Blinding note: Stage 1 deliberately *reveals* the methodology (`_OG`) — that's what's being replicated. Only the original results stay hidden. The `_OG` protocol must **never** reach the Stage-2 (Robustness) models, which design their own methods.

---

## Turn 1 — Orientation

```
Hello! I'd like your help with a replication pass for my research lab. This is a focused job: you'll EXECUTE a fixed, pre-specified methodology exactly as written and report the numbers — you are not designing or choosing methods. An earlier analysis was run with a different model; the point of this pass is to check whether that exact methodology reproduces on a different model and software stack, so please don't look for or rely on any prior results.

For context:
- Read STUDY_OVERVIEW_all.md for the study, and INVEST_Qs_OG_all.md for the 13 questions.
- Orient yourself in the data in validation_subset/: the main sample is LS_analysis_main_N2074 (.csv / .pkl / .sav — identical, use whichever is easiest); LS_exclusion_q1_N3003 is a larger pre-exclusion set used only for the first question. Variable definitions are in DATA_CODEBOOK.md; the eight factor scores are explained in FACTOR_GLOSSARY.md.
- The factor scores + composites are in FACTOR_SCORES_N2074.csv (keyed by ResponseId; merge them on). The validated joint 8-factor solution is fixed — do not re-derive it. (You will run per-block factor analyses for one question, which the protocol specifies and permits.)
- Hold constant the definitions in VALIDATION_INSTRUCTIONS.md (relationship-type groupings, gender grouping, high-psychopathy cutoff, multi-partner need, composites). Apply them to the data yourself and report the resulting Ns.

Your methodology for every question is fixed and given in ANALYSIS_PROTOCOL_OG.md — you'll follow it exactly in the next step.

Please put everything you create — scripts, raw outputs, figures, reports — into a folder named {OUTPUT_FOLDER}.

For now: read everything above, confirm the data loads and merges as expected, and tell me if anything is unclear or any input seems missing. Do not start the analyses yet.
```

## Turn 2 — Execute the replication

```
Great — it's time to run the analyses. Work through the 13 questions one by one, performing each exactly as specified in ANALYSIS_PROTOCOL_OG.md. This is a replication: execute the methodology as written — do not redesign, "improve," or substitute methods. If a step is genuinely infeasible with the provided data, say so explicitly and explain why, rather than swapping in a different approach. Sanity-check each result, then document.

Put all outputs in {OUTPUT_FOLDER}. Deliverables:
- RAW.md — all raw results for each question.
- DYFA.md — your write-up via the DYFA method as explained in DYFA_Guidelines_all.pdf.
- For each question, at least one figure that clearly expresses its result(s), with the figure code isolated. Use this per-question pipeline: Q1_analysis.py → Q1_raw.csv → Q1_fig.py → Q1_fig.png, from Q1 through Q13.
- Once all questions are done and DYFA.md is written, embed the figures into the DYFA by building a .docx report — the primary deliverable — titled {REPORT_NAME}.
- SUMMARY.md — a quick overview of the process, significant results, and any doubts/issues (including anything you found infeasible).

Report, per question: the analysis N and any subgroup Ns; descriptive inputs (group means/SDs, cross-tabs, or input correlations); the test statistic, effect size, and a 95% confidence interval; and a one-sentence conclusion. Don't search for or rely on any prior results. Let me know if you have any questions before you begin!
```

## Turn 3 — QA / self-check pass

```
Before we finalize, please run a quality-assurance pass over your own results:

- Re-check any question where a figure or a number looks off, surprising, or internally inconsistent — e.g., an N that doesn't match across steps, a confidence interval that excludes its own point estimate, or an effect direction that contradicts the descriptives. Trace it back through {OUTPUT_FOLDER}/Q{n}_analysis.py to the data and confirm it's right.
- Confirm each question was executed exactly as written in ANALYSIS_PROTOCOL_OG.md. Flag — don't fix-by-redesign — any place you had to deviate or where a step was infeasible.
- Verify the held-constant definitions produced the expected group structure: report the Ns for the relationship-type groups (4-class and 5-class), the gender groups, and the psychopathy bands.
- Record anything you corrected, anything still uncertain, and any deviation in SUMMARY.md.

Keep the methodology fixed — this pass confirms the execution is correct, it does not change the approach.
```

## Operator reminders (do not paste)

- **This is replication: methodology revealed, results blind.** The model executes `ANALYSIS_PROTOCOL_OG.md`; never share `origin_Fable-5/`, the scorecards, `ORIGINAL_METHODOLOGY.md`, or the `_arm2` protocol.
- **Run ≥2 models** (roster: Gemini = frontier, Nemotron = open). Nemotron is free → re-run it a few times (`REPLICATE_Nemotron_run2/`, …) for a reproduction *distribution*.
- **Watch for redesign drift.** A model "improving" a step instead of executing it is the main failure mode here; treat any deviation as a grading note (or re-run), not a new method.
- **Grade** each model's output against `origin_Fable-5/` via `SCORECARD_GUIDE.md` → a **Stage-1 scorecard**. Since the methodology is fixed, expect REPRODUCED across the board; any miss localizes a model/stack difference, which is itself the finding.
- **Record exact model name + license** for each run (the open-models claim depends on it).
```
