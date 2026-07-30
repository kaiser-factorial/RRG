# Method-Free Validation Prompt — reusable (val_model_method-free)

*Operator-only. The staged prompt for a **method-free** validator: the model designs its own methodology (proposes → reconsiders → discusses → locks `APPROACH.md`), then executes. Blind to the original **methods and results**. This is the arm Codex ran; use this template to run additional method-free models (e.g., Laguna) for inter-model agreement. The fixed-protocol arm uses `OS_VAL_PROMPT.md` instead.*

## Modes (operator)

This template supports two methodology modes, toggled in the GUI (default: **with discussion**):

- **With discussion** — the model proposes (two passes), then you discuss and agree on the method before it locks `APPROACH.md` (Turns 3–5).
- **No discussion** — the model proposes (two passes) and locks its own `APPROACH.md`; you review and confirm it before the run, but don't debate the method (operator-reviewed lock).

Turns tagged `{mode:discuss}` or `{mode:nodiscuss}` appear only in that mode; untagged turns appear in both.

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

First, for context, read {STUDY_OVERVIEW} (the study's goals and design). {DATA_ORIENTATION}{#aux} {AUX_DATASET} is {AUX_NOTE}.{/aux}{#given_solution}

Important: {GIVEN_SOLUTION_NOTE}{/given_solution}{#additional}

You also have additional provided inputs — use them as given (do not re-derive what they supply):
{ADDITIONAL}{/additional}

Also read {HELD_CONSTANTS_FILE} — it lists the definitions I need held constant ({HELD_CONSTANTS_SUMMARY}) and what to report. Hold those definitions fixed, but the analysis method for each question is entirely your choice.

Side question before we go further: which file format is easiest for you to explore and ground yourself in the data structure — and is that the same one you'd prefer for the actual analysis?
```

## Turn 2 — Methodology proposal (two passes)

```
Now read the questions in {QUESTIONS_FILE}. Before any analysis, I'd like to settle methodology. Produce INVEST_METH.md outlining the analysis method you'd choose for each question, given the study context, the dataset structure, and the held-constant conventions. Take your time. Then do a second pass: revisit each question, reconsider whether your first choice was best, and revise INVEST_METH.md where warranted. When you're done, we'll discuss.
```

## Turn 3 — Discussion {mode:discuss}

```
Thanks! Let's discuss your choices. For some questions I may have had a different approach in mind; where that's the case, I'll describe my alternative and ask you to weigh it against yours — then explain, on the merits, whether yours or mine is more suitable. Document your reasoning in DISCUSS_METH.md so we can talk it through.

NOTE: I have no attachment to my own suggestions — my only preference is whichever approach makes the most sense for each question.
```

## Turn 4 — Discuss interactively *(operator-led; no fixed prompt text)* {mode:discuss}

Discuss the model's choices on their merits — there's no scripted message here. **Operator note (not for the model):** when *you, the researcher,* raise an alternative approach, draw it from your own judgment. Do not pull from the held-back original methodology — the model must never see it or learn it exists; importing it would re-anchor the model and undo the blinding.

## Turn 5 — Lock the methodology {mode:discuss}

```
Once we've agreed, document the final agreed approach (one entry per question) in APPROACH.md.
```

## Turn 5 — Lock the methodology (operator-reviewed) {mode:nodiscuss}

```
Now settle your methodology. Drawing on both of your passes, document your final approach — one entry per question, with a brief note on why each method fits — in APPROACH.md. Flag any question where you were torn between approaches. Before running anything, share APPROACH.md with me so I can review and confirm. I may ask you to reconsider a specific question, but the method choices remain yours.
```

## Turn 6 — Run the analyses

```
It's now time to perform the analyses! Please look into each question one by one, perform the analysis as we decided in APPROACH.md, check to make sure your results are accurate / make sense, and then document. I'd like a document with all the raw results for each question (RAW.md){#method_guide}, plus {METHOD_GUIDE_NAME}.md, which outlines your investigation via the {METHOD_GUIDE_NAME} method as explained in {METHOD_GUIDE_FILE}{/method_guide}.

For each question, include at least one visual chart/figure that clearly expresses that question's result(s). Isolate the figure-generating code so we can nudge the visuals later. A good per-question pipeline: Q1_analysis.py → Q1_raw.csv → Q1_fig.py → Q1_fig.png, applied from Q1 through Q{N_QUESTIONS}, so each step is independently controllable.

Once this is complete for all questions{#method_guide} and the {METHOD_GUIDE_NAME} is written{/method_guide}, add the figures{#method_guide} to the {METHOD_GUIDE_NAME}{/method_guide} by building a .docx report — the primary deliverable — titled {REPORT_NAME}.

Also create SUMMARY.md: a quick overview of the process, any significant results, and any doubts or issues you ran into. Let me know if you have any questions before you begin!
```

## Turn 7 — QA / self-check pass

```
Before we finalize, please run a quality-assurance pass over your own results:

- Re-check any question where a figure or a number looks off, surprising, or internally inconsistent — e.g., an N that doesn't match across steps, a confidence interval that excludes its own point estimate, or an effect direction that contradicts the descriptives. Trace it back through Q{n}_analysis.py to the data and confirm it's right.
- Confirm each question was executed as agreed in APPROACH.md; flag anything you had to change.
- Verify the held-constant definitions produced the expected group structure: report the Ns for {HELD_CONSTANT_GROUPS}.
- Record anything you corrected, anything still uncertain, and any deviation in SUMMARY.md.
```

## Operator reminders (do not paste)

- **Blind on methods AND results.** This arm's whole value is independent method design — keep `ORIGINAL_METHODOLOGY.md`, the originals, and other validators' runs out of reach throughout (including any discussion or review of the model's chosen method).
- **Two method-free models (Codex + this one) = inter-model agreement** within the method-free mode — a direct strengthening of the proposal, not a redundant run.
- **Outputs to `{OUTPUT_FOLDER}/`** so runs don't collide; grade against `{RESULTS_KEY}/` via `SCORECARD_GUIDE.md`. Expect a mix of REPRODUCED (same method) and CONVERGED (different method), as with Codex.
- **Model choice:** prefer nameable open-weights models (citable); avoid stealth/cloaked models for the reported arm.
```
