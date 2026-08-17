---
title: Writing good prompts
description: How to structure a prompt_template — what belongs in the prompt versus the agent, the output contract, and referencing prior-step data without breaking things.
sidebar:
  order: 2
---

An agent's `soul.md` (see [Writing good agents](/docs/guides/writing-good-agents/))
is its stable identity — who it is and how it behaves, every run. A step's
`prompt_template` is the opposite: what's true *this run* — this alert, this
service, whatever the previous step handed off. Mixing the two up is the
most common source of a prompt that's both bloated and strangely rigid. This
guide is about the `prompt_template` half. For the full templating
mechanics — the Jinja2 context, session keys — see [Prompt
construction](/docs/pipelines/prompts/).

## Keep run-varying data in the prompt, not the agent

If a fact changes between runs — which service, what the alert said, what a
prior step found — it belongs in `prompt_template`, rendered from
`{{labels.service}}`, `{{summary}}`, `{{steps.x.field}}`, or a pipeline
`vars:` entry. If it's true of the agent regardless of which run it's
handling — its job, its output format, what confidence means for it — that
belongs in `soul.md` instead. A prompt that repeats the agent's job
description every run is wasted tokens; a soul.md that hardcodes one run's
specifics is an agent that only works for that one alert.

## State the output contract every time, exactly

`confidence`, `summary`, and `next_step_context` are mandatory on every
response — see the [LLMOutput contract](/docs/reference/llm-output/). Show
the model the exact JSON shape it needs to return, close with *"Return ONLY
this JSON, no other text"*, and mean it — a single stray sentence before or
after the JSON breaks parsing, because the runner expects the whole response
body to parse as one object. Include `reasoning: {supports, contradicts,
assumptions}` too, even though it's optional — a `critic`-mode
[verifier](/docs/pipelines/verifiers/) and [grounding](/docs/pipelines/grounding/)
both read it, and so will you, six months from now, trying to work out why a
step decided what it decided.

```yaml
prompt_template: |
  A {{severity}} alert fired for {{labels.service}} in {{labels.environment}}.
  Summary: {{summary}}

  1. <task-specific instruction>
  2. <task-specific instruction>

  Return ONLY this JSON, no other text:
  {
    "confidence": 0.0,
    "summary": "One sentence: what's happening and what you found",
    "next_step_context": "Focused brief for the next step, or \"\" if terminal",
    "reasoning": {
      "supports": "Evidence that makes this credible",
      "contradicts": "Evidence that suggests otherwise",
      "assumptions": "What you're assuming in the absence of data"
    }
  }
```

## Include only what this step actually needs

`context_template.include` decides what's auto-injected into every step's
prompt; `vars:` adds pipeline-level constants. Both are easy to let grow
into a kitchen sink — every field anyone might conceivably want, included
everywhere, "just in case." Resist it. A prompt with ten fields the model
never uses is ten more things it might latch onto irrelevantly, and ten more
things a reader has to mentally filter out to see what the step actually
depends on. Include what this step's task genuinely needs; a later step can
include something different.

## Reference prior-step output precisely

`{{steps.step_name.field}}` pulls a mandatory or extra field from any
already-completed step; `{{artifacts.step_name.key}}` pulls the full text of
a stored artifact. The one real gotcha: **hyphens in step names become
underscores in the reference** — a step named `first-line-triage` is
`{{steps.first_line_triage.summary}}`, not
`{{steps.first-line-triage.summary}}`. This silently renders as an empty
Jinja2 lookup rather than erroring loudly, so a typo here reads at first
like the prior step "didn't return anything," not like a template mistake.
See [Prompt construction](/docs/pipelines/prompts/) for the full context
reference, including `{{pipeline_run_id}}`, `{{current_step}}`, and
`{{labels.*}}`.

## An edited prompt is a reset, not a tweak

`prompt_template`'s content hash is part of every calibration bucket's
key — editing it starts a fresh bucket at zero, discarding the measured
accuracy history for that exact step, same as editing an agent's `soul.md`
does on the Gateway side. See [Editing a prompt or an agent resets the
measurement](/docs/concepts/confidence/#editing-a-prompt-or-an-agent-resets-the-measurement--deliberately)
for exactly what you'll see when it happens. It's not a reason to avoid
editing prompts — it's a reason to batch changes deliberately rather than
tweak wording casually on a step with real production history.

## Where next

- **[Prompt construction & session keys](/docs/pipelines/prompts/)** — the
  full Jinja2 context reference.
- **[Writing good agents](/docs/guides/writing-good-agents/)** — the
  soul.md half of this same split.
- **[LLMOutput: the step contract](/docs/reference/llm-output/)** — every
  mandatory and optional response field.
