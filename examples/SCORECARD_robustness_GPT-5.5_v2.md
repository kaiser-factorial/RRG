# Validation Scorecard — v2 (Codex run, post-refinement)

*Operator-only. Grades the independent Codex run against the original investigation per `HIDDEN/REPLICATION_RUBRIC.md`. Numbering is the new 1–13 (Codex's); the original report's label is in the note. **v2** incorporates the four requested refinements (Q3, Q4, Q11, Q12). See `SCORECARD_GUIDE.md` for how this is produced and `SCORECARD_robustness_GPT-5.5_v1.md` for the pre-refinement snapshot.*

## Verdict legend

- **REPRODUCED** — same method, numbers match within tolerance.
- **CONVERGED** — different (defensible) method, same substantive conclusion (a pass; stronger robustness evidence than a same-method match).
- **DIVERGED** — conclusion or key number disagrees.
- **INCOMPLETE** — intended analysis not run (method gap / data limit).
- *FRAGILE* — original flagged the result as tentative.

## Scorecard

| Q | Topic | Verdict | Method vs. orig | Codex result (v2) | Original result |
|---|---|---|---|---|---|
| 1 | Exclusion bias *(orig Q1)* | **CONVERGED** | Different (χ²/Cramér's V + logit) | dropout-driven, no-current-type 88.3% excluded, V = .78; celibate/single > partnered | dropout-driven (84% of non-finishers); celibate ~2.5× partnered |
| 2 | Security vs exploration *(orig Q4)* | **REPRODUCED** | Same (composite correlation) | r = .436 [.40, .47] | r = +.44 |
| 3 | Response-style artifact *(orig Q12)* | **REPRODUCED** ⬆ | Same (external-proxy partial) | external-proxy partial **r = .307**; bound .31–.44 | external-proxy partial ≈ .32; bound .32–.44 |
| 4 | Within-scale vs joint dims *(orig Q5)* | **CONVERGED** ⬆ | Same family (per-block EFA → Tucker congruence; parallel-analysis factor counts) | intra-dyadic REN factor → RS_care \|c\| = .87; 11/16 within-factors map ≥.85; risky/specialized facets split | intra-dyadic RE → RS_care c = .93; 7/10 map 1:1; risk/multi facets split |
| 5 | Extreme needs = pathology? *(orig Q7)* | **CONVERGED** | Different (top-decile + incremental R²) | comp_SE × SCS r = .44; needs not reducible to pathology | SCS × exploration .42; security × ECR_Ax weak (.15); security ≠ anxiety |
| 6 | Ideal-type profiles *(orig Q6)* | **CONVERGED** | Different (planned contrasts vs ANOVA) | identical Ns; Poly−Mono multi-partner g = 3.43 | RE_multi η² = .56; poly defined by multi-partner, equal care/safety |
| 7 | Predict ideal type *(orig Q11)* | **REPRODUCED** | Same (CV multinomial) | balanced acc = .700, AUC .899 | balanced acc = .70 (5-class) |
| 8 | Fit → satisfaction *(orig Q8)* | **REPRODUCED** | Same (OLS interaction) | N = 1,467; interaction = 0.422, p = 8.4e-8 | interaction = +0.42, t = 5.38 |
| 9 | Misfit → wanting change *(orig Q15)* | **REPRODUCED** | Same (logistic + direction-specific) | multi-partner logit = 3.64, p = 1.6e-32 | multi-partner d = 1.91, AUC = .909 |
| 10 | Gender & age *(orig Q13)* | **CONVERGED** | Different (regression + FDR vs Welch t) | SE_multi largest gender gap (men higher); broad security flat | comp_SEC d = .05 (ns); SE_multi d = +.67 (men) |
| 11 | Psychopathy needs *(orig Q9)* | **CONVERGED** ✓ | Same family, now gender-adjusted | gender-adj SE_multi top-vs-bottom = 0.33, p = 9.5e-4 (shrinks from .46 raw but holds) | SE_multi d = +.35 gender-adjusted; casual+risk, not poly |
| 12 | Dark security / residual jealousy *(orig Q10)* | **REPRODUCED** ⬆ *(FRAGILE)* | Same once matched (top-vs-rest, adj comp_SEC + gender) | **b = 0.167, p = 0.019** | b = 0.167, t = 2.34, p = .019 |
| 13 | Queerplatonic extension *(orig Q14)* | **CONVERGED / N-A** | Same (forced by data) | PSN/PEN absent → opt-in only; n = 145 | PSN/PEN empty → opt-in only; n = 145 |

*(⬆ = upgraded from v1; ✓ = pending confirmation in v1, now confirmed.)*

## Tally (v2)

- **Reproduced: 6** (Q2, Q3, Q7, Q8, Q9, Q12)
- **Converged: 7** (Q1, Q4, Q5, Q6, Q10, Q11, Q13)
- **Incomplete: 0** · **Diverged: 0**

**All 13 questions now agree** — 6 by the same method, 7 by a different defensible method.

## What changed from v1

| Q | v1 → v2 | Why it moved |
|---|---|---|
| 3 | INCOMPLETE → **REPRODUCED** | Added an external-instrument response-style proxy; the interpretable partial (.307) reproduces the original (~.32). The earlier within-pool controls were correctly identified as over-corrective. |
| 4 | INCOMPLETE → **CONVERGED** | Clarifying that the fixed-factor rule applies only to the joint solution unblocked per-block EFAs. An independent EFA (different factor counts, chosen by parallel analysis) recovered the headline finding: within-relationship romantic exploration maps onto care/security. |
| 11 | CONVERGED (pending) → **CONVERGED (confirmed)** | Gender-adjusted contrasts: the SE_multi signal shrinks (.46 → .33) but survives — gender explains part, not all. |
| 12 | DIVERGED → **REPRODUCED** | The v1 disagreement was localized to reference-group + covariate choices. Under the matched specification, the estimate is *identical* (b = 0.167, p = 0.019). |

## The Q12 story (worth keeping for the paper)

Q12 is the clean demonstration of the rubric's divergence → second-pass logic. v1 showed an apparent disagreement (Codex's top-vs-middle contrast was null). Re-running under the original's specification — top decile vs. everyone else, adjusting for `comp_SEC` and gender — reproduced the original coefficient to three decimals. The "divergence" was an analytic-choice difference on a small, pre-flagged-fragile effect, not an implementation discrepancy. This is exactly what a localizing second pass is for, and it converts an ambiguous miss into an informative result.
