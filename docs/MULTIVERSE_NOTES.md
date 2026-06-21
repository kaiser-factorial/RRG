# Multiverse Option — working notes

*Notes on adding a multiverse (specification-robustness) component, including a starting spec grid for the LoveSmarter analyses. Status: pending — confirm with advisor whether his "omniverse" already covers this (if yes, don't duplicate; if "omniverse" = the correlation-scan, multiverse is a real gap to add).*

## What it is (and what it is NOT)

- **Multiverse analysis** (Steegen et al. 2016; cousin: specification-curve, Simonsohn et al.) = run the analysis across **all defensible analytic/data-processing choices** and report the *distribution* of results. It answers: *does the conclusion hold across the space of reasonable specifications, or only under the one path taken?*
- **Different axis from the RRG "Robustness" stage.** Two distinct robustness questions — keep separate, don't double-count:
  - **Multiverse = specification robustness** — one analyst, many analytic choices.
  - **RRG-Robustness = analyst/model robustness** — many independent models, free method choice.
  - A finding can survive one and fail the other.
- **Not** the exploratory correlation/Chatterjee scan ("omniverse"?), which is *lead generation*, not robustness.

## Placement in the flow

`omni scan → leads → expand question set → model 0 (Fable) analysis → MULTIVERSE → RRG (replication → robustness → generalization)`

- Multiverse sits as **its own component beside RRG, not a ladder rung.** Rationale: the DoF ladder varies *one axis at a time* (model → method → data); multiverse deliberately sweeps *many* choices at once, so it would break the ladder's single-axis logic. Keeping it separate preserves the ladder's clean structure.
- **Who runs it:** fine to use the same model as the investigation (multiverse's value is the spec grid, not analyst diversity). Cheap/scriptable → a good place for an OS model or plain scripted execution.

## Integrity rule (the crux)

**The spec grid must be PRE-SPECIFIED** — enumerated (and ideally signed off by the human/team) *before* seeing results. If the analyzing model picks which specs count as "reasonable" post hoc, it can flatter its own result. This is the thing reviewers scrutinize most. Pre-register the grid, then run all of it.

## The spec grid (starting template)

Each row is a decision node with the original's default + the defensible alternatives to sweep. Not every node applies to every question — each question uses its relevant subset. Full cross-product explodes combinatorially, so curate per question (or sample) and keep the grid auditable.

| Category | Decision node | Default (original) | Alternatives to sweep | Applies to |
|---|---|---|---|---|
| **Sample** | Bot/quality exclusion | `Delete_ZV ≤ 1` | stricter / looser / none | all |
| **Sample** | Missingness inclusion | drop > 10 of 170 missing | > 5 · > 20 · complete-case · keep-all+impute | all (sets N) |
| **Sample** | Missing-data handling | column-mean imputation | listwise · multiple imputation · FIML | factor/composite Qs |
| **Sample** | Special codes (e.g., "9") | treated as value | treat as missing | item-based Qs |
| **Measurement** | Factor scores | EFA k=8 promax (Bartlett) | **CFA-derived** · unit-weighted composites · regression scores | all factor-based Qs |
| **Measurement** | Rotation (if EFA) | promax | oblimin · geomin | factor derivation |
| **Measurement** | # factors (if EFA) | 8 | 7 · 9 · parallel-analysis | factor derivation |
| **Operationalization** | Rel-type collapse (4-class) | 1–4 Mono / 5–12,15 CNM / 13 Single / 14 Celib | alt. CNM boundary · rel-anarchy placement · drop ambiguous | Q1, Q6, Q8, Q9 |
| **Operationalization** | Ideal-type split (5-class) | Open = 5–7, Poly = 8–12,15 | alt. Open/Poly boundary | Q6, Q7 |
| **Operationalization** | High psychopathy | top decile `DirtyDozen_P` | absolute ≥ 4 · top quartile · continuous | Q11, Q12 |
| **Operationalization** | Multi-partner need | mean(RE_multi, SE_multi) | RE_multi only · SE_multi only | Q8, Q9 |
| **Operationalization** | Gender grouping | `Gender3cat` (cis-or-trans) | `SexGender9cat` cis-only · incl/excl NB+ | Q10, Q11, Q12 |
| **Test** | Group-difference test | Welch t / one-way ANOVA | Student t · Mann-Whitney / Kruskal-Wallis | Q6, Q10, Q11 |
| **Test** | Effect size | Cohen's d / η² | Hedges g · rank/robust effect size | group-diff Qs |
| **Test** | Correlation type | Pearson | Spearman · **Chatterjee ξ** | Q2, Q3, Q5 |
| **Test** | Regression estimator | OLS | robust (Huber) · bootstrap | Q8, Q9, Q12 |
| **Test** | Covariate set | per-question (e.g., gender) | + age · + structure · none | Q9–Q12 |
| **Test** | Multiplicity correction | Holm / FDR (where used) | none · Bonferroni · FDR | facet families (Q10, Q11) |
| **Test** | Classifier + CV (Q7) | multinomial logistic, 5-fold stratified | LDA · random forest · repeated CV | Q7 |
| **Test** | Nonlinearity probe (Q5) | decile means + quadratic | splines · GAM | Q5 |

## How to run / report

- For each question, run its applicable spec combinations; record the **headline statistic** for every spec.
- Report a **specification curve**: the headline effect sorted across specs, annotated with which choices drive the spread.
- Report the **fraction of specifications that preserve the conclusion** (sign + significance) — the headline robustness number.
- Flag any single choice that flips the result (a "load-bearing" researcher degree of freedom).

## Open / to confirm

- **Confirm with advisor:** does "omniverse" mean multiverse, or the correlation-scan? (Decides whether this is duplicate or a gap.)
- **CFA interaction:** once the CFA lands, "factor scores" node becomes EFA vs CFA vs composites — a natural, high-value multiverse axis.
- **Grid sign-off:** which alternatives count as "reasonable" needs team/advisor agreement (pre-registration).
- **Tractability:** curate per-question subsets or sample the grid; full cross-product is large.
