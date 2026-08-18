---
title: Adding trust, one signal at a time
description: A ladder for introducing gating signals one at a time — start with nothing, and climb only as far as the risk of the action justifies.
sidebar:
  order: 1
---

Every signal below is optional and additive. A pipeline with none of them
turned on is a legitimate, supported way to run VectorStep — that's rung 0,
and plenty of pipelines never leave it. Climb a rung when the cost of the
agent being wrong goes up, not because a rung exists. Most pipelines should
stop climbing well before rung 6: once the risk of the action no longer
justifies the next rung, stop.

This page is a ladder, not a reference. Each rung explains why you'd bother
before it says how — the technical detail lives on the linked page.

## Rung 0 — Nothing

**Turn on:** nothing.

**The problem it solves:** none, deliberately. This is the baseline — a
working pipeline that triggers on a webhook, runs a step, and does whatever
the step's executor does. No confidence check, no verifier, no grounding, no
calibration, no readiness gate.

If the action a step takes is low-stakes or already reviewed by a human
downstream, this is where you should stay. Read the [pipeline
schema](/docs/pipelines/schema/) to see the shape of a pipeline with nothing
turned on.

## Rung 1 — A confidence floor

**Turn on:** `confidence_threshold` and `on_low_confidence`.

**The problem it solves:** the agent already reports a confidence number on
every response, whether you use it or not. Rung 1 just stops ignoring it —
below the threshold, the step escalates, aborts, or proceeds anyway,
depending on `on_low_confidence`, instead of the response being trusted
unconditionally.

This is the cheapest rung to climb — no new agent call, no new config block,
just a bar and a threshold. See [how confidence and calibration
work](/docs/concepts/confidence/) for what the number means and why it's a
starting point, not a verdict.

## Rung 2 — A second opinion

**Turn on:** `verifier`.

**The problem it solves:** the agent grading its own work is not evidence — a
model that got the task wrong will often say so confidently. A verifier is a
second agent call that sanity-checks the primary response before its
confidence is trusted, and it can only lower that confidence, never raise it.

Climb this rung when a wrong answer would be expensive enough that a second,
independent look is worth the extra call. Read
[Verifiers](/docs/pipelines/verifiers/) for the trigger bands and combination
strategies.

## Rung 3 — Grounding

**Turn on:** `grounding`.

**The problem it solves:** plausible-sounding prose isn't evidence. Grounding
checks whether every load-bearing claim in a step's output is actually backed
by a tool call or tool result in its own trace — not just phrased
confidently.

Climb this rung when the step's output makes factual claims you'd want
challenged in an incident review — "the deploy succeeded", "the ticket was
created" — rather than claims that are inherently a judgement call. See
[Grounding](/docs/pipelines/grounding/).

## Rung 4 — Deterministic checks

**Turn on:** deterministic checks.

**The problem it solves:** some facts aren't a judgement call at all, and
don't need a model in the loop to settle. A deterministic check runs a real
command or query and treats the result as ground truth — one failed check
forces trust to zero, no averaging, no partial credit.

Climb this rung when there's a fact you could check with a shell command or
an API call instead of asking a model — "is the alert still firing?", "does
this record still exist?". Deterministic checks are documented alongside
grounding: see [Grounding](/docs/pipelines/grounding/).

## Rung 5 — Calibration

**Turn on:** `calibration`.

**The problem it solves:** an agent saying "90% confident" doesn't tell you
whether its 90% has historically meant 90%. Calibration bins every marked
outcome per agent, model, provider and prompt version, and measures what each
confidence band was actually worth — in `advisory` mode with zero effect on
behaviour, or `enforce`d once you trust the bins.

Climb this rung once a step has enough run history to calibrate against, and
you want the measured track record to matter more than the agent's own
self-report. See [Calibration](/docs/pipelines/calibration/).

## Rung 6 — Readiness

**Turn on:** `readiness`.

**The problem it solves:** promoting a pipeline from testing to production is
usually a gut call. Readiness replaces the gut call with owner-defined
criteria across operational, confidence, accuracy and calibration tiers,
judged against real evidence before a pipeline earns production traffic.

This is the top of the ladder — climb it for pipelines whose production
promotion should be earned, not asserted. See [Promotion
readiness](/docs/concepts/readiness/).
