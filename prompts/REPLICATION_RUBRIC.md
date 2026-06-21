# LoveSmarter — Replication Rubric

*What counts as a successful independent replication of the **investigation results** (Q1, Q4–Q15). The factor solution underneath them is already validated and is treated as fixed (see §0). The goal is to reproduce the **structure, direction, and magnitude** of the findings — not identical trailing decimals. Different software, seeds, and imputation order can move the last digit or two without meaning anything; a replication succeeds when the substantive conclusions hold.*

## 0. The factor solution is a fixed input — do not re-derive it

The k=8 EFA was validated separately (the earlier MATLAB→Python work). This exercise validates the analyses built *on top of* those factors, so the factors are held constant:

- Use **`FACTOR_SCORES_N2074.csv`** (the 8 factor scores + 6 composites, keyed by `ResponseId`) as given inputs — merge them onto the data by `ResponseId`. **`FACTOR_LOADINGS_170x8.csv`** is the given loading matrix. These are confirmed identical to the investigation's own scores.
- Consequence: every question that takes factor scores as input is being checked at the **analysis level only**. A downstream disagreement therefore reflects the analysis, not the factors — which is exactly what we want.
- *Q4/Q5 caveat:* parts of these questions are *about* the factor solution itself (its factor-correlation matrix, and subscale-vs-joint congruence). Since the solution is fixed, treat the provided loadings as given there; the genuinely fresh pieces are the assumption-light cross-checks — composite correlations and the higher-order analysis run on the given scores.

## 1. Sample reconstruction (must match exactly)

Deterministic — should reproduce to the row:

- 3,133 total → **3,003** after `Delete_ZV ≤ 1` → **2,074** main sample (≤ 10 missing need items).
- Main-sample `ResponseId`s match `in_main_sample == 1`; 929 excluded by the missingness rule.

If any of these differ, reconcile the cleaning before interpreting anything downstream.

## 2. Two kinds of agreement — grade them differently

When the model's numbers differ from the original, the *first* question is always "same method or different method?" They are graded on different standards:

| | What it tests | Standard |
|---|---|---|
| **Reproduction** (same method as the original) | Was the original analysis implemented correctly / is it reproducible? | Tight numeric match, within the tolerances in §3. |
| **Convergence** (a different but defensible method) | Is the finding real, or an artifact of one analytic choice? | Whether the **conclusion** agrees — not the exact number. A different method that converges is *stronger* evidence the finding is real than a same-method match. |

Tag each question **REPRODUCED / CONVERGED / DIVERGED / N-A**. A "CONVERGED" is a pass.

## 3. Tolerances for direction and magnitude (apply to both kinds)

- **Sign / direction must match.** A correlation, group difference, or interaction that flips sign is a failure, not a rounding difference.
- **Magnitude within tolerance** (rules of thumb):
  - correlations *r*: within ≈ ±.05
  - standardized effects *d* / *η²*: within ≈ ±.10 (more slack for very large effects)
  - regression coefficients: same sign, overlapping confidence intervals
  - classification (balanced accuracy): within ≈ ±3 points
- **Relative ordering must hold** — the dominant predictor stays dominant; group rank-orderings (which ideal type scores highest/lowest) are preserved.

## 4. Require the intermediates, not just the headline

To make Reproduction-vs-Convergence judgeable, have the model report **method-agnostic intermediates** for each question, so you can compare *beneath* the final test — where two different methods still agree on what the quantities are:

- the analysis N and any subgroup ns
- group means **and SDs** (for group-difference questions)
- cross-tab counts (for categorical / relationship-type questions)
- the correlation/covariance among the inputs (for relationship questions)
- the test statistic **plus** effect size and CI (not just a *p*-value)

If two methods disagree on the headline but agree on the group means and effect sizes, the finding converged and the difference was just the test.

## 5. Divergence → second pass (localize the cause)

When a free-method result **DIVERGES**, re-run that one question with the **original method pinned**:

- **Matches after pinning** → it was a method difference. Likely both valid; score it as a convergence question, not a failure.
- **Still differs after pinning** → a genuine reproduction failure in the data or implementation. Investigate (cleaning, variable coding, factor-score merge).

This cleanly separates "chose a different approach" from "real discrepancy," instead of leaving an ambiguous mismatch.

## 6. Qualitative conclusion (the real test)

For each question, the one-sentence answer should match the original. Reproducing the number but reversing the interpretation is a failure; reproducing the interpretation with slightly different numbers is a success.

## 7. Fragile results — flag, don't fail

Treated as tentative in the original and not pass/fail criteria:

- Results near *p* = .05, single uncorrected post-hoc tests, and effects in small subgroups (e.g., Singledom/Celibacy ideal groups, n < 80) may not reproduce tightly — note divergence rather than scoring it as failed.
- Anything depending on the empty PSN/PEN columns cannot be replicated from this data; only the QP opt-in selection contrast is reproducible.

## 8. Suggested reporting format

Per question: **REPRODUCED / CONVERGED / DIVERGED / N-A**, the original vs. replicated key statistic side by side, the method the model used (and whether it matched the original), and a one-line note. A 13-row table makes the overall picture legible at a glance; add a "second-pass result" column for any DIVERGED rows that were re-run with the method pinned.
