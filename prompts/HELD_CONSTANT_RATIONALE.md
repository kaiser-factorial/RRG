# What We Hold Constant — and Why

*Grader-only metadoc (keep in HIDDEN). Explains the design logic behind the validation: what is fixed, what is free, what the model executes itself, and what it is never told. The model-facing version of the fixed list (definitions only, no rationale) lives in `VALIDATION_INSTRUCTIONS.md`.*

## The principle

A clean replication separates three things:

1. **Fixed definitions** — how each construct/group is *defined*. Held constant so both analyses measure the same thing. Otherwise a disagreement could just mean the two analyses sliced the data differently, which tells us nothing about whether the finding is real.
2. **Free method** — the *statistical test/model* applied to those constructs. Deliberately left to the model. A different method that reaches the same conclusion is the strongest evidence a finding is robust (this is the whole point of the exercise).
3. **Model-executed steps** — the model **applies the fixed definitions to the data itself** (computes thresholds, group membership, Ns). We hand over the *rule*, not the *result*. Verifying that the model reconstructs the right groups/Ns is part of what's being validated.

So: definitions are given as rules; the model does the slicing and chooses the test.

## What is held constant, item by item

| Held constant | Why | Notes / trade-off |
|---|---|---|
| **Sample & cleaning** (3,133 → 3,003 → 2,074 chain) | Deterministic and already validated; removes sample construction as a confound. | Given via the two data files; the model only re-derives counts to confirm. |
| **Factor scores (k=8) + composites** | The factor pipeline was validated separately. This exercise tests the analyses *on top of* the factors; if the model re-derived them, every downstream disagreement would be confounded by factor differences rather than the analysis. | Provided in `FACTOR_SCORES_N2074.csv`. Result-neutral. |
| **Relationship type — 4-class collapse** (Mono / CNM / Singledom / Celibacy) | 15 raw categories can be collapsed many ways; group-based results are incomparable unless the grouping matches. | Result-neutral grouping rule. |
| **Ideal type — 5-class split** (Open Mono = 5–7, Poly = 8–12 & 15) | Needed for the ideal-type questions; the CNM→Open/Poly split is a real definitional choice the model would otherwise guess at. Verified to reproduce the original group sizes exactly. | Result-neutral. |
| **"Partnered" = Mono or CNM** | Defines who is eligible for the satisfaction/fit analyses. | Result-neutral. |
| **Gender = Gender3cat** (man/woman cis-or-trans; NB+ separate) | Keeps the model from running a cis-only contrast; the registered prediction is specifically men vs. women. | Choice of grouping is not itself a finding. |
| **High psychopathy = top decile of DirtyDozen_P** | The Dirty Dozen has no clinical cutoff, so *any* threshold is arbitrary. Fixing it isolates "does the method replicate" from "was the cutoff chosen differently." | A definitional choice, not a result. The optional ≥ 4 absolute cutoff is a secondary robustness check, not required. |
| **Multi-partner need = mean(RE_multi, SE_multi)** | Used as the key predictor across the fit, change, and psychopathy questions; holding it steady keeps those apples-to-apples. | **Judgment call — see below. Decision: KEEP.** |
| **"Wants to change" = ideal type ≠ current type** | The only change-desire signal in this dataset; the operationalization is a choice worth fixing. | Mild: framing the outcome this way is part of the original design, not its result. |

## The multi-partner-need judgment call (decided: keep)

This is the one fixed definition that quietly **doubles as a finding**: that multi-partner needs are the load-bearing construct behind ideal relationship type, the fit effect, and the change motivation is *itself* one of the investigation's headline results. By handing the model a ready-made `mean(RE_multi, SE_multi)` predictor, we nudge it toward that construct rather than letting it discover the centrality on its own.

We are keeping it constant anyway, because:

- It makes the fit / change / psychopathy questions directly comparable on the same predictor, rather than leaving the predictor definition free to vary alongside the method.
- The nudge is partial, not decisive: the model still chooses the analysis and can fail to find (or can contradict) the effect even with the predictor handed to it. Convergence still has to be earned at the method level.

The cost to keep in mind while grading: a strong multi-partner result in those questions is *slightly* less impressive as independent corroboration than if the model had built the construct itself. If you ever want the stronger test, drop this one definition from `VALIDATION_INSTRUCTIONS.md` and let the model choose its own predictor — at the price of apples-to-apples comparison on those questions.

## What is deliberately NOT held constant

- **The statistical method** (test, model, estimator, assumption handling) for every question. This is the variable under study; see `REPLICATION_RUBRIC.md` for how to grade same-method (Reproduction) vs. different-method (Convergence) outcomes.

## What the model is NOT told

- **The original methods and results** (kept in this HIDDEN folder).
- **That the PSN/PEN queerplatonic columns are empty** — discovering that *is* the answer to question 13, so pre-telling it would hand over the result. The model receives the `RSN_QPSection` opt-in column and finds the rest itself.
