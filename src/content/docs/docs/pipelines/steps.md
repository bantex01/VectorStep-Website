---
title: Step library
description: Reusable step definitions shared across pipelines, and the deep-merge rules for use.
sidebar:
  order: 2
---

The step library (`service/steps/`) holds named, reusable step definitions.
A pipeline references one with `use: <step-name>` and can override any field —
overrides deep-merge over the library definition. Analytics aggregate per
library step across every pipeline that uses it.

Named step definitions live in `step_library_dir` (default `./steps`). Each
file defines a reusable step config that pipelines can reference by name using
a `use:` key. The loader resolves references before Pydantic validation, so
the runner is completely unaware of the library mechanism.

## Library step file

`steps/sre-investigation.yaml`:

```yaml
name: sre-investigation
description: Grafana RED metrics investigation — updates Jira with findings
tags: [investigation, grafana, openclaw]

executor: openclaw
executor_config:
  agent: sre-investigation
  session_key: "agent:sre-investigation:{{pipeline_run_id}}:{{current_step}}"
confidence_threshold: 0.60
on_low_confidence: escalate
timeout_seconds: 1200
prompt_template: |
  ... default prompt ...
```

## Referencing a library step in a pipeline

```yaml
steps:
  - use: first-line-triage          # fully inherits the library step

  - use: sre-investigation          # inherit config, override just the threshold
    confidence_threshold: 0.80

  - use: sre-investigation          # add a model override — executor_config is deep-merged
    executor_config:                # so agent/session_key are still inherited
      model: anthropic/claude-opus-4-8

  - use: sre-investigation          # custom prompt for this pipeline
    prompt_template: |
      Pipeline-specific prompt referencing {{steps.first_line_triage.summary}} ...
```

## Merge rules

- All top-level fields: local value wins if present, library value is the
  default.
- `executor_config` only: **deep-merged** — local keys add to or override
  library keys, rather than replacing the whole block. This lets you add
  `model` or `thinking_level` without repeating `agent` and `session_key`.
- `description` and `tags` are library-only metadata and are stripped before
  the step is passed to the runner.

## Step library UI

The `/ui/steps` page shows all loaded library steps with their
executor/agent, confidence threshold, tags, which pipelines reference each
step, and a copy button for the `- use: step-name` snippet. Each step with
run history also gets a **per-pipeline/agent/model breakdown table** — runs,
success rate, and avg tokens (in/out) for every distinct (pipeline, agent,
model) combination that's executed this step, since the same library step can
be wired to a different agent or model in different pipelines. Scoped to
`stage=production` runs, same as every other rollup surface (see
[Pipeline stages](/docs/concepts/stages/)).

## Hot reload

`POST /reload` and SIGHUP reload the step library first, then re-resolve all
pipeline references against the updated library. A **Reload config** button
on the `/ui/pipelines` page calls this endpoint directly from the browser.

:::caution
The `steps/` directory is gitignored. Step definitions reference your
specific agents, session key patterns, and confidence thresholds — they are
personal to your deployment, like `config.yaml`. Copy the starter definitions
from `samples/steps/` into `service/steps/` and adapt them to your agents.
:::

All templates live in `samples/` at the repo root — `samples/pipelines/` for
pipeline YAMLs and `samples/steps/` for step definitions. These are committed
reference files. Copy them into the appropriate `service/` subdirectory and
fill in your details.
