---
name: vp-scorecard
description: >
  Build a validation scorecard skeleton: lay each validator result beside the
  original (the answer key), pre-classify a SUGGESTED verdict per the rubric, and
  leave the final verdict to the human grader. Use after a validator returns its
  outputs for a stage, to grade a run into a versioned SCORECARD.
---

# vp-scorecard — grade a validator run against the key

Operationalizes Stage 6 (Grading). Turns a validator's returned outputs into a per-question scorecard that sets each result beside the original and assigns a verdict. **The skill scaffolds and *suggests*; the human assigns the final verdict** — the validator never grades itself, and neither does this skill on its own.

This artifact is **operator-side and withheld** — it contains results and verdicts, so it must never enter a package (the linter blocks `SCORECARD_*`).

## Inputs

- `RUN` — the validator's output folder (e.g., `REPLICATE_{MODEL}/`, `{MODEL}/`).
- `KEY` — the results key: `origin_Fable-5/` (`q*_results.txt`, `INVESTIGATION_SUMMARY.md`).
- `RUBRIC` — `REPLICATION_RUBRIC.md` (verdict definitions + tolerances).
- `MAP` — the new 1–13 ↔ original-label mapping (from `ORIGINAL_METHODOLOGY.md`).
- `STAGE` — `replication` | `robustness` | `generalization` (sets the verdict vocabulary).
- `PRIOR` — the previous scorecard version, if this is a refinement round.

## Verdict vocabulary (from the rubric)

- **REPRODUCED** — same method, numbers match within tolerance.
- **CONVERGED** — different defensible method, same conclusion (a pass; stronger robustness evidence).
- **DIVERGED** — conclusion or key number disagrees.
- **INCOMPLETE** — intended analysis not run (method gap / data limit).
- **N-A** — not answerable from the data.
- Stage-specific: replication expects **REPRODUCED** (a miss localizes a model/stack difference); generalization uses **GENERALIZES / SAMPLE-SPECIFIC**.
- Tag **FRAGILE** where the original pre-flagged the result as tentative (a miss is noted, not failed).

## Procedure

1. **Map the question** (new # → original label) so like is compared with like.
2. **Extract the validator's result** for each question from `RUN` (`RAW.md`, `Q*_summary.json`/`Q*_raw.csv`, `DYFA.md`): the headline statistic, N + subgroup Ns, and the method used.
3. **Pull the original's matching statistic** from `KEY`.
4. **Lay them side by side** and **pre-classify a SUGGESTED verdict** per the rubric tolerances:
   - direction/sign must match;
   - magnitude within bands (r ≈ ±.05; d / η² ≈ ±.10; balanced accuracy ≈ ±3 pts; coefficients same sign, overlapping CIs);
   - relative ordering preserved (the dominant predictor stays dominant; group rank-orders hold).
   Mark every suggested verdict **provisional — pending human confirmation.**
5. **Write the one-line note** (caveats: fragile, data-limited, reference-group sensitivity).
6. **Flag divergences for a second pass** (Stage 7): a DIVERGED result should be re-run with the original method pinned — matches → method difference (record as such); still differs → genuine discrepancy. Leave a column for the second-pass result.
7. **Human confirms** each verdict; only then is the scorecard final.

## Output

`SCORECARD_v{n}.md` (or `SCORECARD_stage{n}.md`), withheld in the operator kit, containing:

- a header noting stage, model(s) + exact name/license, and version;
- the per-question table: **Q | Topic | Verdict | Method vs. orig | Validator result | Original result | Note**
  (for a fixed-method stage, "Method vs. orig" is "same (fixed)"; for robustness it varies);
- a **tally** (counts per verdict);
- if `PRIOR` exists, a **"what changed from v{n-1}"** table with *why* each verdict moved;
- when a question's full ladder is known, its **validation-depth tier** (Tier 1 replicates → Tier 2 + robust → Tier 3 + generalizes);
- for a **robustness** stage run across multiple models, the **method-choice distribution** per question — how many models independently chose each approach (e.g., "Q7: 3/3 CV multinomial; Q5: 2 quadratic-probe / 1 decile-means"). This distribution is itself a finding: it shows which questions are method-settled (independent convergence) vs. method-ambiguous (spread).

## Versioning & provenance

- Name each snapshot `SCORECARD_v{n}` (or per stage); **keep prior versions** — the trajectory (e.g., v1→v2 flips after a refinement) is itself a result.
- Record the model's exact name + license in the header (the open-models claim depends on it).

## Notes

- **Suggested ≠ final.** The skill may pre-classify to save effort, but a human must confirm every verdict; nothing is graded autonomously.
- Per-stage reading: replication → mostly REPRODUCED (misses = stack differences); robustness → a mix of REPRODUCED/CONVERGED (the reproduction-vs-robustness signal); generalization → GENERALIZES/SAMPLE-SPECIFIC.
- **Convergence is information — read robustness conditional on divergence.** The fuller per-finding taxonomy: *method-consensus + reproduced* (solid) · *method-divergent + converged* (robust) · *method-divergent + diverged* (fragile/method-dependent) · *method-consensus + numbers diverged* (a reproduction problem to chase). Independent same-method choice is never scored as a failure to test robustness; it's a consensus signal, captured in the method-choice distribution.
- This skill grades **correctness/agreement only** — blinding is `vp-blinding-lint`'s job, and it runs at dispatch, not here.

## Implementation (built)

A reference scaffolder lives at `Pipeline_Report/vp_scorecard.py` (reads `questions_map.yaml`; PyYAML the only dependency):

```
python3 vp_scorecard.py --run RUN_FOLDER --stage STAGE --model NAME
                        [--license T] [--key origin_Fable-5] [--prior PATH] [--version N]
```

What it does mechanically (and only mechanically):

- maps each pipeline question to the original label via `questions_map.yaml` (the fixed 1–13 ↔ orig table);
- pulls the validator's headline material — `raw/Q{n}_summary.json` numbers + the per-Q line in `SUMMARY.md` (falls back to a flat `Q{n}_raw.csv`) — and the key's matching `F:`/`A:` findings from the `## Q{orig}.` section of `INVESTIGATION_SUMMARY.md`, laid side by side;
- emits a **provisional** verdict hint *only* where one labelled scalar (a validator `pearson_r`/`r`) matches a key `r = …` within the rubric's ±.05 correlation tolerance — written as `_REPRODUCED?_`; **every other row is left `PENDING`**;
- writes `SCORECARD_{stage}_{label}_v{n}.md` (auto-versioned) with the legend, the 7-column table, a tally template, a robustness method-choice-distribution stub, a second-pass reminder, and — when a prior version exists (auto-detected or `--prior`) — a "what changed from v{n-1}" table seeded with the prior verdicts.

**It never assigns a final verdict.** The output header is marked `SKELETON` / `PROVISIONAL`; a human confirms every row. Behavior is locked by `Pipeline_Report/test_scorecard.py` (runs against the real GPT-5.5 robustness run: 13 rows mapped, 0 final verdicts, exactly one advisory hint, prior-diff seeded — all green).
