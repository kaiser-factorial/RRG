# Generalizing the validation pipeline to other labs

Goal: let another lab drop in their **dataset + original investigation + research
questions/methodology + held-constants** and run the same blinded, multi-model,
degrees-of-freedom validation — without editing the engine.

This doc is the **schema + prompt audit** (design only; no engine changes yet). It is
written so the templatization can later be edited from a **Setup GUI tab** — every
study-specific token is mapped to the control that will eventually edit it.

## Mental model: engine vs. cartridge

- **Engine (reusable, stays put):** the DoF-ladder stages, the blinding/leakage gate,
  dispatch + turn mechanics, the discuss/no-discuss mode toggle, and the GUI itself.
  Almost all of this already lives in `vp_config.yaml` and `vp_gui.py`.
- **Cartridge (per-lab, swappable):** the study's data, questions, held-constants,
  original investigation, and the lab-specific prose currently baked into the prompts.
  New file: `study.yaml` (worked example: `study.example.yaml`).

What already generalizes today (no work needed): `paths`, `files` registry, `roster`,
`stages`, `blinding` forbid/withhold lists, `constraints`, `dispatch`, and the
`{MODEL}` / `{OUTPUT_FOLDER}` / `{REPORT_NAME}` substitution. The `.rrg_root` marker
already supports multiple project roots.

What does **not** generalize today: the **prompt prose**. `METHOD_FREE_PROMPT.md` and
`STAGE1_REPLICATION_PROMPT.md` hardcode this study's dataset filenames and domain
concepts (the 8-factor solution, DYFA, relationship-type / psychopathy groupings). That
is the work.

## Principle: scaffold + injected blocks

Each stage prompt splits into two layers:

- **Scaffold** (engine-owned, identical across labs): the "I'm consulting you
  independently, blind to methods/results" framing, the two-pass proposal, the
  discuss/lock toggle, the run step, the QA pass, the per-question
  `Q{n}_analysis.py → Q{n}_raw.csv → Q{n}_fig.py → Q{n}_fig.png` pipeline.
- **Injected blocks** (cartridge-owned): data orientation, questions reference,
  held-constants, given-solution note, deliverable/method-guide, reporting spec.

The scaffold references the blocks via `{PLACEHOLDER}`s. Short values fill inline;
multi-line `[prose]` fields are injected as whole paragraphs a lab can author.

## Prompt audit (token → placeholder → cartridge field → GUI control)

`R` = appears in replication prompt, `MF` = method-free/robustness prompt.

| Hardcoded today | Placeholder | Cartridge field | GUI control | Req? | In |
|---|---|---|---|---|---|
| `STUDY_OVERVIEW_all.md` | `{STUDY_OVERVIEW}` | `study.overview_file` | file | req | R, MF |
| `LS_analysis_main_N2074` | `{MAIN_DATASET}` | `study.dataset.main_name` | text | req | R, MF |
| `ResponseId` | `{MERGE_KEY}` | `study.dataset.merge_key` | text | req | R, MF |
| `DATA_CODEBOOK.md` | `{CODEBOOK}` | `study.dataset.codebook` | file | req | R, MF |
| `DATA_SUBSET_OVERVIEW.md` | `{SUBSET_OVERVIEW}` | `study.dataset.subset_overview` | file | opt | MF |
| data-orientation paragraph | `{DATA_ORIENTATION}` | `study.dataset.orientation` | prose | req | R, MF |
| `LS_exclusion_q1_N3003` + note | `{AUX_DATASET}` | `study.dataset.aux` | toggle+text+prose | opt | R, MF |
| `.csv / .pkl / .sav` | `{FORMATS}` | `study.dataset.formats` | list | req | R, MF |
| 8-factor scores / glossary | `{SOLUTION_GLOSSARY}` | `study.given_solution.glossary` | file (module) | opt | R, MF |
| `FACTOR_SCORES…`, `FACTOR_LOADINGS…` | `{SOLUTION_ARTIFACTS}` | `study.given_solution.artifacts` | list (module) | opt | R, MF |
| "do not re-derive…" text | `{GIVEN_SOLUTION_NOTE}` | `study.given_solution.note` | prose (module) | opt | R, MF |
| `INVEST_Qs_OG_all.md` | `{QUESTIONS_FILE}` | `study.questions.file` | file | req | R, MF |
| "13 questions" / `Q1…Q13` | `{N_QUESTIONS}` | `study.questions.count` | num | req | R, MF |
| `VALIDATION_INSTRUCTIONS.md` | `{HELD_CONSTANTS_FILE}` | `study.held_constants.file` | file | req | R, MF |
| parenthetical held-constant list | `{HELD_CONSTANTS_SUMMARY}` | `study.held_constants.summary` | prose | req | R, MF |
| QA "report the Ns for…" list | `{HELD_CONSTANT_GROUPS}` | `study.held_constants.qa_groups` | prose | req | R, MF |
| `ANALYSIS_PROTOCOL_OG.md` | `{ORIGINAL_PROTOCOL}` | `study.original.methodology_file` | file | req | R |
| `origin_Fable-5/` | (engine) | `study.original.results_key` | file | req | — |
| `DYFA` / `DYFA_Guidelines_all.pdf` | `{METHOD_GUIDE_NAME}`,`{METHOD_GUIDE_FILE}` | `study.deliverable.method_guide` | toggle+text+file | opt | R, MF |
| per-question stats to report | `{REPORTING_SPEC}` | `study.deliverable.reporting_spec` | prose | req | R |
| `{REPORT_NAME}` (already done) | `{REPORT_NAME}` | `study.deliverable.report_name` | text | req | R, MF |
| roster names in operator notes | `{ROSTER_SUMMARY}` | derived from `roster` | (auto) | — | R, MF |

