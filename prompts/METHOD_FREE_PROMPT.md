# Method-Free Validation Prompt — reusable (val_model_method-free)

*Operator-only. The staged prompt for a **method-free** validator: the model designs its own methodology (proposes → reconsiders → discusses → locks `APPROACH.md`), then executes. Blind to the original **methods and results**. This is the arm Codex ran; use this template to run additional method-free models (e.g., Laguna) for inter-model agreement. The fixed-protocol arm uses `OS_VAL_PROMPT.md` instead.*

## Fill in before running

- `{MODEL}` — the validator model (e.g., `poolside/laguna-m.1`).
- `{OUTPUT_FOLDER}` — a fresh per-model folder for its work (e.g., `Laguna/`), parallel to `Codex/`.
- `{REPORT_NAME}` — the final report filename (e.g., `Laguna_Report.docx`).

## Setup before the run

Share **exactly the all-arms package**: `STUDY_OVERVIEW_all.md`, `INVEST_Qs_OG_all.md`, `DYFA_Guidelines_all.pdf`, and `validation_subset/`. Send **nothing more**:

- **Do NOT** send `ANALYSIS_PROTOCOL_arm2.md` — that is the fixed-method arm; it would defeat the point of letting this model design its own methodology.
- **Do NOT** send any other validator's run (`Codex/`, `APPROACH_arm1.md`, `INVEST_METH_arm1.md`, their outputs) — it would anchor this model.
- **Do NOT** send `HIDDEN/`, `origin_Fable-5/`, or any `SCORECARD_*`.

One-line rule: **this model gets exactly what the first method-free model got, and nothing more.**

---

## Turn 1 — Context + data orientation

```
Hello! I'd like your help exploring some investigation questions for my research lab. I recently ran an investigation with another model and am now consulting you, independently, as an expert to help validate the initial findings. To keep your assessment unbiased, I'm deliberately not sharing how the original analyses were done — I want your own approach.

First, for context, read STUDY_OVERVIEW_all.md (the study's goals and design). Then orient yourself in the data, in validation_subset/: the main analysis sample is LS_analysis_main_N2074 (.sav / .csv / .pkl — all equivalent, use whichever is easiest); LS_exclusion_q1_N3003 is a larger pre-exclusion set used only for the first question. Variable definitions are in DATA_CODEBOOK.md; what the eight factor scores mean is in FACTOR_GLOSSARY.md; how the subset was built is in DATA_SUBSET_OVERVIEW.md.

Important: the factor solution is already validated and is given — the eight factor scores + composites are in FACTOR_SCORES_N2074.csv (keyed by ResponseId; merge them on), loadings in FACTOR_LOADINGS_170x8.csv. Use these as-is; do not re-derive the validated joint 8-factor solution. (You may run other factor analyses on the raw items where a question calls for it.)

Also read VALIDATION_INSTRUCTIONS.md — it lists the definitions I need held constant (relationship-type groupings, how "high psychopathy" is defined, etc.) and what to report. Hold those definitions fixed, but the analysis method for each question is entirely your choice.

Side question before we go further: which file format is easiest for you to explore and ground yourself in the data structure — and is that the same one you'd prefer for the actual analysis?
```

## Turn 2 — Methodology proposal (two passes)

```
Now read the questions in INVEST_Qs_OG_all.md. Before any analysis, I'd like to settle methodology. Produce INVEST_METH.md outlining the analysis method you'd choose for each question, given the study context, the dataset structure, and the held-constant conventions. Take your time. Then do a second pass: revisit each question, reconsider whether your first choice was best, and revise INVEST_METH.md where warranted. When you're done, we'll discuss.
```

## Turn 3 — Discussion

```
Thanks! Let's discuss your choices. For some questions I may have had a different approach in mind; where that's the case, I'll describe my alternative and ask you to weigh it against yours — then explain, on the merits, whether yours or mine is more suitable. Document your reasoning in DISCUSS_METH.md so we can talk it through.

NOTE: I have no attachment to my own suggestions — my only preference is whichever approach makes the most sense for each question.
```

## Turn 4 — Discuss interactively *(operator-led; no fixed prompt text)*

Discuss the model's choices on their merits — there's no scripted message here. **Operator note (not for the model):** when *you, the researcher,* raise an alternative approach, draw it from your own judgment. Do not pull from the held-back original methodology — the model must never see it or learn it exists; importing it would re-anchor the model and undo the blinding.

## Turn 5 — Lock the methodology

```
Once we've agreed, document the final agreed approach (one entry per question) in APPROACH.md.
```

## Turn 6 — Run the analyses

```
It's now time to perform the analyses! Please look into each question one by one, perform the analysis as we decided in INVEST_METH.md, check to make sure your results are accurate / make sense, and then document. I'd like a document with all the raw results for each question (RAW.md), plus DYFA.md, which outlines your investigation via the DYFA method as explained in DYFA_Guidelines_all.pdf.

For each question, include at least one visual chart/figure that clearly expresses that question's result(s). Isolate the figure-generating code so we can nudge the visuals later. A good per-question pipeline: Q1_analysis.py → Q1_raw.csv → Q1_fig.py → Q1_fig.png, applied from Q1 through Q13, so each step is independently controllable.

Once this is complete for all questions and the DYFA is written, add the figures to the DYFA by building a .docx report — the primary deliverable — titled Laguna_Report.

Also create SUMMARY.md: a quick overview of the process, any significant results, and any doubts or issues you ran into. Let me know if you have any questions before you begin!
```

## Turn 7 — QA / self-check pass

```
Before we finalize, please run a quality-assurance pass over your own results:

- Re-check any question where a figure or a number looks off, surprising, or internally inconsistent — e.g., an N that doesn't match across steps, a confidence interval that excludes its own point estimate, or an effect direction that contradicts the descriptives. Trace it back through Q{n}_analysis.py to the data and confirm it's right.
- Confirm each question was executed as agreed in APPROACH.md; flag anything you had to change.
- Verify the held-constant definitions produced the expected group structure: report the Ns for the relationship-type groups (4-class and 5-class), the gender groups, and the psychopathy bands.
- Record anything you corrected, anything still uncertain, and any deviation in SUMMARY.md.
```

## Operator reminders (do not paste)

- **Blind on methods AND results.** This arm's whole value is independent method design — keep `ORIGINAL_METHODOLOGY.md`, the originals, and other validators' runs out of reach throughout (including the Turn 4 discussion).
- **Two method-free models (Codex + this one) = inter-model agreement** within the method-free mode — a direct strengthening of the proposal, not a redundant run.
- **Outputs to `{OUTPUT_FOLDER}/`** so runs don't collide; grade against `origin_Fable-5/` via `SCORECARD_GUIDE.md`. Expect a mix of REPRODUCED (same method) and CONVERGED (different method), as with Codex.
- **Model choice:** prefer nameable open-weights models (citable); avoid stealth/cloaked models for the reported arm.
```
