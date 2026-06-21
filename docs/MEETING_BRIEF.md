# Validating AI-Assisted Research — Lab Meeting Brief

*Prepared for lab meeting, June 19, 2026 · A multi-model pipeline for validating AI-assisted analyses, with first results from the LoveSmarter investigation.*

---

## Why this matters

We increasingly use AI models to do substantial analytic work. But the usual quality checks — reading the code, having a second analyst re-run things — don't map cleanly onto the failure modes that are specific to AI-assisted analysis:

1. **Silent implementation error** — something cleaned or computed subtly wrong, in a way that reads as plausible.
2. **Analytic-choice fragility** — a finding that holds only under the one method the model happened to pick.
3. **Anchoring** — the obvious "check" (show a second model the first's work) just produces an echo, not an independent test.

The pipeline I've built is a concrete, reusable way to address all three.

## The pipeline, in one breath

Take the AI-assisted investigation, package only the data its questions need into a **blinded, reproducible bundle**, hand that to **independent validator models** that never see the original methods or results, then **grade their output against a held-back answer key** using a framework that separates *"same method, same answer"* (reproducibility) from *"different method, same answer"* (robustness). Anything that disagrees gets a localizing second pass to tell a real discrepancy from a mere analytic-choice difference.

Key design choices that make it work: the already-validated parts (here, the factor solution) are handed over as **fixed inputs**; the construct **definitions are held constant** while the **method is free to vary**; and a **human stays the grader** against a private key — the models never grade themselves.

## The three-arm design (the proposal)

| Arm | Model | Gets | Tests |
|---|---|---|---|
| **0 — Origin** | Claude | — | The work under validation |
| **1 — Blind, method-free** | Codex (and Laguna, next) | data + questions, blind to methods & results; **chooses its own method** | Reproducibility **and** robustness in one pass |
| **2 — Fixed-protocol, open-source** | Nemotron (free) | data + the **agreed method**, blind to results; **executes only** | Computational reproducibility across a different model + software stack |

The arms are complementary: Arm 1 *varies* the method to test whether findings depend on analytic choices; Arm 2 *fixes* the method to test whether they survive a different stack. Because the open-source arm is **free**, it can be re-run many times for a stability distribution — something closed models can't match cheaply.

## What we've seen so far — Arm 1 (Codex)

The LoveSmarter investigation had **13 questions**. Codex re-analyzed all of them, blind.

- **First pass: 10 of 13 agreed** — 4 *reproduced* (same method, matching numbers) and 6 *converged* (a different defensible method, same conclusion). The other 3 were not contradictions: 2 method gaps and 1 small effect the original had itself flagged as fragile.
- **After one targeted refinement round: all 13 agree** — 6 reproduced, 7 converged, 0 incomplete, 0 diverged.

A few illustrative matches:

| Question | Original | Codex | Verdict |
|---|---|---|---|
| Security vs. exploration correlation | r = .44 | r = .436 | Reproduced |
| Predicting ideal relationship type (accuracy) | .70 | .700 | Reproduced |
| Need–structure fit → satisfaction (interaction) | 0.42 | 0.422 | Reproduced |
| "Where does polyamory sit" (needs profile) | large multi-partner gap | large multi-partner gap | Converged (different test) |

**The most instructive case (Q on "dark-security" jealousy):** it *looked* like a disagreement on the first pass. The localizing second pass traced it to a reference-group and covariate choice; once the specification matched, the estimate reproduced to three decimals (b = 0.167, p = .019). The "divergence" was an analytic-choice difference on a fragile effect — exactly what the framework is designed to distinguish from a real error.

## What this demonstrates

- **The findings hold up.** Independently reproduced or converged across all 13 questions, by a model that never saw how the original was done.
- **The method does real work.** The reproduction/convergence split delivered both reproducibility *and* robustness evidence from a single run; the second-pass procedure correctly separated "different choice" from "real discrepancy"; and the process even surfaced (and let us fix) an instruction-design bug that had briefly suppressed one analysis.

## Status & next steps

- **Arm 1, second model (Laguna):** queued — a second independent method-free validator gives us an inter-model agreement signal.
- **Arm 2 (Nemotron, fixed protocol):** ready to run; free and repeatable for a reproduction distribution.
- **Toward a paper:** formalize the protocol; run all three arms across multiple validators and multiple studies; report inter-model agreement and the reproduction/convergence/divergence breakdown; and benchmark the catch-rate against conventional code review on deliberately seeded errors.

## Takeaway

A blinded, multi-model validation protocol — with an explicit reproduction-vs-convergence grading framework — that, on its first real test, independently stood up all 13 findings of an AI-assisted study and demonstrated it can tell a genuine error from a defensible difference in approach.
