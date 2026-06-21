# HANDOFF — AI-Assisted Research Validation Project

*Continuity brief for a future session (Claude or other). Read this first to get oriented, then the pointers at the bottom. Last updated 2026-06-20.*

---

## 1. What this is

Two intertwined efforts for Corina's lab (Dr. Zhana Vrangalova / LoveSmarter):

1. **Validate the LoveSmarter investigation.** An AI-assisted analysis of the "Skopje2" survey (relational-security & erotic-exploration needs → ideal relationship type) was run by **Claude Fable 5** (the "origin" / model-0). We're independently checking its 13 findings.
2. **Generalize the method into a publishable pipeline.** The validation workflow became a reusable protocol for validating *any* AI-assisted analysis. **Corina's advisor independently proposed writing a paper about it** and is pursuing API funding. This is now a real paper.

The pipeline itself is the headline contribution: a blinded, multi-model validation procedure with an explicit grading framework.

## 2. The pipeline — degrees-of-freedom (DoF) ladder

Start fully locked, add **one degree of freedom per stage** (advisor's reframe; supersedes the earlier "arm" framing). Canonical spec: `Pipeline_Report/PIPELINE_DoF_REORDER.md`.

| Stage | Opens | Methodology | Tests | Models (roster) | Status |
|---|---|---|---|---|---|
| **1 — Replication** | (baseline; vary *model*) | **revealed** (`ANALYSIS_PROTOCOL_OG.md` = original methods) | computational reproducibility (same method, new model/stack) | Gemini (frontier) + Nemotron-3 (open) | **not yet run** on proper basis |
| **2 — Robustness** | *method* | **hidden** (models design own) | survives a different defensible method | GPT-5.5 (frontier) + DeepSeek (open) + Laguna-M.1 (open) | **GPT-5.5 done** (13/13, v2); others pending |
| **3 — Generalization** | *data* | agreed or free | survives different data | Grok (frontier) + Qwen (open) | **blocked on data plan** |

Output = a **validation-depth tier** per finding (Tier 1 replicates → +robust → +generalizes).

Always fixed across stages: the **13 questions**, the **factor solution** (validated upstream, given as input), and the **held-constant construct definitions**.

## 3. Folder map

**`DataAnal/PANEL/` — model-facing** (what validators receive):
`STUDY_OVERVIEW_all.md`, `INVEST_Qs_OG_all.md`, `DYFA_Guidelines_all.pdf`, and `validation_subset/` (data + codebook + glossary + factor scores/loadings + `VALIDATION_INSTRUCTIONS.md`; hash-locked, inputs only).

**`PANEL_VAL/` — operator side** (withheld):
- `origin_Fable-5/` — the origin run = **results key** (never sent).
- `robustness_GPT-5.5/`, `robustness_Laguna-M.1/` — validator runs.
- `ANALYSIS_PROTOCOL_OG.md` — original methods (Stage-1 input; do NOT send to robustness).
- `INVEST_Qs_OG_op.md` — operator question doc (verbatim + new↔orig map; un-scrubbed Q12).
- `HIDDEN/` — `ORIGINAL_METHODOLOGY.md`, `REPLICATION_RUBRIC.md`, `HELD_CONSTANT_RATIONALE.md`, prompts (`STAGE1_REPLICATION_PROMPT.md`, `METHOD_FREE_PROMPT.md`, `CODEX_PROMPT.md`), `validate*` factor tooling.
- `Pipeline_Report/` — `VALIDATION_PIPELINE.md`, `PIPELINE_DoF_REORDER.md`, `vp_config.yaml`, `skills/` (the `vp-*` SKILL.md files), `SCORECARD_*`, `SCORECARD_GUIDE.md`, `TOOL_MVP_DESIGN.md`, `MULTIVERSE_NOTES.md`, `MEETING_BRIEF.md`.
- `archive/` — retired: `ANALYSIS_PROTOCOL_arm2.md` (converged methods, arm-era), `INVESTIGATION_Qs_all.md` (rephrased, superseded), `OS_VAL_PROMPT.md`, `Nemotron_arm2/` (wrong-methodology run).

## 4. Conventions & invariants (don't break these)

- **File suffixes:** `_all` = sent to every validator; `_OG` = original-methods (Stage-1 only); `_op` = operator doc; `validation_subset/` auto-shared (no suffix). Run folders: `{stage}_{model}/`.
- **Blinding is the #1 risk.** Results (`origin_Fable-5/`, `SCORECARD_*`) are blind at *every* stage. Methodology is **revealed in replication** (it's what's replicated) but **hidden in robustness** (models design their own — never send any protocol there). `vp-blinding-lint` enforces this; run it before every dispatch.
- **Origin family excluded as validator** — Anthropic (Claude/Fable/Mythos) never validates its own work.
- **Numbering fixed at 1–13** across all stages (sensible thematic order; `INVEST_Qs_OG_op.md` maps to the original Q1/Q4–Q15). Keep it fixed or cross-stage comparison breaks.
- **Factor solution = fixed input**, not re-derived. (Caveat: per-block EFAs *are* allowed for the within-scale-vs-joint question — that's Q4.)
- **Don't force method divergence** in robustness — independent convergence on the same method is a *consensus signal*, not a failure. Record the per-question method-choice distribution.
- **Determinism:** temperature 0 / fixed seed (critical for replication).
- **Grading stays human** — skills *suggest* verdicts; a person confirms. Models never grade themselves.

## 5. Where we are / what's done

- **Robustness, GPT-5.5 (Codex-app harness):** complete and graded. v1 = 10/13 agreed; after one refinement round, **v2 = all 13 agree** (6 reproduced, 7 converged). The Q12 "divergence → localize → reproduced exactly" story is the marquee demonstration. *Caveat: run on the current basis (subset + EFA scores).*
- **Skills** (`vp-package`, `vp-replication`, `vp-robustness`, `vp-blinding-lint`, `vp-scorecard`) drafted as `SKILL.md` files. **Not installed** — installing a live skill must be done via Settings → Capabilities, not in-session. `vp-generalization` pending the data plan.
- **MVP tool:** design (`TOOL_MVP_DESIGN.md`) + config (`vp_config.yaml`). Two pieces **now built and tested**:
  - **Blinding linter** — `Pipeline_Report/vp_blinding_lint.py` (config-driven, all 6 checks, HARD-FAIL vs FLAG severities, `--json`/exit-2 for automation). Tests: `test_blinding_lint.py` (clean package + 7 leaky variants, all green).
  - **Thin driver** — `Pipeline_Report/vp_driver.py` (roster resolution + Anthropic-exclusion, package assembly per send-list, calls the linter and blocks on HARD FAIL, `--force` logged override, output folder, provenance + `_packages/provenance_log.jsonl`). **Build-then-publish:** assembles+lints in sandbox staging and only publishes to the folder on PASS, so a leaky package never lands on disk (also: the Cowork mount is **append-only** — file deletes need user approval via the delete-permission prompt). Collisions go to `{label}__{timestamp}`. Tests: `test_driver.py` (writes redirected to temp; all green).
  - Fixed a YAML syntax error in `vp_config.yaml` (`generalization:{` → `generalization: {`) found while wiring this up.
  - **Scorecard scaffolder** — `Pipeline_Report/vp_scorecard.py` (+ `questions_map.yaml`). Maps new#↔orig, lays the validator's headline material (`raw/Q{n}_summary.json` + `SUMMARY.md`) beside the key's `F:`/`A:` findings, emits a `SCORECARD_{stage}_{model}_v{n}.md` skeleton with PENDING verdicts, a conservative `_REPRODUCED?_` auto-hint only where one labelled scalar matches within rubric tolerance, tally/method-distribution/second-pass templates, and a "what changed" diff seeded from the prior version. **Grades nothing as final — human confirms every row.** Tests: `test_scorecard.py` (real GPT-5.5 run; 13 mapped, 0 final, 1 hint, prior-diff seeded; all green).
  - **All three MVP pieces (linter, driver, scorecard) now built + tested.** Still to build (optional): output-ingestion automation. Execution stays in vendors' native agent apps; OpenRouter automation is Phase 2 (open models only).
  - **Local GUI** — `Pipeline_Report/vp_gui.py` (single file, stdlib only; `python3 vp_gui.py` → `http://127.0.0.1:8765`). Six tabs: **Dashboard** (stage×model packaged/returned/graded grid), **Convert data** (run `convert_data.py` on the source → csv/parquet, showing the per-format "identical ✓" verification), **Build** (run the driver + see the blinding result and paths, dry-run/force), **Runs** (browse a run's files; view text + images), **Compare** (step Q1–Q13, validator figure(s) beside the original's — figure↔question matching is boundary-safe so Q1≠Q11), **Scorecards** (generate a skeleton + read existing). Backend only shells out to the three scripts and reads files under the repo (path-confined; binds 127.0.0.1). Agent conversations stay in the CLI/Hermes; the GUI is just package prep + output viewing. **Build** also shows a **multi-turn dispatch hand-off** (the validator flow is interactive, not one-shot): cd into the freshly-created empty run folder → start the agent (`hermes run --model {slug}`) → paste the stage prompt's turns in order (parsed live from the stage `prompt_doc`; Turn 4 etc. flagged operator-led, operator reminders shown separately, never as paste text). No prompt is baked into a command and **no `HIDDEN/` path appears in any command**. Configured by the `dispatch:` block in `vp_config.yaml` (`start_template` + per-model OpenRouter slugs — verify the slugs). **Compare** supports per-question **notes**, saved to `Pipeline_Report/_compare_notes/{run}.json` (operator-side, never inside a run folder, so they can't contaminate outputs). `vp_scorecard.py` auto-folds those notes into each question's Note cell (📝), so Compare annotations flow into grading.
  - **Source-of-truth = the original full `.sav`** (advisor: one source of truth; no more derived subsets sent). `.sav` is painful and per-stack readers disagree, so the agreed approach is **ship the `.sav` (authoritative, hash-locked) + a reproducible csv + a metadata sidecar**, where the csv is a *reproducible derivative* (regenerable from the `.sav`), not a second source — same "reproducible-by-spec" logic as the CFA. Converter built: `Pipeline_Report/convert_data.py` — **format-agnostic** (not SPSS-only, for the paper's generality). Reads SPSS `.sav/.zsav/.por` + Stata `.dta` + SAS `.sas7bdat/.xpt` (pyreadstat, with labels/missing) and flat `.csv/.tsv/.xlsx/.parquet` (pandas); writes `--formats csv parquet` (csv default human-readable; **parquet** typed/analysis companion; **pkl dropped** — Python-only/version-fragile/executes-on-load) + `{stem}.meta.json` (value/variable labels, dtypes, user-missing, **source sha256**, + a `verification` block) + `{stem}.codebook.csv`. Coded by default (round-trips), `--labeled` applies labels; csv byte-deterministic, parquet content-identical. **Post-write verification**: each derivative is read back and compared to the source cell-for-cell — parquet bit-for-bit, csv to float precision (~1e-16); `--json` surfaces it. Verified on the full source (**3,133 × 1,141**, 980 vars with value labels) and tested via `test_convert.py` (incl. a flat-csv source path). **Do conversion ONCE and ship it — don't have each validator convert in-run** (that makes conversion a per-model degree of freedom → drift). Folded into the `vp-package` skill. **Still pending the advisor:** confirm he's OK shipping the reproducible csv alongside the `.sav` (vs `.sav`-only); and this is the same change as Open decision #1 (CFA/source-of-truth) — the measurement-model half (CFA vs EFA scores) is still open, so the subset wiring in `vp_config.yaml`/`vp-package` is left in place until that lands.

## 6. Open decisions (mostly waiting on the advisor's next meeting)

1. **CFA + source-of-truth change.** Advisor is delivering a **CFA** (confirmatory factor analysis). Plan: move the canonical input from "derived subset + EFA scores" → **"full original dataset + the CFA measurement model"** (validators do their own cleaning; CFA is reproducible-by-spec, which resolves the EFA-nondeterminism dilemma). **Key question to resolve:** does the CFA *confirm* the existing 8-factor structure (→ validation) or specify a *new* one (→ re-basing)? This change triggers re-runs.
2. **"Omniverse" vs "multiverse."** Advisor uses "omniverse" for a big correlation-matrix lead-finding scan (possibly with Chatterjee ξ). Confirm whether he also means a true **multiverse** (specification robustness). If yes → already covered; if no → add it (spec grid drafted in `MULTIVERSE_NOTES.md`). Multiverse sits *beside* the ladder, not as a rung.
3. **Stage-3 data plan.** Define "open the data": CV splits / holdout subsample / a genuinely separate LoveSmarter wave — and whether method is held or free. Gates `vp-generalization`.

## 7. Re-runs needed (once basis is settled)

- **Replication (Gemini, Nemotron)** — never properly run. (An earlier Nemotron run used the wrong-stage methodology → archived.)
- **Laguna-M.1 robustness** — only a partial run, and it was on the *contaminated* subset (its outputs had leaked into `validation_subset/`; cleaned up). Re-run cleanly for a full Q1–Q13.
- **GPT-5.5 robustness** — may need re-running if the source-of-truth (CFA/full-data) basis changes.

## 8. Gotchas & lessons (learned the hard way)

- **Contamination happened once:** a validator wrote its analysis *into* `validation_subset/` (the auto-shared folder) — a live leak of results+methodology to future validators. Caught during cleanup, moved out. This is exactly why the linter + hash-lock exist. Watch for it.
- **Model licensing churns fast (June 2026):** Claude Fable 5 was pulled by US-gov order then restored; Laguna M.1 went from proprietary → Apache-2.0. **Verify model + license at run time**; the roster has `(confirm)` flags.
- **Question text can itself leak** — original Q12 embedded "+.44" (a result); the model-facing version is scrubbed.
- **Blinding is per-stage**, not global — the most common future mistake will be sending `ANALYSIS_PROTOCOL_OG.md` (or any protocol) to a robustness model.

## 9. Where we're going

Near-term: settle the CFA/source-of-truth basis and Stage-3 data plan with the advisor → then run Replication (Gemini + Nemotron) and finish Robustness (DeepSeek, Laguna-M.1), grade into per-stage scorecards, compile validation-depth tiers. Build the skills/MVP only as far as needed to run those stages.

Paper: the method + the v1→v2 worked example largely exist in draft form across `VALIDATION_PIPELINE.md`, the scorecards, and `MEETING_BRIEF.md`. The stronger empirical section comes from running all three stages across the multi-vendor roster and reporting inter-model agreement + the reproduction/convergence/divergence breakdown. **Keep the paper ahead of the tool** — the MVP is for running the stages, not a product to perfect.

## 10. Key docs to read next

- `Pipeline_Report/PIPELINE_DoF_REORDER.md` — the canonical pipeline spec (ladder + roster).
- `Pipeline_Report/VALIDATION_PIPELINE.md` — the full write-up (paper seed).
- `Pipeline_Report/vp_config.yaml` — the operational source of truth (routing, blinding, roster, stages).
- `HIDDEN/REPLICATION_RUBRIC.md` + `Pipeline_Report/SCORECARD_GUIDE.md` — how grading works.
- `Pipeline_Report/SCORECARD_robustness_GPT-5.5_v2.md` — the one completed result.
- `Pipeline_Report/MULTIVERSE_NOTES.md`, `TOOL_MVP_DESIGN.md` — the two parked workstreams.
