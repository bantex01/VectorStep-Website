---
title: Pipeline schema
description: The full pipeline YAML reference — triggers, steps, executors, thresholds, flow control.
sidebar:
  order: 1
---

Pipelines are YAML files in `service/pipelines/`. Each declares a `trigger`
(source + match rules), a list of `steps` (each with an executor, prompt
template, confidence threshold and flow-control policy), and optional
pipeline-level settings (stage, tags, notifications, readiness criteria).
Steps can be defined inline or pulled from the reusable
[step library](/docs/pipelines/steps/) with `use:`.

## Model selection and verifiers

Model selection is handled by the named agent's own config in the executor
backend. To override the model for a specific step, set
`executor_config.model` — this is passed directly to the executor and takes
precedence over the agent's configured model.

Steps support an optional `verifier` block for independent confidence
verification by a second agent. The verifier trigger can be set to
`always: true` (fires unconditionally), or scoped to a confidence band. See
[Verifiers](/docs/pipelines/verifiers/) for full trigger configuration
examples.

## Step types

The `steps` list is heterogeneous — each entry is a sequential step (has a
`name:` key), a parallel group (has a `parallel:` key), or a fan-out (has a
`fan_out:` key). See [Parallel groups & fan-out](/docs/pipelines/parallel/)
for parallel groups and fan-out, and [Executors](/docs/integrations/executors/)
(`executor: pipeline`) for sub-pipeline calls.

## Full example

```yaml
name: alert-triage-critical
description: Full triage pipeline for critical alerts
tags: [critical, sre, grafana]  # optional — free-form labels, searchable on /ui/pipelines
version: 1
stage: production                # testing (default) | production — see §3c

trigger:
  match:
    severity: critical          # matched against NormalisedContext fields/labels
    environment: prod           # all conditions must match (AND logic)
  dedup:                        # optional — overrides config.yaml dedup.* for this pipeline
    window_seconds: 600         # see §3a

context_template:
  include:                      # fields auto-injected into every step prompt
    - severity
    - labels.service
    - labels.environment
    - summary

vars:                           # pipeline-level variables, available in all prompts
  jira_project: MYPROJECT
  confluence_space: MYSPACE

steps:
  - name: initial-triage
    executor: openclaw           # or: gateway | human | webhook
    executor_config:
      agent: sre-triage-sonnet          # named agent in the executor backend
      session_key: "agent:sre-triage-sonnet:{{pipeline_run_id}}:triage"
      model: anthropic/claude-sonnet-4-6   # optional — overrides agent's configured model
      thinking_level: low                  # optional — off|minimal|low|medium|high|xhigh
    confidence_threshold: 0.75
    on_low_confidence: escalate  # escalate | abort | proceed
    on_abort: notify
    timeout_seconds: 120
    prompt_template: |
      You are an SRE triaging a {{severity}} alert for {{labels.service}}
      in {{labels.environment}}.

      Alert summary: {{summary}}

      Return JSON only, no other text:
      {
        "confidence": 0.0,
        "summary": "...",
        "next_step_context": "...",
        "reasoning": {
          "supports": "...",
          "contradicts": "...",
          "assumptions": "..."
        }
      }

  - name: remediation
    executor: openclaw
    executor_config:
      agent: sre-remediation-sonnet
      session_key: "agent:sre-remediation-sonnet:{{pipeline_run_id}}:remediation"
    confidence_threshold: 0.85
    on_low_confidence: escalate
    on_abort: notify
    prompt_template: |
      Previous triage: {{steps.initial_triage.next_step_context}}
      ...
    verifier:
      executor: openclaw
      executor_config:
        agent: sre-verifier-opus
      combination_strategy: veto
      veto_floor: 0.60
      trigger:
        confidence_below: 0.95
        confidence_above: 0.50

notifications:
  escalate:
    - channel: log                   # always available — zero config required
      template: |
        ESCALATED: {{pipeline_name}} — {{step_summary}}
      config:
        level: error                 # debug | info | warning | error | critical
    - channel: telegram
      template: |
        Escalated: {{pipeline_name}}
        Service: {{labels.service}}
    - channel: webhook
      template: |
        {"text": "Escalated: {{pipeline_name}} — {{labels.service}}"}
      config:
        url: https://hooks.slack.com/services/...
        headers:
          Authorization: ${SLACK_TOKEN}

  notify:
    - channel: log
      template: "ABORTED: {{pipeline_name}} — {{step_summary}}"
      config:
        level: warning
    - channel: telegram
      template: |
        Aborted: {{pipeline_name}}
        Service: {{labels.service}}
        Step: {{current_step}}

schedule:                        # optional — omit for webhook-only pipelines
  cron: "*/5 * * * *"
  summary: "Scheduled health check for my-service"
  severity: warning
  labels:
    service: my-service
    environment: prod

budget:                          # optional — omit to run with no token/cost limit
  max_tokens: 50000              # abort run if accumulated tokens across all steps exceeds this
  max_usd: 5.00                  # abort run if accumulated cost across all steps exceeds this
  include_approx_cost: false     # let an unpriced step's live/approximate OpenRouter cost count toward max_usd
```

At least one of `max_tokens`/`max_usd` is required if `budget:` is present at
all; both may be set together (whichever trips first aborts the run and
names which limit it was). `include_approx_cost` can also be set per-step,
overriding the pipeline's default for that one step. See
[Cost accounting](/docs/operations/cost-accounting/) for `max_usd` and
live/approximate pricing in full.

## Token budget guardrail

If `budget.max_tokens` is set, the runner accumulates `input_tokens +
output_tokens` from each completed step (including all branches of
parallel/fan-out groups) and aborts the run with `status=aborted` if the total
exceeds the ceiling. The check runs after each successful step — a step
that's already failed or escalated won't trigger a second abort. A
`budget_exceeded` event is appended to the run log.

Token counts come from `meta.agentMeta.usage` in the VectorStep Gateway response.
Steps using other executors (`openclaw`, `human`, `webhook`) contribute 0
tokens to the accumulator — set `max_tokens` conservatively if your pipeline
mixes executor types.
