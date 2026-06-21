# Validation Scorecard — v1 (Codex run)

*Operator-only (lives with the grader kit). Compares the independent Codex run against the original investigation, per the grading framework in `HIDDEN/REPLICATION_RUBRIC.md`. Numbering is the new 1–13 (Codex's); the original report's label is in the note. Status: **v1 — before the four requested refinements (Q3, Q4, Q11, Q12).***

## Verdict legend

- **REPRODUCED** — same method, numbers match within tolerance.
- **CONVERGED** — different (defensible) method, same substantive conclusion. *A pass, and stronger robustness evidence than a same-method match.*
- **DIVERGED** — conclusion or key number disagrees.
- **INCOMPLETE** — the intended analysis wasn't run (method gap / data limit); re-run pending.
- *FRAGILE* tag — the original flagged this result as tentative, so a miss is expected, not damning.

## Scorecard

| Q | Topic | Verdict | Method vs. orig | Codex result | Original result |
|---|---|---|---|---|---|
| 1 | Exclusion bias *(orig Q1)* | **CONVERGED** | Different (χ²/Cramér's V + logit + "missing" band) | Exclusion dropout-driven; no-current-type 88.3% excluded, V = .78; celibate/single > partnered | Dropout-driven (84% of non-finishers); celibate ~2.5× partnered |
| 2 | Security vs exploration *(orig Q4)* | **REPRODUCED** | Same (composite correlation) | r = .436 [.40, .47] | r = +.44 |
| 3 | Response-style artifact *(orig Q12)* | **INCOMPLETE** | Partial — only within-pool controls | raw .436; within-pool partial −.97 (flagged over-corrective); no informative estimate | raw .44; external-proxy partial ≈ .32; bound .32–.44 |
| 4 | Within-scale vs joint dims *(orig Q5)* | **INCOMPLETE** | Different — descriptive mapping, no EFA | item→factor block mapping only (read "don't re-derive" as "no EFA") | subscale-EFA → joint Tucker congruence; 7/10 map 1:1, 3 split/absorbed |
| 5 | Extreme needs = pathology? *(orig Q7)* | **CONVERGED** | Different (top-decile + incremental R²) | comp_SE × SCS r = .44; needs not reducible to pathology | SCS × exploration .42; security × ECR_Ax weak (.15); security ≠ anxiety |
| 6 | Ideal-type profiles *(orig Q6)* | **CONVERGED** | Different (planned contrasts vs ANOVA) | identical Ns; Poly−Mono multi-partner g = 3.43 | RE_multi η² = .56; poly defined by multi-partner, equal care/safety |
| 7 | Predict ideal type *(orig Q11)* | **REPRODUCED** | Same (CV multinomial) | balanced acc = .700, AUC .899 | balanced acc = .70 (5-class) |
| 8 | Fit → satisfaction *(orig Q8)* | **REPRODUCED** | Same (OLS interaction) | N = 1,467; interaction = 0.422, p = 8.4e-8 | interaction = +0.42, t = 5.38 |
| 9 | Misfit → wanting change *(orig Q15)* | **REPRODUCED** | Same (logistic + direction-specific) | multi-partner logit = 3.64, p = 1.6e-32 | multi-partner d = 1.91, AUC = .909 |
| 10 | Gender & age *(orig Q13)* | **CONVERGED** | Different (regression + FDR vs Welch t) | SE_multi largest gender gap (men higher); broad security flat | comp_SEC d = .05 (ns); SE_multi d = +.67 (men) |
| 11 | Psychopathy needs *(orig Q9)* | **CONVERGED** *(pending gender-adj)* | Same family, but not gender-adjusted | top-vs-bottom SE_multi g = .45; casual+risk, not poly | SE_multi d = +.35, RE_risky +.31 (gender-adjusted); RE_multi null |
| 12 | Dark security / residual jealousy *(orig Q10)* | **DIVERGED** *(FRAGILE)* | Different (3-band, all security facets, no gender) | top-vs-middle null (p = .22); top-vs-bottom p = .004 | high-P jealousy b = .167, p = .019 (controlling comp_SEC + gender) |
| 13 | Queerplatonic extension *(orig Q14)* | **CONVERGED / N-A** | Same (forced by data) | PSN/PEN absent → opt-in only; n = 145 | PSN/PEN empty → opt-in only; n = 145 |

## Tally (v1)

- **Reproduced: 4** (Q2, Q7, Q8, Q9) — same method, numbers match.
- **Converged: 6** (Q1, Q5, Q6, Q10, Q11, Q13) — different method, same conclusion.
- **Incomplete: 2** (Q3, Q4) — method gaps, addressed by the refinement prompt.
- **Diverged: 1** (Q12) — and the original flagged it fragile, so this is the rubric's "note, don't fail" case.

**Read:** 10 of 13 already agree (4 reproductions + 6 convergences). The two incompletes are fixable re-runs, not contradictions; the single divergence is a small, pre-flagged fragile effect that's sensitive to reference-group and covariate choices.

## Notable independent improvements by Codex

Several of Codex's *different* choices are arguably refinements, which strengthens the convergence story: planned contrasts (Q6), an explicit casual-vs-poly effect-difference test (Q11), log loss + nested model comparison (Q7), and a bottom-decile contrast band (Q11/Q12).

## Pending → v2

After the refinement run (Q3 external-style proxy; Q4 per-block EFA + congruence; Q11 gender-adjusted contrasts; Q12 top-vs-rest adjusted for security + gender), update Q3/Q4 from INCOMPLETE and confirm Q11/Q12. Also tighten `VALIDATION_INSTRUCTIONS.md` so "fixed factors" clearly refers only to the joint 8-factor solution (the Q4 gap traced to that wording).
