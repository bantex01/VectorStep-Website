---
title: Writing your grounding judge
description: "Placeholder outline — starting from the bundled sample, choosing a model for it, and sizing max_tokens against a step's claim count."
sidebar:
  order: 7
---

[PLACEHOLDER — outline only, not full prose yet.]

`samples/agents/grounding-judge/` in the Gateway repo is a working starting
point, used in [Turn on grounding](/docs/tutorials/turning-on-grounding/) as
written. This guide is about what to change and why, once the bundled
default isn't quite right for a specific step.

## Planned sections

1. **Start from the sample, don't write one from scratch.** Its `soul.md`
   already encodes the two things that actually matter — no outside
   knowledge, and a claim that restates the given task needs no evidence.
   Rewriting those from zero is the most likely way to accidentally lose
   one of them.
2. **Model choice: usually the cheapest model that follows instructions
   reliably.** Cross-referencing a claim against a transcript is a
   constrained, mechanical task, not open-ended reasoning — it doesn't need
   the same model as the primary agent it's judging. The real requirement is
   *reliably* returning the exact JSON shape, including the `reasoning.claims`
   list, every time; if a cheap model drifts off-format under real traces,
   that's the signal to move up, not before.
3. **Keep `tools: []`, deliberately.** A judge that can browse or query
   isn't cross-referencing anymore — it's a second investigator, and its
   score stops meaning "was this backed by the primary's own evidence."
   Resist adding tools even when it would make the judge "smarter."
4. **Size `max_tokens` to the step's claim count, not a guess.** [The
   grounding-accuracy troubleshooting
   guide](/docs/troubleshooting/fixing-grounding-accuracy/) covers this as
   a symptom (a parse failure, not a low score) — this section is the
   design-time version: a step whose output routinely makes many
   load-bearing claims needs a judge `max_tokens` sized for a
   proportionally long `reasoning.claims` list from the start, not
   discovered after the first parse failure in production.
5. **One shared judge, or several domain-specific ones?** `grounding.agent`
   defaults to `grounding-judge` but is settable per step — when a generic
   judge is the right default (most steps), and when a step's evidence is
   specialised enough (ticket-ID formats, dashboard UID conventions) that a
   step-specific judge with a slightly more informed `soul.md` catches more
   than a generic one would.
6. **Trust the judge before you enforce it.** Grounding's shadow mode
   exists exactly for this — watch its verdicts against steps you can
   manually verify for a while before flipping `enforce: true`, the same
   discipline [Choosing confidence
   thresholds](/docs/guides/choosing-confidence-thresholds/) recommends for
   the primary agent's own threshold.

## Where next

- **[Grounding](/docs/pipelines/grounding/)** — the full judge contract
  and config reference.
- **[Turn on grounding](/docs/tutorials/turning-on-grounding/)** — the
  hands-on tutorial this guide is the deeper companion to.
- **[Grounding keeps flagging real evidence as
  unsupported](/docs/troubleshooting/fixing-grounding-accuracy/)** — the
  `max_tokens` sizing problem from the symptom side.
