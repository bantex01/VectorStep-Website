---
title: "Tutorial: store a full investigation as an artifact"
description: Placeholder outline — stop cramming long findings into next_step_context and store them as a proper artifact instead.
sidebar:
  order: 5
---

[PLACEHOLDER — outline only, not a full walkthrough yet.]

Every tutorial so far has kept `next_step_context` short — a sentence or
two. Real investigation output is often much longer (a full research
writeup, a compiled log excerpt), and stuffing that into `next_step_context`
or `summary` is exactly what
[artifacts](/docs/operations/runs/#artifact-storage) exist to avoid: content
stored on disk by reference, pulled into a later prompt by
`{{artifacts.step_name.key}}` only when a step actually needs it.

## What this builds on

`pipelines/alert-triage.yaml` from the fan-out tutorial (or straight from
Tutorial 2 if you skipped fan-out) — adds one more step downstream of
`triage`.

## Outline

1. Extend `first-responder`'s prompt to also return an `artifacts` key —
   have it write a longer `investigation_notes` artifact (the full
   reasoning, not just the one-sentence `summary`) alongside the normal
   mandatory fields.
2. Add a `write-up` step downstream that references
   `{{artifacts.triage.investigation_notes}}` in its own prompt — e.g. an
   agent that turns the raw notes into a cleaner incident-channel message.
3. Trigger it, then look at where the artifact actually lives on disk
   (`{artifacts_dir}/{run_id}/triage/investigation_notes`) versus what's in
   the database (`pipeline_steps.artifacts` holds only the opaque
   `local://...` reference, never the content) — the point being what stays
   out of the DB and why.
4. Note the hyphen-to-underscore rule applies here too
   (`artifacts.first_line_triage.x`, not `artifacts.first-line-triage.x`) —
   same gotcha as `{{steps.x.y}}` from [Writing good
   prompts](/docs/guides/writing-good-prompts/).

## Where next

- **[Artifact storage](/docs/operations/runs/#artifact-storage)** — full
  reference, including how content is written and replaced with a
  reference before anything touches the database.

Next in the series: **[Route escalations to a real
channel](/docs/tutorials/routing-notifications/)**.
