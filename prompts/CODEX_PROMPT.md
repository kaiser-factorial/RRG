# Codex Prompt — Methodology Phase

*Operator-only (keep in HIDDEN). The staged prompt for the Codex / OS-model validation run. Blind by design: Codex is never shown the original methodology or results. Send these as sequential turns, adjusting the discussion step to Codex's actual output.*

---

## 2) METHODOLOGY [Codex] [OS Model]
*Goal: Agree upon `APPROACH.md`*

**Turn 1 — context + data orientation**

> Hello! I'd like your help exploring some investigation questions for my research lab. I recently ran an investigation with another model and am now consulting you, independently, as an expert to help validate the initial findings. To keep your assessment unbiased, I'm deliberately **not** sharing how the original analyses were done — I want your own approach.
>
> First, for context, read **`STUDY_OVERVIEW_all.md`** (the study's goals and design). Then orient yourself in the data, in the **`validation_subset/`** folder: the main analysis sample is **`LS_analysis_main_N2074`** (saved as `.sav`, `.csv`, and `.pkl` — all equivalent, so use whichever is easiest). A second file, **`LS_exclusion_q1_N3003`**, is a larger pre-exclusion set used only for the first question. For variable definitions see **`DATA_CODEBOOK.md`**; for what the eight factor scores mean, **`FACTOR_GLOSSARY.md`**; for how the subset was built, **`DATA_SUBSET_OVERVIEW.md`**.
>
> Important: the factor solution is already validated and is **given** — the eight factor scores + composites are in **`FACTOR_SCORES_N2074.csv`** (keyed by `ResponseId`; merge them on), loadings in **`FACTOR_LOADINGS_170x8.csv`**. Use these as-is; do **not** re-derive the factors.
>
> Also read **`VALIDATION_INSTRUCTIONS.md`** — it lists the definitions I need held constant (relationship-type groupings, how "high psychopathy" is defined, etc.) and what to report. Hold those definitions fixed, but the *analysis method* for each question is entirely your choice.
>
> {Side question: which file format is easiest for you to explore and ground yourself in the data structure — and is that the same one you'd prefer for the actual analysis? Do different analysis types favor different formats (dataset held equal, N ≈ 3,000)? Would you prefer a different format altogether?}

**Turn 2 — methodology proposal (two passes)**

> Now read the questions in **`INVEST_Qs_OG_all.md`**. Before any analysis, I'd like to settle methodology. Produce **`INVEST_METH.md`** outlining the analysis method you'd choose for each question, given the study context, the dataset structure, and the held-constant conventions. Take your time. Then do a second pass: revisit each question, reconsider whether your first choice was best, and revise `INVEST_METH.md` where warranted. When you're done, we'll discuss.

**Turn 3 — discussion**

> Thanks! Let's discuss your choices. For some questions I may have had a different approach in mind; where that's the case, I'll describe my alternative and ask you to weigh it against yours — then explain, on the merits, whether yours or mine is more suitable. Document your reasoning in **`DISCUSS_METH.md`** so we can talk it through.
>
> NOTE: I have no attachment to my own suggestions — my only preference is whichever approach makes the most sense for each question.

**Turn 4 — discuss interactively** *(no fixed text)*

**Turn 5 — lock it in**

> Once we've agreed, document the final agreed approach (one entry per question) in **`APPROACH.md`**.

---

## Operator reminders (do not paste to Codex)

- **Keep it blind.** Source any "alternative approach" you raise in Turn 3 from your own judgment, *not* from `ORIGINAL_METHODOLOGY.md`. Pulling the originals in re-introduces the anchor you're trying to avoid.
- **Why blind:** letting Codex propose cold yields a natural mix — questions where it independently picks the same method (reproducibility evidence) and questions where it differs (robustness evidence). That maps onto the Reproduction-vs-Convergence split in `REPLICATION_RUBRIC.md`.
- **Files Codex must NOT see:** everything in this HIDDEN folder (`ORIGINAL_METHODOLOGY.md`, `REPLICATION_RUBRIC.md`, `HELD_CONSTANT_RATIONALE.md`, the `validate*` tooling, this prompt). Pull HIDDEN out of the shared folder before pointing Codex at it.
- **Next phase:** after `APPROACH.md` is agreed, the analysis phase has Codex execute each question and report the intermediates listed in `VALIDATION_INSTRUCTIONS.md`; you grade against `REPLICATION_RUBRIC.md`.
