# Validation Pipeline Tool — MVP Design Sketch

*A first, low-risk implementation of the DoF-ladder validation pipeline. Scope: automate the **mechanical, error-prone** parts (packaging, blinding, routing, provenance, scorecard scaffolding); keep **execution** in vendors' native agent apps and **grading** with the human. Intended to be usable to run the paper's own remaining stages, not a polished product.*

---

## 1. Purpose & scope

**Does:**
- Builds the per-stage / per-model data package from a single source, applying the file-routing rules.
- Enforces blinding: a leakage linter blocks a package from going out if it contains anything the receiving model shouldn't see.
- Generates the correct staged prompts (from the stage skills) with placeholders filled.
- Logs exactly what each model received (provenance / audit trail).
- Scaffolds the scorecard from the returned outputs vs. the results key.
- Gates the ladder (a stage can't start until the prior one is graded).

**Does NOT (by design, for the MVP):**
- Run the models or execute their code — that happens in each vendor's native agent app (you paste the prompt + attach the package).
- Auto-grade — it builds the scorecard skeleton; the human assigns verdicts.
- Auto-scrub semantics — it *flags* likely leaks; a human confirms edits (deciding what counts as a leak is editorial).

## 2. Key decision: how validators execute

| | Native agent app (Codex app, Gemini agent, …) | OpenRouter + self-built loop |
|---|---|---|
| Build effort | ~none | high (agent loop + sandbox + security) |
| Execution quality | best per vendor | you own it |
| Programmatic orchestration | no (manual paste) | yes (full automation) |
| Cheap repeated OS runs | no | yes |
| Via OpenRouter? | no — vendor products | yes |

**Execution choice: one OpenRouter account + a single agent CLI for all validators.** Rather than juggling each vendor's separate app/account, all validator models (Gemini, GPT, Grok, DeepSeek, Nemotron, Laguna) are driven through **one OpenRouter API key** via an existing agent harness (e.g., **Hermes**) that supplies the tool-use loop + code sandbox. The software **build** uses **Claude Code** separately. Benefits: one bill + one spend cap (great for reimbursement), and — methodologically — a **uniform execution stack**, so the replication stage varies *only the model* (cleanly matching the ladder's one-axis-at-a-time logic). **Confirm before relying on it:** the harness supports OpenRouter as a backend, per-model **tool-use/function-calling** works through OpenRouter, and it provides a **sandboxed code executor**. (A fully-managed/UI version remains a later phase.)

## 3. Architecture (three pieces)

**(a) A config manifest** — one declarative file (YAML/JSON), the heart of the system:
- the **roster**: stage → models, each tagged frontier/open + license;
- the **routing rules**: which files are `_all`, `_armN`, `_OG`, or withheld, and per-stage send/withhold lists;
- the **leakage denylist**: files and tokens that must never leave the operator side;
- **stage gating**: replication → robustness → generalization order, with "≥1 open-weights if ≥2 models" enforced.