Generic deliverable names (`RAW.md`, `SUMMARY.md`, `APPROACH.md`, `DYFA.md`→`{METHOD_GUIDE_NAME}.md`)
stay in the scaffold.

## Optional modules

Some studies won't have these; they toggle off cleanly so no empty placeholders leak:

- **given_solution** — a fixed artifact the model must not re-derive (here: 8-factor solution).
- **aux dataset** — a secondary sample used for a subset of questions.
- **method_guide** — a special reporting method (here: DYFA). Off → generic "write up your analysis."

## Resolution mechanism

At load time the engine merges `vp_config.yaml` (engine manifest) + `study.yaml`
(cartridge). `parse_prompt_turns` (and `render_dispatch` / `/api/prompt`) gain a fill
step that substitutes the study placeholders alongside the existing
`{MODEL}/{OUTPUT_FOLDER}/{REPORT_NAME}`. Disabled modules drop their blocks entirely
(a `{#given_solution}…{/given_solution}` style conditional, or simpler: omit the turn /
paragraph when the module is off).

## Setup GUI tab (next phase, designed-for here)

A "Setup / Study" tab renders one control per cartridge field using the `[control]`
annotations above: file pickers (scoped to the project root, with exists-checks), text/
number inputs, prose textareas, and module on/off switches. It writes `study.yaml`,
then runs a **preflight**:

1. every referenced file exists and is inside the project root;
2. `validation_subset/` hash-locks against the source;
3. a **dry-run blinding pass** succeeds for each stage (the safety net — generalization
   must never silently weaken `always_withhold`);
4. **live prompt preview** per stage with all placeholders filled (reuses the Runs
   chunked-prompt renderer).

## Phased plan

1. **(this doc)** schema + audit — DONE.
2. Add `study.yaml` loading + merge into the engine; add the placeholder fill + module
   conditionals to the parser/endpoints.
3. Templatize `METHOD_FREE_PROMPT.md` and `STAGE1_REPLICATION_PROMPT.md` into
   scaffold + `{placeholders}` per the table.
4. Build the Setup tab (authoring + preflight + preview).
5. Ship a blank `study.template.yaml` + a starter file skeleton; keep LoveSmarter as the
   worked example.

## Open questions for Corina

- Should `study.yaml` be a **separate file** (clean cartridge boundary) or a `study:`
  section merged into `vp_config.yaml` (one file to edit)?
- For prose blocks: edit as **raw text in the Setup tab**, or keep them as standalone
  `.md` files the tab just points to (better for long/Markdown-heavy content)?
- Generalization stage prompt isn't wired yet — fold it into this pass or leave for later?
