---
title: Prompt construction & session keys
description: The Jinja2 context every prompt template renders with, and how session keys isolate conversation state per step.
sidebar:
  order: 8
---

Every step's `prompt_template` is a Jinja2 template rendered against a fixed
set of context variables before it's sent to an executor. This page covers
what's available in that context, plus session keys — how a step's
conversation state is scoped and isolated.

## Prompt construction

Jinja2 renders prompt templates with a context dict containing:

- All fields from `context_template.include` resolved from
  `NormalisedContext`
- All fields from the pipeline `vars:` block
- `{{pipeline_run_id}}` — unique ID for this run
- `{{pipeline_name}}` — name of the current pipeline
- `{{current_step}}` — name of the current step
- `{{steps.step_name.field}}` — output fields from any previously completed
  step (hyphens → underscores: `first-line-triage` → `steps.first_line_triage`)
- `{{artifacts.step_name.key}}` — full text content of an artifact produced
  by a prior step (requires an `artifacts:` config block; hyphens →
  underscores same as above)
- `{{labels.service}}`, `{{labels.environment}}` etc. — `labels` dict is
  always present

## Session keys

Each pipeline step gets an isolated session key scoped to the run. Session
keys for the `openclaw` and `gateway` executors must start with
`agent:{agent-name}:` — the respective gateway validates this.

```yaml
session_key: "agent:sre-triage:{{pipeline_run_id}}:triage"
```

If `session_key` is omitted, the executor generates a default automatically.

## Where next

- **[Flow control](/docs/pipelines/flow-control/)** — the `when:` expressions
  and step context that use the same `{{ steps.step_name.field }}` references.
- **[Grounding](/docs/pipelines/grounding/)** — deterministic checks also
  render `shell.run`, `webhook.url`/`webhook.headers`/`webhook.payload`, and
  `human.message` through this same Jinja2 context.
