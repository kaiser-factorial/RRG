# HANDOFF — AI-Assisted Research Validation Project

*Continuity brief for a future session (Claude or other). Read this first to get oriented, then the pointers at the bottom. Last updated 2026-06-22 (rrg-cli Origin tab, grading, stats extraction).*

---

## ⮕ Session update — 2026-06-22 (rrg-cli: Origin review, grading workflow, stats extraction)

All in the **standalone `rrg-cli/` package** (own git repo, remote on GitHub). Builds on the workspace-mode work below. Run the GUI from `RRG_root`: `RRG/.venv/bin/rrg gui --workspace . --port 8765`. Static assets (`web/app.js|css|html`) reload on browser refresh; **Python changes need a server restart**. There is a `SPEC.md` at the repo root documenting the whole CLI + GUI — read it first.

**What shipped this session (committed, pushed):**

1. **Origin tab** (`origin.py`, `/api/origin*`): per-question separation matrix cross-checking `questions_map` ↔ `QUESTIONS.md` ↔ `ANALYSIS_PROTOCOL_OG.md` ↔ origin `SUMMARY.md` (reusing the scorecard's `_markdown_section` so "scoreable" = what the scorecard extracts); streamed PDF viewer of the origin report (`/api/origin/report.pdf`, iframe, query-token auth, relaxed `frame-ancestors 'self'` — needed because `<object>`/data-URL renders blank and `style-src 'self'` blocks inline styles, see below); a result-free **methodology generation prompt** (`OG_METHODOLOGY_PROMPT.md`) rendered with study context, paste-back writes `ANALYSIS_PROTOCOL_OG.md`, with a result-leak heuristic warning.
2. **Per-stage model editor** (Setup): replaced the freeform roster textarea with grouped rows (model/vendor/type/license/dispatch slug); writes `roster` + `dispatch.model_slugs`.
3. **Unified Review & Grade tab** (`grading.py`, replaces Compare + Scorecards): per-question 3-section view — a **stats comparison** (Statistic | Validator value | Origin value), full **DYFA narratives** side by side, figures, and a **verdict** control. Grading state is per-run JSON; a run is "graded" **only when a human confirms a verdict for every question** (no longer implied by a scorecard file existing). Finalize → versioned `SCORECARD_*.md` filled with verdicts; drafts deletable, finalized ones protected until reopened.
4. **Validator-led stats extraction** (`extract.py`): flattens the validator's `raw/Q*_summary.json`; for each value, finds the same number in the origin's per-question text (`q*_results.txt` + narrative section) and shows the origin's own representation (e.g. `88.3` vs `0.8832`) + snippet, or "— not reported". Surfaces **origin-only figures** (numbers the origin reported that the validator didn't). Stage-aware framing: replication should match exactly, robustness may legitimately differ. In the rendered narratives, stat numbers are colored by model (origin **amber**, validator **stage color** — replication green / robustness blue), numbers not in the stats section are **red**, and figure refs are differentiated.

**Gotchas learned this session:** the GUI's CSP is `style-src 'self'` → **inline `style=` attributes are silently dropped**; use CSS classes (`.v-origin`, `.v-stage-N`, `.v-extra`, `.figref`) instead. Chrome won't render a PDF from a `data:`/`blob:` `<object>` reliably → use a same-origin streaming endpoint in an `<iframe>`. Committing from a sandbox failed on the mounted FS (no unlink) — commit from the Mac. Active GUI tab is persisted in the URL hash so reloads stay put.

**Tests:** `cd rrg-cli && PYTHONPATH=src ../RRG/.venv/bin/python -m pytest -q` — was green this session (test files: origin, grading, extract, scorecard_gui, packaging_blinding, converter, scaffold_doctor, cli). Note: `pyreadstat` must be installed for strict preflight to pass.

**Blinding breach found + fixed (important).** A test run of Gemini 3.1 Pro (transcript saved under `RRG_root/experiments/gemini_test1_MovieRatings/`) revealed the validator ran `ls -la ../../../origin/ ../../../private/` to look for prior results — because packages were built/run *inside* `operator/`, every secret (origin answer key, `private/`, scorecards, `shared/ANALYSIS_PROTOCOL_OG.md`) was one `../` away. The content-lint guards what's *in* a package, not what the validator can *reach*. Fix (rrg-cli, ADR `docs/adr/0001-validator-isolation.md`): `rrg package` now writes a self-contained delivery **zip** (no `_provenance.json`); run the validator on it **outside the project**; **`rrg import <returned> --stage --model`** brings outputs back into `operator/<run>/` with zip-slip protection. We deliberately did **not** add "don't snoop" prompt language (priming risk). Also: Turn 1 of the replication/robustness prompts now gates analysis ("orientation only — confirm inputs, then stop and wait"), since Gemini began analysing before the execute turn was even sent.

