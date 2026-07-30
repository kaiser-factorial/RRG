# RRG — Project Summary

## Purpose

RRG is a blinded, multi-model pipeline for validating analyses originally produced
with AI assistance. It began as a validation of the LoveSmarter / Skopje2
investigation and is being generalized into a reusable research method.

The central question is not simply whether another model reaches the same answer.
The pipeline identifies **how deeply each finding survives independent scrutiny**
by opening one degree of freedom at a time.

| Stage | What changes | What remains fixed | What it tests |
|---|---|---|---|
| 1 — Replication | Model and software stack | Questions, data, definitions, methodology | Computational reproducibility |
| 2 — Robustness | Model, stack, and method | Questions, data, construct definitions | Survival under another defensible method |
| 3 — Generalization | Data, plus prior freedoms | Questions and construct definitions | Survival beyond the original sample/data realization |

The output is a validation-depth tier for each finding: replicates, is robust, and
potentially generalizes.

## What is built

### Reusable pipeline engine

- A config-driven package builder resolves the selected stage and model, assembles
  only the permitted inputs, records hashes and provenance, and creates a separate
  folder for returned results.
- A blinding linter blocks packages containing the original results, scorecards,
  forbidden methodology, operator-only tooling, or unexpected files. Packages are
  assembled in temporary staging and published only after the gate passes.
- A study cartridge (`study.yaml`) separates LoveSmarter-specific inputs and
  definitions from the reusable pipeline engine. Prompt placeholders and optional
  modules allow the workflow to be retargeted to another study.

### Data conversion and verification

- The original dataset remains the provenance anchor.
- A deterministic converter creates CSV and Parquet analysis copies, a codebook,
  and a JSON metadata sidecar.
- Every derivative is read back and checked against the source. For the current
  3,133-row × 1,141-column dataset, Parquet verifies bit-for-bit and CSV verifies
  within numeric tolerance with exact strings and missingness.
- The validator receives the full converted dataset and must derive the analysis
  sample from held-constant inclusion and grouping rules. No prebuilt analysis
  subset is routed into new packages.

### Stage-specific prompting

- Replication receives the original analysis protocol and is instructed to execute
  it without redesigning the method.
- Robustness is blinded to the original methodology and proposes its own approach.
  It supports either a discussion-and-lock workflow or an operator-reviewed
  no-discussion lock.
- Prompts are presented as a sequence of turns in the GUI rather than embedded in
  a one-shot shell command.

### Review and grading tools

- The local GUI supports study setup and preflight, data conversion, package
  building, run browsing, figure comparison, notes, and scorecard generation.
- The scorecard tool aligns validator outputs with the held-back results key and
  creates a grading skeleton. It may provide conservative hints, but every verdict
  remains a human decision.
- Provenance records the stage, model, license, exact files and hashes, prompt
  version, determinism settings, lint result, and any forced override.

### Quality controls

- Automated tests cover conversion fidelity, blinding failures, routing and
  publication behavior, and scorecard scaffolding.
- The origin model family is excluded from the validator roster.
- Results and scorecards remain operator-only at every stage. Original methodology
  is revealed only for replication and forbidden in robustness.

## Current empirical status

- One GPT-5.5 robustness run has been completed and graded on the earlier analysis
  basis. After one targeted refinement pass, all 13 findings agreed with the
  original through reproduction or independent methodological convergence.
- Replication has not yet been run on the final basis.
- Additional robustness models have not yet been run on the final basis.
- Generalization has a conceptual stage in the ladder but no approved data plan or
  executable prompt/package route yet.

## Current blockers

1. **Measurement model / CFA.** The advisor-provided CFA is still pending. We need
   to know whether it confirms the existing eight-factor structure or replaces it,
   and exactly which artifacts validators should receive. Replication and new
   robustness runs should wait until this basis is settled.
2. **Generalization design.** We need to define what counts as opening the data:
   a held-out split, repeated resampling, a separate wave/sample, or some
   combination. We also need to decide whether Stage 3 holds a method fixed or
   permits another free method choice.
3. **Scope of the paper.** The pipeline and worked example are sufficiently mature
   to support a methods paper, but the empirical plan, model roster, and distinction
   between multiverse and “omniverse” analyses need advisor agreement.

## Immediate path after those decisions

1. Add the approved CFA/measurement-model artifacts to the study cartridge and
   package routing.
2. Re-run preflight and blinding tests on the settled basis.
3. Run replication with at least one frontier and one open-weights model.
4. Complete robustness with the remaining independent models.
5. Implement and run the agreed generalization design.
6. Grade each run and compile per-finding validation-depth tiers and cross-model
   agreement for the paper.