**(b) A thin driver** (a script) — does the deterministic file ops. **Built: `vp_driver.py`.**
- resolves the `{stage, model}` run against the roster (refuses an origin-family/Anthropic validator; records type + license);
- assembles the package by copying the routed files (`_all` + hash-locked subset + the stage's methodology per the send-list);
- runs the leakage linter (`vp_blinding_lint` as a library) and refuses to proceed on a HARD FAIL (`--force` overrides, and the override is logged in provenance);
- creates the `{stage}_{model}/` output folder for returned results — **outside** the package, so results can't co-mingle with inputs;
- writes the provenance record (file list + sha256 hashes, prompt-doc version, timestamp, lint result, determinism settings) into the package and appends a line to `_packages/provenance_log.jsonl`.

**Build-then-publish (important):** the driver assembles + lints in a sandbox staging dir and **publishes to the operator's folder only on PASS** — so a leaky package never lands on disk at all (strictly safer than "write then delete," and required because the Cowork folder mount is append-only: deletes need explicit user approval). Re-runs that would collide are published to a `{label}__{timestamp}` dir rather than overwriting. Behavior is locked by `test_driver.py` (writes redirected into a temp tree; all green).

**(d) Scorecard scaffolder — `vp_scorecard.py` (built).** Reads a validator RUN + the results key + `questions_map.yaml`; maps new#↔orig, lays the headline material side by side, emits a `SCORECARD_{stage}_{model}_v{n}.md` skeleton with PENDING verdicts (a conservative `_REPRODUCED?_` hint only where one labelled scalar matches within tolerance), tally/method-distribution/second-pass templates, and a prior-version "what changed" diff. Grades nothing as final — the human confirms every row. Tests: `test_scorecard.py`.

*All three mechanical pieces (linter, driver, scorecard) are built and tested.* Optional remaining work: output-ingestion automation (Phase 2).

**(c) Stage skills** (via `/skill-creator`) — injected instruction bundles, one per stage, that emit the staged prompts and the send/withhold list for that stage. These are just the prompt docs you already have, turned into reusable, parameterized skills.

## 4. Skill breakdown

- **`vp-package`** — build the data subset(s), export `.sav/.csv/.pkl`, run the cell-for-cell sameness check, assemble codebook/glossary. (Stage 0.)
- **`vp-replication`** — Stage 1: fill `STAGE1_REPLICATION_PROMPT.md` placeholders; send list = `_all` + `validation_subset/` + `ANALYSIS_PROTOCOL_OG.md`.
- **`vp-robustness`** — Stage 2: the method-free staged prompt (`METHOD_FREE_PROMPT.md`); send list = `_all` + `validation_subset/` (no protocol).
- **`vp-generalization`** — Stage 3: the data-variation prompt (TBD once the data plan is set).
- **`vp-blinding-lint`** — the leakage check (spec below).
- **`vp-scorecard`** — assemble validator outputs vs. the key into a `SCORECARD_v{n}` skeleton, per `SCORECARD_GUIDE.md`.

(One skill per stage keeps the blinding rules co-located with each stage's prompt — so the skill that builds the Stage-2 package is the same one that knows Stage 2 must withhold all protocols.)

## 5. Leakage-linter spec (the safety feature)

**Input:** a candidate package folder + the stage + the denylist + the results key.
**Checks:**
1. **No withheld files** — fail if the package contains anything from `origin_Fable-5/`, any `SCORECARD_*`, anything in `HIDDEN/`, `ORIGINAL_METHODOLOGY.md`, or a stage-forbidden protocol (`_arm2`/`_OG` in a Stage-2 package; any protocol in robustness).
2. **No result tokens** — scan text files for known result values from the key (numbers, effect sizes) and original-method keywords; flag matches.
3. **Stage-appropriate methodology** — Stage 1 *must* include `ANALYSIS_PROTOCOL_OG.md`; Stage 2 *must not* include any methodology protocol.
4. **Routing consistency** — every file's suffix matches the stage's allowed set; `validation_subset/` present and unmodified (hash-checked against source).
**Output:** PASS, or a list of flagged items; the driver blocks dispatch until PASS or explicit human override (logged).

## 6. Workflow (one model, one stage)

1. Pick `{stage, model}` from the roster.
2. Driver builds `package/{stage}/{model}/` per routing rules; writes provenance log.
3. `vp-blinding-lint` runs → must PASS.
4. Operator opens the vendor's native agent app, pastes the stage prompt (from the stage skill), attaches the package.
5. Model executes; outputs saved to `REPLICATE_{MODEL}/` (or stage-named folder).
6. `vp-scorecard` builds the scorecard skeleton vs. the key; human assigns verdicts.
7. Stage gate: advance only when the current stage is graded.

## 7. Phasing

- **MVP (now):** config + driver + stage skills + leakage linter + provenance + scorecard scaffold. Native-agent execution (manual paste). **Usable to run the paper's Stage 1 and Stage 3.**
- **Phase 2:** OpenRouter loop for the free open-weights models → automated *repeated* runs for a reproduction distribution. (Build the agent loop + a sandboxed executor; pin temperature 0 / seeds.)
- **Phase 3 (full app):** UI with a roster picker (enforcing the open-weights constraint), managed sandboxes, output collection, one-click scorecards. Candidate for a separate tools/software paper.

## 8. To confirm / decide

- Which models expose **tool-use / code-execution** in a way you can drive (matters only for Phase 2).
- The **Stage-3 data-variation** definition (gates the `vp-generalization` skill).
- Config format and where the tool lives (standalone repo vs. part of this project).
- Whether to keep the human-paste step even in Phase 2 for frontier models (likely yes — best execution, and the volume case is only for OS repeats).

---

*Sequencing note: this serves the paper rather than competing with it — the MVP is mostly packaging what already exists, and you'd use it to run the remaining stages. Resist scope-creep into the full app until the paper is drafted.*
