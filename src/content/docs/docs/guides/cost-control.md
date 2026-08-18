---
title: Cost control
description: "Placeholder outline — proactive spend strategy: model selection, threshold placement, and verifier/grounding/fan-out choices that affect cost, not just budget.max_usd as a backstop."
sidebar:
  order: 8
---

[PLACEHOLDER — outline only, not full prose yet.]

[Gate a pipeline on budget](/docs/tutorials/gating-on-budget/) covers
`budget.max_usd` — a hard backstop that aborts a run after it's already
gotten expensive. This guide is about the design choices that decide how
expensive a pipeline gets *before* that backstop is ever needed.

## Planned sections

1. **A budget cap is a backstop, not a strategy.** It catches a runaway
   run; it does nothing about a pipeline that's reliably, unremarkably
   expensive every single time it fires. The rest of this guide is about
   the second problem.
2. **Model selection is the biggest lever, by far.** [Writing good
   agents](/docs/guides/writing-good-agents/)'s "match the model to the job"
   principle is a cost argument as much as a quality one — a cheap default
   with `model_fallbacks`, an expensive model reserved for the one step
   (often a verifier) where it's actually earning its keep.
3. **An accurate confidence threshold saves money, not just catches
   errors.** A step that escalates early on genuinely low confidence avoids
   paying for however many expensive downstream steps would otherwise have
   run on a shaky foundation. [Choosing confidence
   thresholds](/docs/guides/choosing-confidence-thresholds/) covers picking
   the number; this is the cost argument for why getting it right matters
   beyond correctness.
4. **Verifier mode is a cost/rigor trade-off.** `critic` re-reads what the
   primary already produced; `independent` redoes the entire task from
   scratch, roughly doubling that step's cost. [Verifiers](/docs/pipelines/verifiers/)
   frames the choice around correlated vs uncorrelated errors — the same
   choice, priced.
5. **Grounding is cheap if the judge is.** [Writing your grounding
   judge](/docs/guides/writing-your-grounding-judge/)'s model-choice
   section applies directly here — a grounding judge doesn't need a
   frontier model, and shadow mode means you're already paying for it on
   every run whether or not `enforce: true` is set.
6. **`max_items` on a fan-out is a direct cost cap.** N branches means N
   LLM calls, concurrently — [fan-out](/docs/pipelines/parallel/)'s
   `max_items` guardrail (default 20) is as much a cost control as a
   safety one, worth setting deliberately rather than leaving at the
   default for a step whose list could plausibly be much longer.
7. **Team budgets tell you about a trend; `max_usd` stops one run.**
   `pricing.team_budgets` is advisory, month-to-date, and never blocks
   anything — it's for noticing a team's spend is climbing before it's a
   crisis. `budget.max_usd` is the emergency brake for one run. Neither
   substitutes for the other.
8. **Unpriced spend is invisible spend.** A model with no `pricing.models`
   entry contributes `NULL`, not `0`, to every rollup — cost control starts
   with the pricing table actually covering what's really running, or
   opting into live/approximate OpenRouter pricing so an unpriced model at
   least shows up as an estimate instead of a gap.

## Where next

- **[Cost accounting](/docs/operations/cost-accounting/)** — the full
  pricing table, budget guardrail, and team-budget reference.
- **[Gate a pipeline on budget](/docs/tutorials/gating-on-budget/)** — the
  hands-on backstop this guide's opening section refers to.
