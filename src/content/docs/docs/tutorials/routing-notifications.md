---
title: "Tutorial: route escalations to a real channel"
description: "Placeholder outline — wire the notifications: block so Tutorial 2's escalate status actually reaches someone, not just the run list."
sidebar:
  order: 6
---

[PLACEHOLDER — outline only, not a full walkthrough yet.]

Tutorial 2 got `alert-triage` to escalate on low confidence — but "escalate"
so far has only meant a status change visible if you happen to check the UI.
This tutorial wires a real [`notifications:`](/docs/pipelines/notifications/)
block so an escalation actually goes somewhere.

## What this builds on

`pipelines/alert-triage.yaml` as left at the end of [Turn on the trust
knobs](/docs/tutorials/turn-on-the-knobs/) — its `escalate` transition is
the trigger this tutorial routes.

## Outline

1. Add a pipeline-level `notifications:` block with an `escalate` entry on
   the zero-config `log` channel first — real, verifiable in the service's
   own logs, no external account needed, and the right default for anyone
   who already centralises application logs.
2. Trigger the low-confidence path from Tutorial 2 again (rename
   `known-issues.md` the same way) and confirm the escalation template
   renders real values — `{{pipeline_name}}`, `{{step_summary}}`,
   `{{confidence}}`, `{{confidence_threshold}}` — not placeholders.
3. Show the `stage: testing` interaction explicitly: this pipeline has been
   running in testing (the default) this whole series, so every
   notification so far has actually been *forced* to the `log` channel and
   suppressed elsewhere regardless of what's configured — tie directly into
   [Testing vs production stages](/docs/concepts/stages/#what-testing-mutes).
4. Add a second channel as an optional extension — `telegram` (needs
   `notifications.telegram` credentials in `config.yaml`) or `webhook` — and
   show fanning one action out to multiple channels via a list.
5. Briefly contrast with `executor: notify` (a first-class step, not a
   state-transition reaction) — when you'd reach for one over the other.

## Where next

- **[Notifications](/docs/pipelines/notifications/)** — the full channel
  reference and `executor: notify` for structured outbound payloads.
- **[Human-in-the-loop](/docs/pipelines/human-in-the-loop/)** — a
  different mechanism for when escalation should mean "wait for someone to
  actually decide," not just "tell someone."

Next in the series: **[Gate a pipeline on
budget](/docs/tutorials/gating-on-budget/)**.
