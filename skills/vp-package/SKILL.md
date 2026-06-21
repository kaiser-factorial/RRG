---
name: vp-package
description: >
  Build the canonical, blinding-safe input package shared with all validators:
  the source data (verified-identical formats, record IDs + value labels
  preserved), the reference docs, and the fixed measurement-model artifact. Use
  at the start of a validation effort, or whenever the source data or measurement
  model changes.
---

# vp-package — build the shared input package (Stage 0)

Produces the common, all-arms package every validator receives, regardless of stage or model. Stage-specific files (e.g., a methodology protocol) are added later by the stage-prep skills — this skill builds the shared core and verifies its integrity.

> **Pending source-of-truth change.** The canonical input is moving from "derived subset + EFA factor scores" to "**full original dataset + a confirmed (CFA) measurement model**," once the CFA is available (see `PIPELINE_DoF_REORDER.md` discussion). This skill supports both configurations; the *Configuration* section says which artifacts to assemble. Build against whichever is current, and re-run this skill if the basis changes.

## Outputs (the all-arms package)

- The `_all` reference files: `STUDY_OVERVIEW_all.md`, `INVEST_Qs_OG_all.md`, `DYFA_Guidelines_all.pdf`.
- The source data (see Configuration).
- The reference docs that travel with the data: `DATA_CODEBOOK.md` (+ variable map), `FACTOR_GLOSSARY.md`, `DATA_SUBSET_OVERVIEW.md` (or a "full-data notes" doc), `VALIDATION_INSTRUCTIONS.md`.
- The fixed **measurement-model artifact** (see Configuration).

## Configuration

**A — Current (subset + EFA scores):**
- Source data: the nested subsets `LS_analysis_main_N2074` and `LS_exclusion_q1_N3003`, each in `.sav` / `.csv` / `.pkl`.
- Measurement model: `FACTOR_SCORES_N2074.csv` (+ `.pkl`) and `FACTOR_LOADINGS_170x8.csv`.

**B — Planned canonical (full dataset + CFA):**
- Source data: the **full original `.sav`** plus the variable map/codebook (validators do their own cleaning/selection per protocol).
- Measurement model: the **CFA specification** (confirmed structure + scoring method); optionally CFA-derived scores as a grading reference. *CFA, being specified, is reproducible — so validators can score it themselves and still match.*

## Procedure

1. **Assemble** the `_all` files, the source data, the reference docs, and the measurement-model artifact for the current configuration into the shared package folder (`validation_subset/` or the full-data equivalent).
2. **Integrity checks:**
   - record IDs (`ResponseId`) preserved, no nulls/dupes;
   - value labels / variable labels carried into the `.sav`;
   - for multi-format exports, a **cell-for-cell sameness check** across `.sav` / `.csv` / `.pkl` (max numeric diff = 0; strings exact; NaN patterns match);
   - **no leakage columns** — confirm the source contains only pre-analysis data (scored scales are fine) and *no* analysis outputs (no result columns, no precomputed-and-hidden answers).
3. **Convert the source to analysis-ready derivatives** (`convert_data.py`). The original file is the **single source of truth** (the advisor's requirement). Convert it *once*, deterministically, and ship the original + the derivatives + the metadata sidecar together — never have each validator convert in-run (that makes conversion a per-model degree of freedom → drift). See *Source-format conversion* below.
4. **Apply routing labels:** `_all` suffix on shared context files; the data folder is auto-shared (hash-locked, so the linter can verify it's unmodified downstream).
5. **Record** the package's file list + hashes (provenance) as the baseline the linter checks against.
6. **Hand off** to the stage-prep skills, which add any stage-specific files and run `vp-blinding-lint` before dispatch.

## Source-format conversion (`convert_data.py`)

The pipeline is format-agnostic so it can validate any lab's analysis, not just SPSS ones. `Pipeline_Report/convert_data.py` reads the source and writes reproducible derivatives + a sidecar:

- **Reads** (auto-detected): SPSS `.sav/.zsav/.por`, Stata `.dta`, SAS `.sas7bdat/.xpt` (via pyreadstat, with value/variable labels + missing), and flat `.csv/.tsv/.xlsx/.parquet` (via pandas, thinner metadata).
- **Writes** (`--formats`, sidecar + codebook always): **csv** (universal, human-readable — best for *exploring*; default) and **parquet** (typed, compressed, language-agnostic via Arrow — best *analysis* companion; ship alongside csv). (pkl was dropped: Python-only, version-fragile, executes code on load — parquet does the typed job without the liabilities.)
- **Labels:** label-bearing sources export **coded** by default (raw codes, round-trips); `--labeled` applies value labels. Either way the labels live in `{stem}.meta.json`, so the csv's loss of labels/dtypes is recoverable.
- **Verification:** after writing, each derivative is read back and **compared to the source cell-for-cell** (NaN pattern, max numeric diff, strings). parquet matches bit-for-bit; csv matches to float precision (a value can't be both human-readable and bit-exact in text — diff ~1e-16, not a real change). Results are recorded in the sidecar's `verification` block and shown by the GUI.
- **Provenance:** the sidecar records the **source file's sha256** — the anchor proving the derivative came from this exact source. csv is byte-identical on re-run; parquet is content-identical.

Rule of thumb: keep the original as source of truth, ship **csv + parquet** (explore + analyze) and the sidecar. Run it from the CLI or the GUI **Convert data** tab (which shows the per-format "identical ✓" verification). Tested by `Pipeline_Report/test_convert.py`.

## Notes

- This skill never adds a methodology protocol — that's stage-specific (replication gets `_OG`; robustness gets none).
- Keep the measurement-model artifact **fixed across all stages and models** (it's validated upstream); only its form changes with the configuration (EFA scores → CFA spec).
- The package is the same for every validator — uniformity is an experimental control.
