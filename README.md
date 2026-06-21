# RRG — AI-Assisted Research Validation Pipeline

A blinded, multi-model procedure for independently validating an AI-assisted data
analysis, plus the tooling to run it. **RRG** = the three rungs of the validation
ladder: **R**eplication → **R**obustness → **G**eneralization.

> Private working repo for the LoveSmarter / Skopje2 validation. Contains the
> reusable framework + the LoveSmarter-specific config, prompts, and worked
> example. **No data and no answer key live here** — the original dataset and the
> origin run stay outside git (see *Data*).

## The idea

An AI model (the "origin" run) produced an analysis with a set of findings. We
check those findings independently by handing the *same questions* to other
models under increasing freedom, one **degree of freedom** added per stage:

| Stage | Opens | Methodology | What it tests |
|---|---|---|---|
| **1 — Replication** | model only | revealed (original methods given) | does the original analysis reproduce on a different model/stack? |
| **2 — Robustness** | + method | hidden (model designs its own) | does the finding survive a *different defensible method*? |
| **3 — Generalization** | + data | agreed/free | does it survive *different data*? |

Each finding earns a **validation-depth tier** (replicates → + robust → + generalizes).
Grading stays human; the tools *scaffold and suggest*, a person confirms.

**Blinding is the #1 invariant.** The origin results and (in robustness) the
original methodology are never sent to a validator. The tooling enforces this
mechanically before every dispatch.

## The toolkit (stdlib + a couple of libs; each has a test)

| Script | Does | Test |
|---|---|---|
| `convert_data.py` | source dataset → reproducible csv/parquet + metadata sidecar, **verified identical** to the source | `test_convert.py` |
| `vp_blinding_lint.py` | the blinding gate — scans a package for leaks; HARD-FAIL vs FLAG | `test_blinding_lint.py` |
| `vp_driver.py` | assemble a package per routing rules, run the gate, publish on PASS, write provenance | `test_driver.py` |
| `vp_scorecard.py` | lay a validator run beside the key → a scorecard skeleton (PENDING verdicts) | `test_scorecard.py` |
| `vp_gui.py` | a local web app tying it together (Dashboard · Convert · Build · Runs · Compare · Scorecards) | — |

Run the tests:

```bash
python3 test_convert.py && python3 test_blinding_lint.py && \
python3 test_driver.py && python3 test_scorecard.py
```

Start the GUI:

```bash
python3 vp_gui.py          # → http://127.0.0.1:8765
```

Requirements: `python3`, `pyyaml`, `pandas`, `pyreadstat`, `pyarrow`
(`pip install pyyaml pandas pyreadstat pyarrow`).

## Layout

```
vp_*.py / convert_data.py    the tools (kept flat so they find each other)
test_*.py                    behavior tests
vp_config.yaml               operational source of truth (roster, routing, blinding, dispatch)
questions_map.yaml           fixed 1–13 ↔ original-numbering map
skills/                      the vp-* SKILL.md guides (one per stage + package + lint + scorecard)
docs/                        methodology + tool design + grading guide + HANDOFF
prompts/                     staged validator prompts, rubric, original methodology (operator-side)
examples/                    worked-example scorecards (GPT-5.5 robustness v1 → v2)
```

## Data (kept out of git)

The **original dataset is the single source of truth** and is never committed. The
tools resolve data relative to a project root (by default the parent of this
folder). To run in place, keep `RRG/` next to the working data dirs
(`DataAnal/`, `PANEL_VAL/`); most scripts also accept `--repo-root` to point
elsewhere. `convert_data.py` produces the analysis-ready csv/parquet derivatives
on demand (and verifies them identical to the source), so derivatives don't need
to be stored.

## Conventions (don't break these)

- **Blinding is per-stage.** Methodology is *revealed* in replication, *hidden* in
  robustness — never send any protocol to a robustness model. Run the linter
  before every dispatch.
- **Origin family never validates its own work** (excluded as a validator).
- **Numbering fixed at 1–13** across all stages (see `questions_map.yaml`).
- **Grading stays human** — the scorecard scaffolder marks everything PROVISIONAL.
- **One source of truth** — the original dataset; derivatives are reproducible from it.
