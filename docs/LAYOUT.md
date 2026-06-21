# Project layout

The pipeline runs from a **project root** — a directory that holds this repo
(`RRG/`) alongside the data. The root is self-contained and movable: drag it
anywhere (or clone onto another machine) and everything still resolves.

```
<project root>/              ← contains a .rrg_root marker file
├── .rrg_root                ← empty sentinel that marks the root (create it: `touch .rrg_root`)
├── RRG/                     ← this repo (the generic framework; the only thing in git)
│
├── data/                    ← the source-of-truth dataset(s)         [git-ignored]
│   └── <dataset>.sav            (referenced by origin.source_data in vp_config.yaml)
│
├── shared/                  ← what validators RECEIVE (model-facing)  [git-ignored]
│   ├── STUDY_OVERVIEW_all.md
│   ├── INVEST_Qs_OG_all.md
│   ├── DYFA_Guidelines_all.pdf
│   └── validation_subset/       (hash-locked; auto-shared to every validator)
│
└── operator/               ← WITHHELD from validators (the blind)     [git-ignored]
    ├── origin_Fable-5/          the analysis under validation = the answer key
    ├── robustness_<model>/      validator run folders (outputs come back here)
    ├── replication_<model>/
    ├── factor_tooling/          factor-validation tooling + data
    ├── archive/
    └── _packages/               assembled outgoing packages (driver writes here)
```

## The one rule the layout encodes

**`shared/` may go to a validator. `operator/` never does.** That is the
blinding boundary, and the blinding linter enforces it before every dispatch
(`operator/origin_Fable-5/`, any `SCORECARD_*`, and `factor_tooling/` are
hard-blocked from any outgoing package).

## How the root is found

Each tool resolves the root in this order:

1. `$RRG_PROJECT_ROOT` if set;
2. the nearest ancestor containing a **`.rrg_root`** file;
3. the nearest ancestor containing a data dir (`operator/`, `shared/`, `data/`,
   or legacy `PANEL_VAL/`, `DataAnal/`);
4. the repo's parent directory.

So the repo's parent (your root) wins, and `RRG/` stays portable.

## Using it for a different project

Create a root, clone `RRG/` into it, `touch .rrg_root`, and drop your dataset +
study inputs in following the layout above. Then point the path keys in
`RRG/vp_config.yaml` (`origin.source_data`, `origin.results_key`, `paths.*`,
`files.*`) at your files. `convert_data.py` produces the csv/parquet derivatives
(verified identical to the source); the rest of the pipeline runs from there.
