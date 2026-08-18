---
title: Designing pipelines
description: "Placeholder outline — when to split a step in two, sequential vs parallel vs fan-out vs sub-pipeline, and the step library."
sidebar:
  order: 4
---

[PLACEHOLDER — outline only, not full prose yet.]

[Writing good agents](/docs/guides/writing-good-agents/) is about scoping
one agent well. This guide is the same judgment call one level up: how many
steps a pipeline should have, and which of VectorStep's composition
mechanisms — sequential, `parallel:`, `fan_out:`, or a sub-pipeline —
fits a given decomposition.

## Planned sections

1. **One step is one auditable decision.** The reason to split rather than
   cram two jobs into one step's prompt isn't stylistic — a step gets its
   own confidence score, its own verifier, its own grounding check, its own
   calibration bucket. A step doing two things blends two different
   decisions into one number, the same argument [Writing good
   agents](/docs/guides/writing-good-agents/) makes about agent scope,
   applied to pipeline structure instead.
2. **Sequential when order matters, parallel when it doesn't.** Use plain
   sequential steps when a later step genuinely needs an earlier one's
   output. Reach for a `parallel:` group specifically when branches are
   independent *and* the branch set is fixed at authoring time — see [Fan
   out over multiple services](/docs/tutorials/fan-out-over-services/) for
   why fan-out is the dynamic version of the same idea, not a different
   idea.
3. **When a sub-pipeline earns its keep.** `executor: pipeline` isn't just
   "more steps in a different file" — a sub-pipeline gets its own `run_id`
   linked via `parent_run_id`, its own trace, and (if it's genuinely shared
   logic) its own promotion status independent of whatever calls it. Reach
   for one when the same multi-step logic is called from more than one
   pipeline, not as a way to make one pipeline's YAML shorter.
4. **The step library is for repeated shapes, not for hiding
   complexity.** `use:` (see [Step library](/docs/pipelines/steps/)) is the
   right tool when the *same* step config is genuinely reused across
   pipelines — it's the wrong tool for making a single pipeline's own YAML
   feel shorter by moving a one-off step somewhere else to look at less
   often.
5. **Step count has a real cost, not just a review-time one.** Every step
   is a calibration bucket that needs its own history, a readiness tier
   that needs its own evidence, a line in the Trust panel a human has to
   read during an incident. More granularity is only a win if each new
   step is actually a decision worth auditing on its own — not a reflex
   ("smaller steps are always better software engineering").

## Where next

- **[Parallel groups & fan-out](/docs/pipelines/parallel/)** — the
  mechanical reference for both composition mechanisms.
- **[Step library](/docs/pipelines/steps/)** — `use:`, deep-merge rules,
  and per-pipeline step analytics.
- **[Executors](/docs/integrations/executors/#pipeline--sub-pipeline-call)**
  — the `pipeline` executor's full reference.