**Convention gap to revisit:** that Gemini run did *not* follow the deliverable conventions — no `raw/Q<n>_summary.json` (so the Review tab's stats comparison is blank), monolithic `run_analysis.py`, figures `images/visual_q<n>.png` not `Q<n>_fig.png`, report not in DYFA shape. Open decision (Corina leaning "discuss/combination"): tighten the prompt vs. add an `rrg import`-time normalize step vs. make the GUI extractor tolerant. The MovieRatings *demo* prompt/spec edits (DYFA + turn-gating) are loose on disk under `demo_projects/` (not in either repo).

**Earlier UI polish (committed):** narrative stat coloring (origin amber / validator stage-color / red for untracked numbers / ranges), figure refs white-italic click-to-scroll, hash-routed tabs. Open question: whether to also color stat *names* (`p`, `chi-square`), not just values.

---

## ⮕ Session update — 2026-06-22 (rrg-cli GUI workspace mode)

This work is in the **standalone `rrg-cli/` package** (its own git repo), *not* the `RRG/` monorepo above. `rrg-cli` is the generalized, extracted CLI/GUI engine; each study is a self-contained project directory marked by a `.rrg_root` file.

**What was built — multi-project workspace mode for the GUI.** Previously the GUI was locked to one project. Now `rrg gui --workspace /path/to/workspace` confines the GUI to one workspace directory and lets you discover, switch between, and create projects safely.

- **`src/rrg_cli/workspace.py`** (new): `discover_project_roots` (walks the workspace for `.rrg_root` markers, excludes `.git`/`data`/`operator`/`shared`/etc.), `initial_workspace_project`, and **`WorkspaceState`** — the key safety piece: it holds one `RLock` that serializes project *selection* and *every* active-project operation (build, convert, save_setup…), so a long-running op can't accidentally execute against a switched-out project root. `select_project`/`create_project` reject path traversal and require workspace-relative child paths.
- **`gui.py`**: wraps `GUIState` in `WorkspaceState`; new endpoints `/api/workspace`, `/api/project/select`, `/api/project/create`. Backward compatible — without `--workspace`, `workspace.enabled=false` and behaviour is unchanged.
- **`cli.py`**: `rrg gui --workspace DIR` flag.
- **`web/`**: new **Projects** tab (header, `utility` class → right-aligned). Switcher table (active/ready/invalid pills, Open buttons) + new-project form. Header order is now `…Scorecards | Projects · Setup`, with **Setup rightmost**.
- **`tests/test_scorecard_gui.py`**: `+2` tests covering discovery, switch, create, and traversal rejection (backend + HTTP API).

**Status: code complete, all 22 tests pass.** Verified switching against the two real workspace projects — `LoveSmarter-validation` (root, 1 package / 13 questions) ⇄ `MovieRatings demonstration` (`demo_projects/MovieRatings/RRG_demo`, 2 packages / 11 questions); counts re-scope correctly and switch-back restores. Design doc: `rrg-cli/docs/PROJECT_WORKSPACES.md`.

**⚠️ Not yet committed.** The changes are in the working tree of `rrg-cli/` (untracked `src/rrg_cli/workspace.py` + 6 modified files). A sandbox git commit failed on the mounted filesystem (no unlink/rename permission) and left a stale `rrg-cli/.git/index.lock`. To finish: `cd rrg-cli && rm -f .git/index.lock && git add -A && git commit`. A live click-through of the Projects tab in a real browser is the only verification step still outstanding (run `rrg gui --workspace .` from `RRG_root`).

---

## ⮕ Session update — 2026-06-22 (GUI overhaul + pipeline generalization + dataset switch)

All work this session is in **`RRG/vp_gui.py`**, **`RRG/prompts/`**, **`RRG/vp_config.yaml`**, and new files **`RRG/study.yaml`** + **`RRG/study.example.yaml`** + **`RRG/docs/GENERALIZATION_DESIGN.md`**. Run the GUI: `cd RRG && python3 vp_gui.py --port 8766` (8765 had a stray process; the server does **not** hot-reload — restart after edits; prompt/cartridge edits show on next render).

**1. GUI/UX polish.** Hover+cursor feedback on all clickables; smooth transitions; loading spinners; async **busy buttons** (disable + spinner on Build/Convert/Save/Generate); input `:focus` states; figure fade-in; `prefers-reduced-motion` guard. **Build tab:** already-built indicator (reads `_packages/provenance_log.jsonl`), saved-path box, explicit "dry-run saved nothing" message, prompt-doc path, green stage chip, state persists across nav. **Runs tab:** click a run → row stays highlighted + a scoped, collapsible **per-run prompt** appears (only that stage's prompt, split into per-turn chunks, with model/output/report auto-filled).

**2. Discussion-mode toggle.** Prompt turns can be tagged `{mode:discuss}` / `{mode:nodiscuss}` (untagged = both). Default **discuss**. No-discuss = model self-proposes then an **operator-reviewed lock** (no debate). Toggle lives in both Runs preview and Build. Also fixed `METHOD_FREE_PROMPT.md` Turn 6: execution doc `INVEST_METH.md`→**`APPROACH.md`**, hardcoded `Laguna_Report`→`{REPORT_NAME}`.

**3. Generalization — engine/cartridge split.** The pipeline is now retargetable to another lab. Reusable **engine** = `vp_config.yaml` + `vp_gui.py` + stage-prompt **scaffolds**. Per-lab **cartridge** = `RRG/study.yaml` (worked example `study.example.yaml`; full design + prompt audit in `docs/GENERALIZATION_DESIGN.md`). Prompts are templates with `{PLACEHOLDERS}` (resolve to file basenames / cartridge values, recursive) and `{#module}…{/module}` optional blocks. Engine fns in `vp_gui.py`: `load_study`, `study_placeholders`, `study_modules`, `render_prompt`, `fill_turns`, `render_stage_prompt`, `preflight`. **Setup tab** (new) edits `study.yaml` via `/api/study` (GET/POST — `yaml.safe_dump`, **strips comments**), runs **`/api/preflight`** (file-exists + clean-render checks), and previews any stage via `/api/study_preview`.

**4. Dataset switch (this is the big one — partially resolves Open decision #1).** Dropped the prebuilt `validation_subset/` samples. Now the validator gets the **full converted dataset** (deterministic, verified derivatives of `origin.source_data` from the Convert tab) and **derives its own analysis sample** via the held-constants. Specifics:
- `study.yaml` dataset → `LSS1_…forPascal` (`.csv`/`.parquet`) + Convert codebook (`…codebook.csv`); `subset_overview` cleared; **aux** and **given_solution** modules turned **off** (factor solution dropped for now).
- New **`additional` datasets module** (cartridge list + `{ADDITIONAL}` placeholder + Setup-tab editor "name :: file :: note") — this is where a **prof-supplied CFA** plugs in later without re-architecting.
- **Routing updated:** `vp_config.yaml` `files.all` now carries `VALIDATION_INSTRUCTIONS.md` + the 3 converted derivatives; stage `send` lists drop the `subset` token; `files.subset` retired; `blinding.subset_integrity`→`dataset_integrity` note; `check_subset_integrity` no longer fires. **All test suites green** (`test_driver`, `test_blinding_lint`, `test_convert`, `test_scorecard`) after updating `test_driver.py` + `test_blinding_lint.py` to the converted-dataset world.
- I generated the derivatives into `data/` (parquet **bit-for-bit exact**; **csv had 46 string mismatches + ~3.6e-12 float noise** — see pending items).

**Pending / next session:**
- **Stage colors** (Corina asked): currently all-green chips. Decision needed — r/y/g vs a cool palette. *Recommendation: green/blue/purple* (stages are a depth progression, not a quality/stoplight gradient; cool palette avoids implying stage 1–2 are "bad", and is colorblind-friendlier). One-liner change in the `.stagechip` CSS + a per-stage class in `stageChip()`.
- **CSV convert fidelity:** the csv derivative didn't fully verify (46 string mismatches, tiny float noise); parquet is exact. Investigate (encoding/NaN/float-format) or prefer parquet as the model-facing format.
- **result_token_scan noise:** with the full raw dataset in the package, the assistive token scan flags many coincidental numbers. Consider excluding the dataset derivative from that scan.
- **Operator-only prompt sections** ("Setup before the run" / "Fill in") at the top of each prompt `.md` still name LoveSmarter subset files — not rendered by the engine, but templatize for true reuse.
- **Setup-tab save strips YAML comments** (annotated reference stays in `study.example.yaml`) — optional: comment-preserving save.
- **Generalization stage prompt** still not wired (no `prompt_doc`).
- **CFA / measurement model** (Open decision #1) still needs the advisor: when the CFA arrives, add it via the `additional` module (or re-enable `given_solution`).

---

> **Canonical location + layout (as of 2026-06-21):** all pipeline code, tests, config, skills, framework docs, prompts/rubric/methodology, and example scorecards live in the **`RRG/`** repo (single source of truth; `git@github.com:kaiser-factorial/RRG.git`). The repo sits inside a **self-contained, movable project root** (e.g. `RRG_root/`, marked by a `.rrg_root` file) that also holds the runtime data in **role-based folders** — see `docs/LAYOUT.md`:
>
> | role | folder (new) | was |
> |---|---|---|
> | source-of-truth dataset | `data/` | `DataAnal/fullSet/` |
> | model-facing (sent to validators) | `shared/` | `DataAnal/PANEL/` |
> | operator-only (withheld; the blind) | `operator/` | `PANEL_VAL/` |
> | results key (analysis under validation) | `operator/origin_Fable-5/` | `PANEL_VAL/origin_Fable-5/` |
> | factor tooling | `operator/factor_tooling/` | `PANEL_VAL/HIDDEN/` |
>
> The top-level split **`shared/` (may go to a validator) vs `operator/` (never does)** is the blinding boundary. Tools find the root via `$RRG_PROJECT_ROOT` → `.rrg_root` marker → a data dir (new or legacy names) → repo parent. **Read inline paths below historically:** `Pipeline_Report/...` → `RRG/...`; `DataAnal/PANEL/...` → `shared/...`; `PANEL_VAL/...` → `operator/...`; `HIDDEN/` → `operator/factor_tooling/`.

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
