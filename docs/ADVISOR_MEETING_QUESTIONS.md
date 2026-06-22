# Advisor Meeting — Decisions Needed

These questions are ordered by how directly they block the next validation runs.

## 1. CFA and measurement-model basis

1. Does the forthcoming CFA **confirm the existing eight-factor structure**, or
   does it define a new structure that should replace and re-base the prior work?
2. What exact artifacts will be available: model specification, loadings, factor
   scores, fit statistics, covariance matrix, scoring coefficients, and/or code?
3. Should validators receive fixed respondent-level factor scores, fixed loadings
   with instructions to score them, or a fully specified CFA that they fit
   themselves?
4. Is the measurement model fixed across all three validation stages, including
   generalization, or does any stage reopen it?
5. If a new CFA changes the factor basis, should every prior validation run,
   including GPT-5.5 robustness, be rerun?
6. Which CFA diagnostics and acceptance criteria should be reported before the
   downstream validation begins?
7. Are we comfortable distributing the verified CSV/Parquet derivatives and
   metadata, or should the original `.sav` also travel in each validator package?

## 2. What should “generalization” mean here?

1. What data variation would provide meaningful evidence for this study?
   - a preregistered holdout from the current sample;
   - repeated train/test or cross-validation splits;
   - bootstrap/subsample stability;
   - a separate LoveSmarter wave or external sample;
   - a sequence of these, treated as different strengths of evidence?
2. Is a split of the existing sample genuinely **generalization**, or should it be
   described more narrowly as out-of-sample stability until a new sample exists?
3. Should Stage 3 execute:
   - the original fixed method;
   - the strongest method selected during robustness;
   - each validator's freely chosen method;
   - both a fixed-method and method-free analysis?
4. Should all 13 questions enter Stage 3, or only findings that first replicate and
   pass robustness?
5. What is the success criterion for “generalizes”: same direction, comparable
   effect size, confidence-interval overlap, predictive performance, or a
   question-specific rubric?
6. How should the fixed measurement model be transported to new data? If fixed
   loadings are scored onto a new sample, what invariance checks are required?
7. If no independent wave is currently available, should we implement the
   holdout/resampling machinery now or leave Stage 3 explicitly pending?

## 3. Multiverse versus “omniverse”

1. When you say **omniverse**, do you mean a broad lead-finding scan over the
   correlation matrix, a specification multiverse, or both?
2. If it is a lead-finding scan, is it exploratory work beside the validation
   ladder rather than another validation stage?
3. Do you also want a formal multiverse/specification-curve analysis over plausible
   cleaning rules, construct definitions, covariates, and estimators?
4. Which choices should be treated as legitimate analytic degrees of freedom, and
   which definitions must remain fixed for comparability?

## 4. Model roster and execution

1. Is the proposed mix of at least one frontier and one open-weights model per
   stage sufficient for the paper's claim?
2. Which exact model versions should be frozen and cited at run time?
3. Do repeated runs of an inexpensive open model add useful evidence about model
   stochasticity, or is one deterministic run per model sufficient?
4. Are API/native-agent differences acceptable as part of the software stack, or
   should execution be standardized more tightly across models?

## 5. Paper scope and reporting

1. Is the primary paper contribution the validation ladder itself, the LoveSmarter
   worked example, or both with equal weight?
2. What minimum empirical completion is needed before drafting/submission: Stages
   1 and 2 across the roster, or a completed Stage 3 as well?
3. Which aggregate results matter most: per-finding validation depth, cross-model
   agreement, reproduction versus convergence rates, method-choice distributions,
   or cost/time comparisons?
4. Should the paper present the GPT-5.5 first-pass divergence and targeted
   refinement as the main worked example of discrepancy localization?
5. Are there funder, data-sharing, authorship, or preregistration constraints that
   should shape the next implementation decisions?

## Decisions to leave the meeting with

- Approved measurement-model basis and artifact list.
- Whether prior validation runs must be rerun.
- Operational definition of Stage 3 data variation.
- Stage 3 method policy and success criteria.
- Meaning and placement of “omniverse” versus multiverse.
- Final model roster and minimum run count.
- Minimum empirical package required for the paper.
