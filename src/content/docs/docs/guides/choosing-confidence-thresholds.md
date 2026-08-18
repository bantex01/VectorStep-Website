---
title: Choosing confidence thresholds
description: How to pick an actual confidence_threshold number, and what to do with on_low_confidence — not just what the knob does, but what to set it to.
sidebar:
  order: 5
---

[Adding trust, one signal at a time](/docs/guides/adding-trust/) and [how
confidence and calibration work](/docs/concepts/confidence/) explain what
`confidence_threshold` *does*. This guide is the question those pages don't
answer: what number do you actually put there?

## Start from what the step is allowed to get wrong

A threshold isn't a global policy — it's a statement about one specific
step's consequences. An informational step that hands its findings to a
human, or to another step that checks them again, can tolerate a much lower
bar than a step that performs a real, hard-to-reverse action on its own. The
bundled samples reflect this gradient rather than using one number
everywhere: an investigation step that only informs sits around `0.60`; the
schema default (used when nothing overrides it) is `0.75`; a step that
actually remediates something sits at `0.85` or higher. Don't copy these
numbers directly — copy the reasoning: ask what happens if this exact step
is wrong at the threshold you're about to set, before picking it.

## Don't guess — calibrate, then set it

The honest answer to "what should this be" before a step has run in
production is: you don't know yet, and guessing precisely is less valuable
than finding out. Set a conservative placeholder, run the pipeline in
`stage: testing` (see [Pipeline stages](/docs/concepts/stages/)), mark
outcomes as they come in, and watch **Steps Insights**
(`/ui/insights/steps`) — calibration is advisory by default with zero risk
to behaviour, so you can watch a step's real accuracy at each confidence
band *before* the threshold has to be right. If runs scoring "90%" are only
correct 65% of the time, that tells you where the real bar is far more
reliably than reasoning about it in the abstract. See
[Calibration](/docs/pipelines/calibration/) for how bins and `n_min` work.

## Pick `on_low_confidence` on purpose, not by default

`escalate`, `abort`, and `proceed` are three genuinely different postures,
and it's worth choosing deliberately rather than leaving whatever a sample
happened to use:

- **`escalate`** — a human reviews it. The right default for almost
  everything, provided a human is actually watching the channel it escalates
  to.
- **`abort`** — the pipeline stops cleanly with nothing further happening.
  Appropriate when there's no meaningful human-in-the-loop for this
  pipeline, or when doing nothing is always the safe fallback.
- **`proceed`** — the step continues anyway, below its own stated bar. This
  should be rare and deliberate — a low-stakes, easily-reversible action
  where blocking on every low-confidence result would be pure friction, not
  where it's just the path of least resistance to set up.

## Re-check the threshold every time you add a signal

`combined_trust` is a floor — adding a verifier, enforced grounding, or
enforced calibration to a step can only pull its effective score down, never
up. A threshold that was well-calibrated for raw self-report alone can start
escalating far more often than expected the moment a new signal is turned
on, and that's not a bug to route around — it's the new signal doing its
job. When you climb a rung on [the trust ladder](/docs/guides/adding-trust/),
watch the step's escalate rate for a while before assuming the threshold
still belongs where it was.

## A high escalate rate is data, not just noise

If a step escalates far more than you expected, there are two different
explanations, and they call for different fixes:

- **The threshold is miscalibrated relative to the agent's real accuracy** —
  check Steps Insights; if the agent is actually more (or less) accurate
  than its self-report suggests, that's what calibration exists to catch.
- **The task itself is genuinely hard for this agent** — narrower scope,
  better tools, or a clearer soul.md (see [Writing good
  agents](/docs/guides/writing-good-agents/)) fixes this; a threshold
  adjustment doesn't, it just hides a real capability gap behind a lower
  bar.

## Where next

- **[Calibration](/docs/pipelines/calibration/)** — the bins and validation
  mechanics behind "don't guess, measure."
- **[Promotion readiness](/docs/concepts/readiness/)** — where a step's
  threshold and its measured accuracy become part of the case for promoting
  a pipeline to production.
- **[Verifiers](/docs/pipelines/verifiers/)** — the signal most likely to
  change a step's effective score out from under a threshold you already
  tuned.
- **[Choosing readiness criteria](/docs/guides/choosing-readiness-criteria/)**
  — the same "what number do I actually pick" question, one level up, for
  promoting a whole pipeline rather than gating one step.
