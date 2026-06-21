# Original Investigation — Methodology by Question

*Grader-only reference (keep in HIDDEN). For each question, this records **how the original investigation answered it** — design, variables, sample, and key analytic choices — using the new 1–13 numbering from `INVEST_Qs_OG_all.md`. The original report's label is noted in parentheses. Results are intentionally omitted; this is the method key you compare the validation model's approach against. Source scripts referenced live in `origin_Fable-5/` (`q*.py`, `q5q8_build_cache.py`).*

## Shared setup (applies throughout unless noted)

- **Analysis sample:** N = 2,074 (`Delete_ZV ≤ 1`, then ≤ 10 missing of the 170 need items, column-mean imputed). One row = one respondent.
- **Factor scores:** sign-aligned promax factor scores from the validated k = 8 ML EFA (`RS_care, RS_merge, SS_safety, SS_access, RE_risky, RE_multi, SE_kink, SE_multi`), Bartlett estimates. **These are now provided as fixed inputs** (`FACTOR_SCORES_N2074.csv`).
- **Composites:** unit-weighted block means (`comp_RS/RE/SS/SE`); `comp_SEC` = mean(comp_RS, comp_SS); `comp_EXP` = mean(comp_RE, comp_SE).
- **Relationship-type collapse:** `RelSit_*` codes 1–4 → Monogamy; 5–12 & 15 → CNM; 13 → Singledom; 14 → Celibacy. "Partnered" = Monogamy or CNM.
- **Multi-partner need** (used in several questions) = mean of RE_multi and SE_multi.

---

## 1. Does the missing-data exclusion rule bias the sample? *(orig. Q1)*

Recomputed the missingness rule on **all 3,003** post-`Delete_ZV` respondents (not the 2,074). Cross-tabulated exclusion status (n = 929 dropped) against: (a) survey completion (`Finished`), (b) current relationship situation collapsed to Monogamy/CNM/Singledom/Celibacy, treating **"no RelSit answer" as its own dropout category** rather than discarding it, and (c) per-item missingness within each of the four scale blocks, among finishers only. Also compared sample composition (share of each relationship group) before vs. after the exclusion. Script: `q1_missingness_bias.py`.

## 2. Are security and exploration separate, opposed, or related? *(orig. Q4)*

Triangulated with three convergent measurements on the same sample: (1) the **promax factor-correlation matrix (Φ)** of the k = 8 EFA, factors sign-aligned to their home blocks (alignment required because promax signs are arbitrary); (2) **Pearson correlations among the unit-weighted scale composites** (RS/SS/RE/SE block means), plus the single security-composite × exploration-composite correlation; (3) a **2-factor higher-order ML EFA** on the 8 first-order factor scores, to test whether the hierarchy organizes by security/exploration. Script: `q4_orthogonality.py`.

## 3. Is the security–exploration relationship genuine or response style? *(orig. Q12)*

**Partial correlation** of security vs. exploration, removing a person-level "style" index, computed two ways to bracket the truth: (a) elevation over all 170 need items (flagged as mechanically over-corrective, since the composites are part of that index); (b) a style proxy built from four *other* instruments — mean z of Dirty Dozen, Jealousy, SexDrive, LTMO (n ≈ 1,703). Reported both the raw correlation and the two partialed estimates.

## 4. How do the 10 within-scale factors map onto the 8 joint factors? *(orig. Q5)*

Computed **Tucker congruence coefficients** between each of the 10 subscale-EFA factors (fit per block: RS 2, SS 2, RE 3, SE 3) and the 8 joint-EFA factors, restricting every comparison to the block's own items so the loading vectors are commensurable. Used |c| ≥ .85 (Lorenzo-Seva & ten Berge) as the "same construct" threshold to identify 1:1 matches vs. absorbed/split factors.

## 5. Are the extreme forms of each need pathology? *(orig. Q7)*

