# Validation Pipeline — Degrees-of-Freedom Ladder (reordered)

*Reframes the multi-model validation pipeline as an **escalating ladder**: start with everything locked and add **one degree of freedom per stage**. Replication first, then robustness, then generalization. This supersedes the earlier arm-by-arm ordering (which started open and constrained afterward). Spec for the re-run.*

---

## The idea, and why this order

Add degrees of freedom *as validation passes accrue*, rather than starting open and removing them.

Two reasons it's the right order:

1. **One source of variation at a time → interpretable failures.** If a result diverges when only *one* thing has changed, you know what caused it. Open everything at once and a divergence is unattributable (method? data? a bug?). The ladder builds localization into the structure instead of recovering it after the fact.
2. **Precedence.** Reproducibility is a precondition for testing robustness, which is a precondition for testing generalization. It's not meaningful to ask "does this survive a new method / new data?" about a result you haven't first confirmed reproduces under identical conditions.

This maps onto the metascience ladder reviewers know: **direct replication → conceptual replication → generalization.**

## The ladder

The four things that can vary: **model, methodology, data, question**. The question set is fixed throughout; the *model* is independent at every stage (that's the validation mechanism). Each stage then opens one more axis:

| Stage | New DoF opened | Fixed | Varied | Tests | Pass verdict |
|---|---|---|---|---|---|
| **1 — Replication** | (baseline) | question, **methodology**, **data**, definitions, factors | model | Computational reproducibility — does the *same* pipeline reproduce on a different model + stack? | **REPRODUCED** (else: stack/implementation discrepancy) |
| **2 — Robustness** | methodology | question, data, definitions, factors | model + **method** | Does the finding survive a *different defensible method*? | **REPRODUCED / CONVERGED** (else: DIVERGED = method-dependent/fragile) |
| **3 — Generalization** | data | question, definitions, factors* | model + method + **data** | Does it survive *different data* (new splits / holdout / new sample)? | **GENERALIZES** (else: SAMPLE-SPECIFIC) |

*\*Factor solution stays fixed throughout (validated upstream). At Stage 3 the fixed factor **loadings** are scored onto the new data; the solution itself is not re-derived.*

## Stage detail (what each run looks like)

**Stage 1 — Replication (everything fixed; vary the model).**
Models are *given* the analysis methodology and asked to execute it on the same data; run several independent models. They are blind to the original *results* but not to the method (the method is the fixed thing being replicated). Grade each model's numbers against the original key. Expect REPRODUCED across the board; any miss localizes a model/software-stack difference — which is itself a finding. Re-run free open-source models repeatedly for a reproduction *distribution*.
→ Fixed methodology = the **original investigation's methods** (the thing under replication). Use a model-facing protocol that encodes them.

**Stage 2 — Robustness (open the methodology).**
Fix question + data; let models **design their own method** per question (the staged propose → discuss → lock → execute flow). Blind to the original *methods and results*. This is where the reproduction-vs-convergence distinction lives: a different method reaching the same conclusion (CONVERGED) is the strong robustness signal; it's now cleanly interpretable because Stage 1 already established the computational baseline. A DIVERGED result here means the finding is method-dependent.

**Stage 3 — Generalization (open the data).**
Fix question; vary the **dataset** — new cross-validation splits, a held-out subsample, or eventually a different LoveSmarter wave/sample. Method can be the Stage-2 agreed approach or left free. Blind to original results. A finding that holds GENERALIZES; one that doesn't is SAMPLE-SPECIFIC (real in this sample, but bounded).

## Always fixed (across all stages)

- **The question set** (the 13 questions).
- **The factor solution** — validated separately; supplied as fixed input (loadings + scores). Re-opening the measurement model is a deeper extension, out of scope here.
- **The held-constant construct definitions** (relationship-type groupings, psychopathy cutoff, multi-partner need, etc.) — these define *what is measured*; only method (S2) and data (S3) open.

*(Possible deeper rungs for later: open the **definitions** — a multiverse/specification-curve arm — or open the **measurement model** itself. Note as future extensions, not part of the core ladder.)*

## Output: a validation-depth tier per finding

The ladder yields a clean, paper-friendly summary — each finding earns the highest rung it clears:

- **Tier 1 — Replicates** (passed Stage 1)
- **Tier 2 — Replicates + method-robust** (passed Stages 1–2)
- **Tier 3 — Replicates + robust + generalizes** (passed Stages 1–3)

A finding that stalls tells you *where*: e.g., "replicates and is robust, but sample-specific" is a precise, publishable statement.

## Mapping from the old framing (what to reuse, what changes)

Almost everything carries over — it's a re-sequencing plus one new stage:

- **Old Arm 2 (fixed-protocol OS executor) → Stage 1.** Run it *first*, across several models. Reuse `OS_VAL_PROMPT.md`. **Change:** the fixed methodology should be the **original** investigation's methods (clean replication target); reconcile `ANALYSIS_PROTOCOL_arm2.md` to the original methodology (they largely match already) and rename to reflect Stage 1.
- **Old Arm 1 (method-free reproducer) → Stage 2.** Reuse `METHOD_FREE_PROMPT.md`. Codex's completed run already serves as a Stage-2 data point; Laguna adds a second.
- **New → Stage 3.** No asset yet; needs a data-variation plan (splits/holdout, and eventually a separate sample) and a prompt variant (likely the Stage-2 prompt pointed at the new data, or the agreed method executed on it).

What changes operationally:
- **Blinding shifts per stage.** Methodology is *revealed* in Stage 1 (it's what's being replicated) but *withheld* in Stage 2 (models design their own). Results stay blind at every stage. So Stage 2 models must not see the Stage 1 protocol.
- **Scorecards become per-stage**, versioned as before (`SCORECARD_GUIDE.md`): a Stage-1 scorecard (reproduction across models), a Stage-2 scorecard (the current v1→v2 work), and a Stage-3 scorecard. The localize-a-divergence second pass and human-as-grader still apply within each stage.

## Model roster (per stage)

Each stage pairs one **closed-frontier** model with at least one **open-weights** model. All validators are independent of the **origin (Claude / Anthropic)**, which is excluded from the pool. Frontier families are spread across stages (Google → OpenAI → xAI) so no single vendor underpins more than one stage. **Record the exact model name + license in every scorecard** — the "works on open models" claim depends on it.

| Stage | Role | Model | Vendor (family) | License | Notes |
|---|---|---|---|---|---|
| 1 — Replication | frontier | Gemini (current flagship)\* | Google | proprietary | |
| 1 — Replication | open | Nemotron-3 (Super/Ultra) | NVIDIA | NVIDIA Open Model License (open weights) | free; re-run for a reproduction distribution |
| 2 — Robustness | frontier | **GPT-5.5** | OpenAI | proprietary | run via the **Codex app** (agentic harness) — the *model* is GPT-5.5; "Codex" is the run label, not the model |
| 2 — Robustness | open | DeepSeek (current) | DeepSeek | open weights (MIT)\* | frontier-grade open model |
| 3 — Generalization | frontier | xAI Grok (current flagship)\* | xAI | proprietary | 3rd distinct family; reuse Gemini/GPT if Grok access is hard |
| 3 — Generalization | open | Qwen (current)\* | Alibaba | open weights (Apache 2.0)\* | |

\*Confirm exact version + license string at run time (these move fast). Nemotron-3's open license is verified; double-check the others' model cards when you pull them.

*Optional bonus:* **Laguna XS.2** (Poolside, Apache 2.0 open) is a fun extra diversity run for the robustness stage — "can a small open coding model design the stats?" — but DeepSeek is the serious OS data point there. (Note: Laguna **M.1** is now also Apache-2.0 open weights.)

## Re-run order

1. **Stage 1 — Replication.** Finalize the original-methodology protocol; run it across ≥2 models (e.g., Nemotron + one more), free models repeated for a distribution. Grade vs the key → Stage-1 scorecard.
2. **Stage 2 — Robustness.** Run the method-free flow with independent models (Codex ✓ done; Laguna next), blind to method + results. Grade → Stage-2 scorecard (already at v2 for Codex).
3. **Stage 3 — Generalization.** Define the data variation; run; grade → Stage-3 scorecard.
4. **Compile** the validation-depth tiers across all 13 questions as the headline result.
