# Original Analysis Protocol (_OG) — Stage 1 (Replication) input + archive

*The **original** investigation's exact methodology, written as an execution protocol. Two roles: (1) the archival record of how the original analysis was done, and (2) the **fixed protocol the Stage-1 (Replication) models execute** — to test whether the original pipeline reproduces on a different model + stack.*

*Methods only; original results are withheld (in `origin_Fable-5/`). **Stage-1 only** — do **not** give this to the Robustness (method-free) arm; it would reveal the methodology that arm must design independently.*

*Execution rules: follow each question's method exactly as written; do not redesign or "improve" it. If a step is genuinely infeasible, say so explicitly rather than substituting. Hold constant the definitions in `VALIDATION_INSTRUCTIONS.md` (relationship-type groupings, gender grouping, high-psychopathy cutoff, multi-partner need, composites); compute group memberships yourself and report Ns. Use the provided factor scores/loadings as given — do not re-derive the joint 8-factor solution (you will run per-block EFAs for Q4, which is permitted). Report per question: N + subgroup Ns, descriptive inputs (means/SDs, cross-tabs, or input correlations), the test statistic, effect size, and a 95% CI, and a one-sentence conclusion.*

---

**Q1 — Exclusion bias.** Use the 3,003-row exclusion file. Recompute the ">10 missing of the 170 need items" rule. Cross-tabulate exclusion against: (a) survey completion (`Finished`); (b) current relationship situation collapsed to Monogamy/CNM/Singledom/Celibacy, with **"no RelSit answer (dropout)" kept as its own category**; and (c) per-item missingness within each of the four scale blocks, among finishers. Report exclusion rates by group and the sample composition shift (group shares) before vs. after exclusion.

**Q2 — Security vs. exploration.** Three convergent measurements on the analysis sample: (1) the **promax factor-correlation matrix Φ** of the k=8 solution, factors sign-aligned to their home blocks; (2) **Pearson correlations among the four unit-weighted block composites** (RS/SS/RE/SE), plus the single security-composite × exploration-composite correlation; (3) a **2-factor higher-order ML EFA** on the 8 factor scores — report its loadings and the higher-order factor correlation.

**Q3 — Response-style artifact.** Report the raw security × exploration composite correlation, then partial out a person-level response-style index **two ways**: (a) **elevation** = each respondent's mean across all 170 need items (flag as over-corrective, since the composites are part of it); (b) an **external proxy** = mean of standardized `DirtyDozen`, `Jealousy_Avg`, `SexDrive_Avg`, `LTMO_Avg10`. Report both partials and the resulting range.

**Q4 — Within-scale vs. joint dimensions.** Run a subscale EFA within each block with **fixed factor counts: RS = 2, SS = 2, RE = 3, SE = 3** (10 subscale factors). Compute **Tucker congruence** between each subscale factor and each of the 8 joint factors, restricted to that block's items. Identify 1:1 maps (|c| ≥ .85) vs. split/absorbed factors.

**Q5 — Extreme needs vs. pathology.** Correlate the 8 factor scores with the external scales (`ECR_Ax`, `ECR_Av`, `SCS`, `SOI`, `Compersion_Avg`, `SexDrive_Avg`, `LTMO_Avg10`, `Jealousy_Avg`, `DirtyDozen` + subscales, `PH9_Mean`, `SSSS11_Sum`). Probe nonlinearity **two ways**: (a) means of each external measure **by decile** of the security and exploration composites; (b) add a **quadratic term** to the linear fit and report the increment. Key targets: security × `ECR_Ax`; exploration × `SCS`; convergent checks SE_multi × `SOI`, RE_multi × `Compersion_Avg`, SS_access × `SexDrive_Avg`.

**Q6 — Ideal-type profiles.** Group `RelSit_IdealNow` into the 5 classes. For each factor/composite, **one-way ANOVA with η²** across groups. Plot group means on the (multi-partner love × care/safety) plane.

**Q7 — Predicting ideal type.** **5-fold stratified cross-validated multinomial logistic regression** (standardized 8 factor scores, class-balanced weights) predicting the 5 ideal-type classes; headline **balanced accuracy** (vs. chance and majority baselines). Attribution via single-factor and drop-one-factor runs. Also report the 3-class partnered-only version.

**Q8 — Fit → satisfaction.** Among **partnered** respondents, OLS: `RelSat_Avg5 ~ multi_partner_need + structure(CNM=1) + multi_partner_need × structure`. Report the interaction and the within-structure RE_multi × RelSat correlations (Monogamy vs. CNM) compared via **Fisher r-to-z**.

**Q9 — Misfit → wanting change.** `wants_change` = collapsed ideal ≠ collapsed current (Mono/CNM). Test whether multi-partner need separates changers from the content via **Welch t / Cohen's d, AUC, and gender-adjusted logistic regression** (OR per SD), in **both directions** (current monogamists → CNM ideal; current CNM → monogamy ideal). RelSat as triangulation.

**Q10 — Gender & age.** **Welch t-tests with Cohen's d**, men vs. women (`Gender3cat`), on all 10 need scores (NB+ reported descriptively); **Pearson correlations with age**. Secondary follow-up: break gender out with `SexGender9cat`, contrasting trans/NB subgroups against cis references with Holm and Benjamini-Hochberg correction.

**Q11 — Psychopathy needs.** Define high-psychopathy as the **top decile of `DirtyDozen_P`** (and an absolute cutoff ≥ 4 as robustness). Compare all 10 need scores: **Welch t, Cohen's d (95% CI), Holm correction, and gender-adjusted OLS** (need ~ high-P status + gender) — gender adjustment is part of the method, since the group skews male. First verify which Dirty Dozen items carry the psychopathy subscale (item-total correlations).

**Q12 — Dark security / residual jealousy.** OLS: `Jealousy_Avg ~ high-P status (top decile vs. everyone else) + comp_SEC + Gender3cat`. Report the gender-and-security-adjusted high-P coefficient with CI.

**Q13 — Queerplatonic extension.** Confirm the PSN/PEN item columns are empty (no structural replication possible from this export). Compare **QP opt-ins** (`RSN_QPSection == 1`) vs. everyone else on the factor scores via **Cohen's d**.
