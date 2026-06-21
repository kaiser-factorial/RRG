---
name: vp-blinding-lint
description: >
  The blinding safety-gate for the validation pipeline. Scans a candidate
  package for anything the receiving validator must not see (withheld files,
  result tokens, stage-forbidden methodology) and blocks dispatch on a hard
  failure. Run BEFORE every package is sent to any validator model, at any stage.
---

# vp-blinding-lint — pre-dispatch blinding gate

The single check that stands between "package assembled" and "package sent." It mechanically enforces the blinding rules so a human can't accidentally leak the answer key or the methodology. **Run it before every dispatch, every stage, every model.** A hard failure blocks the send.

## Inputs

- `PACKAGE` — the assembled package folder for one `{stage, model}` run.
- `STAGE` — `replication` | `robustness` | `generalization`.
- `CONFIG` — `vp_config.yaml` (denylist, per-stage methodology rules, subset hash).
- `KEY` — the results key (`origin_Fable-5/`), used only to derive result tokens (never packaged).

## Checks

Two severities: **HARD FAIL → block dispatch**; **FLAG → human must confirm or fix (logged)**.

1. **Withheld files present — HARD FAIL.** Fail if `PACKAGE` contains anything matching `blinding.always_withhold`: `origin_Fable-5/` (the results key), any `SCORECARD_*`, anything under `factor_tooling/` (the `validate*` factor artifacts), the methodology docs by name (`ORIGINAL_METHODOLOGY.md`, the staged prompts/rubric — these live in `RRG/prompts/`, operator-side), and `ANALYSIS_PROTOCOL_arm2.md`. Also fail on any operator-side file not on the stage's explicit send list.

2. **Stage methodology rule — HARD FAIL.** Per `blinding.per_stage_methodology`:
   - **replication** — `ANALYSIS_PROTOCOL_OG.md` *must* be present; no other protocol.
   - **robustness** — *no* methodology protocol may be present (no `_OG`, no `_arm2`, no `ORIGINAL_METHODOLOGY.md`). This is the rule that keeps the design-your-own arm honest.
   - **generalization** — no `ORIGINAL_METHODOLOGY.md`; methodology per the data plan.

3. **Routing / suffix consistency — HARD FAIL.** Every file's routing class matches the stage's allowed set: `_all` and `subset` always allowed; `_OG` only in replication; `_arm2` never; stage-specific files only in their stage.

4. **Subset integrity — HARD FAIL.** `validation_subset/` is present and **hash-matches the source** (not modified, and no extra files slipped in that could carry leaks).

5. **Result-token scan — FLAG.** Derive result-specific tokens from `KEY` (effect sizes, p-values, headline statistics, original-method keywords) and scan all text files in `PACKAGE` for matches. Report each hit for human review. *Tune to exclude legitimate values* — e.g., sample sizes (3,133 / 3,003 / 2,074) are dataset definitions, not results. Treat as assistive, not authoritative.

6. **Completeness — WARN.** The stage's required files are present (`_all`, `subset`, and the stage's required methodology). A missing required item warns before dispatch.

## Output

- **PASS** — green-light; record `blinding_lint_result: pass` in the provenance entry.
- **HARD FAIL** — block; list the offending files/rules; do not send until fixed.
- **FLAGS** — list the matches; a human confirms each is a false positive or removes it. Any override of a hard fail requires explicit, logged human approval.

## Important limits (necessary, not sufficient)

- The token scan catches *literal* leaks (a number, a method name). It will **not** catch a *paraphrased* leak — e.g., a model-facing doc that describes a finding in prose without the exact figure. So whenever a model-facing document is edited, a human should still eyeball it for semantic leakage; the linter does not replace that judgment.
- False positives are expected on the token scan (coincidental numbers); that's why it flags rather than blocks.
- This gate protects *blinding only*. It does not check analytic correctness — that's grading (`vp-scorecard`).

## Where it sits

Called by each stage-prep skill (`vp-replication`, `vp-robustness`, `vp-generalization`) at step "run the blinding linter," after the package is assembled and before hand-off. No package reaches a validator without a PASS (or a logged override).

## Implementation (built)

A runnable reference implementation lives at `Pipeline_Report/vp_blinding_lint.py` (reads `vp_config.yaml`; PyYAML the only dependency). All six checks above are implemented with the two severities; a HARD FAIL exits non-zero (2) to block an automated dispatch:

```
python3 vp_blinding_lint.py --package PATH --stage replication|robustness|generalization
                            [--config vp_config.yaml] [--repo-root LS_Lab] [--json] [--quiet]
```

Behavior notes specific to the implementation:

- The **hash-locked `validation_subset/`** is excluded from the result-token scan — its numbers are the given factor solution / item data (canonical input), and its integrity is separately guaranteed by the subset-integrity check, so scanning it is pure noise.
- The **result-token scan** extracts only *marker-adjacent* values from the key (`η²=`, `r=`, `= +.44`, bolded `**.44**`, `F(df,df)=`), so it catches the documented "Q12 question text embedded +.44" leak class without alarm fatigue. Dataset constants (sample sizes 3,133 / 3,003 / 2,074, item/factor counts) are allow-listed.
- **Method-descriptor keywords** are only flagged where method must be hidden (robustness, generalization), since they are legitimately present in the revealed protocol during replication.
- Behavior is locked by `Pipeline_Report/test_blinding_lint.py` — builds a clean package + seven leaky variants from the real project files and asserts the verdict per check. Run it after any change to the linter or `vp_config.yaml`.