**Correlated the 8 factor scores with 14 external scales** (pairwise-complete n ≈ 1,682–1,785) for convergent/discriminant validity. Then probed nonlinearity two ways to test the "pathological extreme" idea: (a) means of the external measure by decile of the need composite, and (b) adding a **quadratic term** to the linear fit and checking the increment. Key targets: security × attachment anxiety (ECR_Ax) and avoidance (ECR_Av); exploration × sexual compulsivity (SCS) and sociosexuality (SOI). Script outputs: `q7_*`.

## 6. Do needs distinguish ideal relationship type, and where does polyamory sit? *(orig. Q6)*

Grouped `RelSit_IdealNow` into five classes (Monogamy / Open Mono / Polyamory / Singledom / Celibacy). Compared **mean factor scores across groups by one-way ANOVA with η² effect sizes**, and plotted group means on a two-axis plane (multi-partner love × care/safety) to read off where polyamory falls. Script outputs: `q6_*`.

## 7. Can an individual's ideal type be predicted from needs? *(orig. Q11)*

**5-fold stratified cross-validated multinomial logistic regression** (standardized inputs, class-balanced weights) predicting the 5 ideal-type classes (n = 1,956), with **balanced accuracy** as the headline metric (vs. chance and majority baselines). Attribution via single-factor and drop-one-factor runs. Also a 3-class partnered-only version (Mono/Open/Poly). Script outputs: `q11_*`.

## 8. Does need–structure fit predict relationship satisfaction? *(orig. Q8)*

Among **1,467 partnered** respondents, OLS regression of `RelSat_Avg5` on multi-partner need, structure (CNM = 1), and their **interaction** (the moderation test). Cross-checked with within-structure correlations (RE_multi × RelSat in Monogamy vs. CNM) compared via **Fisher r-to-z**. Script outputs: `q8_*`.

## 9. Does need–structure misfit predict wanting to change? *(orig. Q15)*

Defined "wants to change" as **ideal type ≠ current type**, each collapsed to Mono vs. CNM. Tested whether multi-partner need separates would-be changers from the content using **Welch t / Cohen's d, AUC, and gender-adjusted logistic regression** (OR per SD), run in both directions (current monogamists wanting CNM; current CNM wanting monogamy). RelSat used as triangulation. Script outputs: `q15_*`.

## 10. Do needs differ by gender and age? *(orig. Q13, + Q13b follow-up)*

**Welch t-tests with Cohen's d** for men (n = 973) vs. women (n = 877) on all 10 need scores, using `Gender3cat` (man/woman, cis *or* trans); NB+ (n = 223) reported descriptively. **Pearson correlations with age** (n = 1,785). Follow-up (`q13b_gender_subgroups.py`) broke gender out with `SexGender9cat`, contrasting trans and non-binary subgroups against cis references with Holm and Benjamini-Hochberg correction across the exploratory family.

## 11. Do high-psychopathy respondents report different needs? *(orig. Q9)*

First verified which Dirty Dozen items carry the psychopathy subscale in this sample (item-total correlations). Defined **high-psychopathy two ways**: top decile of `DirtyDozen_P` (cutoff ≈ 6.25/9, n ≈ 193) and an absolute cutoff (mean ≥ 4, n ≈ 567) as robustness. Compared all 10 need scores with **Welch t, Cohen's d (95% CI), Holm correction, and gender-adjusted OLS** (group skews male, so adjustment is mandatory). Script: `q9_psychopathy_needs.py`.

## 12. "Dark security": excess jealousy relative to stated security? *(orig. Q10)*

**OLS regression of `Jealousy_Avg` on high-psychopathy status, controlling for stated security need (`comp_SEC`) and gender** (n ≈ 1,682), alongside raw group contrasts. The covariate-adjusted coefficient tests whether high-P respondents are more jealous than their professed security needs would predict.

## 13. Does the structure replicate in queerplatonic relationships? *(orig. Q14)*

Planned an EFA-and-congruence replication on the PSN/PEN items, but **all 82 PSN/PEN columns are entirely empty** in the export, so that was not possible. Pivoted to the answerable selection question: compared **QP opt-ins** (`RSN_QPSection == 1`, n = 145 in the analysis sample) vs. everyone else on the need scores via **Cohen's d**. Script outputs: `q14_*`.
