---
title: "Tutorial: turn on grounding"
description: "Placeholder outline — rung 3 of the trust ladder, hands-on. Cross-check first-responder's claims against the exact trace Tutorial 1 had you watch."
sidebar:
  order: 3
---

[PLACEHOLDER — outline only, not a full walkthrough yet.]

[Build your first agent](/docs/tutorials/build-your-first-agent/) had you
watch `first-responder`'s trace show two real tool calls — `fetch` against
GitHub's status API, `filesystem` reading `known-issues.md` — and told you
that's exactly what [grounding](/docs/pipelines/grounding/) checks
automatically. This tutorial turns that on: a judge agent cross-references
`upstream_incident` and `known_issue` against that same trace, instead of
you eyeballing it.

## What this builds on

`pipelines/alert-triage.yaml`'s `triage` step as left at the end of [Turn on
the trust knobs](/docs/tutorials/turn-on-the-knobs/) — confidence threshold
and verifier already in place. Grounding is `executor: gateway`-only, which
`triage` already is.

## Outline

1. Install the `grounding-judge` sample agent — `cp -r
   samples/agents/grounding-judge agents/` in the Gateway repo — and look at
   its `soul.md`: no tools, told explicitly not to use outside knowledge,
   only to cross-reference the transcript it's handed.
2. Add a `grounding:` block to the `triage` step, shadow mode first (no
   `enforce:` — just `agent: grounding-judge`). Reload, re-trigger.
3. Open the run and find the **"Trust (shadow)"** widget — G sits alongside
   S and V now, with the per-claim ✓/✗ breakdown for `upstream_incident` and
   `known_issue`, each with cited evidence from the trace.
4. Deliberately break something to see G actually catch it: edit the
   prompt to ask the agent to also report on a third claim it has no tool
   for (e.g. "is this a recurring pattern this month") and watch grounding
   correctly flag it unsupported — the agent asserted something it never
   checked.
5. Flip to `grounding.enforce: true` and drop the step's
   `confidence_threshold` slightly below where it's been passing, so the
   next run demonstrates G actually capping `combined_trust` — reference
   [the gate formula](/docs/pipelines/grounding/#deterministic-checks--enforced-grounding-phase-1)
   rather than re-deriving it here.
6. If a claim gets flagged unsupported that you're confident is real, this
   is the exact scenario [the truncation troubleshooting
   guide](/docs/troubleshooting/fixing-grounding-accuracy/) covers — worth
   a forward pointer rather than repeating.

## Where next

- **[Grounding](/docs/pipelines/grounding/)** — the full reference this
  tutorial walks through hands-on.
- **[Writing your grounding judge](/docs/guides/writing-your-grounding-judge/)**
  — going beyond the bundled sample: model choice, and what to change for a
  step with many load-bearing claims.

Next in the series: **[Fan out over multiple
services](/docs/tutorials/fan-out-over-services/)**.
