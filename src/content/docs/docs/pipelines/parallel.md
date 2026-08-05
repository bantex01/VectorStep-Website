---
title: Parallel groups & fan-out
description: Running steps concurrently — static parallel groups and dynamic fan-out — and how their confidence scores join back together.
sidebar:
  order: 4
---

Pipelines aren't purely sequential. A `parallel:` entry runs a fixed set of
branches concurrently; a `fan_out:` entry runs a dynamic number of branches
decided at runtime. Both join their branches' confidence scores back into a
single effective score before standard [flow control](/docs/pipelines/flow-control/)
applies.

## Parallel groups

A `parallel:` entry in the step list runs multiple branches concurrently via
`asyncio.gather` and joins their confidence scores before applying standard
flow control.

```yaml
steps:
  - name: initial-triage
    executor: openclaw
    ...

  - parallel:
      name: context-gathering
      join: all_must_pass         # join strategy: all_must_pass | any_must_pass | weighted_average
      confidence_threshold: 0.70
      on_low_confidence: escalate
      on_abort: notify
      timeout_seconds: 90
      steps:
        - name: check-runbook
          executor: openclaw
          executor_config:
            agent: runbook-lookup
          prompt_template: |
            Look up the runbook for {{labels.service}}...
        - name: check-grafana
          executor: gateway
          executor_config:
            agent: grafana-analyst
          weight: 2.0             # optional — only used by weighted_average strategy
          prompt_template: |
            Check Grafana for {{labels.service}}...

  - name: remediation
    executor: openclaw
    prompt_template: |
      Runbook: {{steps.check_runbook.summary}}
      Grafana: {{steps.check_grafana.summary}}
```

**Join strategies:**

| Strategy | Behaviour |
|---|---|
| `all_must_pass` | `effective = min(all confidences)` — any weak branch drags down the group |
| `any_must_pass` | `effective = max(all confidences)` — useful when one source finding is enough |
| `weighted_average` | Weighted mean; each branch has an optional `weight:` (default 1.0) |

Branch outputs are registered individually so downstream steps reference them
as `{{steps.check_runbook.summary}}` — identical to sequential step
references.

## Fan-out — dynamic parallelism

Parallel groups (above) require branches to be listed in YAML at authoring
time. Fan-out makes parallelism dynamic: a step emits a list at runtime and
the runner spawns one branch per item, joining the results with the same
confidence strategies.

**Example use cases:**
- A "list affected services" step returns `["api", "worker", "db"]` → fan out
  one triage branch per service
- An alert normaliser returns a list of firing alerts → fan out one
  remediation branch per alert

```yaml
steps:
  - name: identify-services
    executor: gateway
    executor_config:
      agent: service-lister
    prompt_template: |
      List affected services as a JSON array under the key "services".
      Alert: {{ summary }}
      Return JSON: {"confidence": 0.0, "summary": "...", "next_step_context": "...", "services": ["svc-a", "svc-b"]}

  - fan_out:
      name: triage-services
      over: "{{ steps.identify_services.services }}"
      as: service                # variable injected into each branch's Jinja2 context
      executor: gateway
      executor_config:
        agent: sre-triage-agent
      prompt_template: |
        Triage service "{{ service }}" (branch {{ fan_out_index + 1 }} of {{ fan_out_total }}).
        Context: {{ steps.identify_services.next_step_context }}
      join: all_must_pass        # same strategies as parallel groups
      confidence_threshold: 0.75
      on_low_confidence: escalate
      on_abort: notify
      max_items: 20              # hard cap — step fails if list exceeds this
      on_empty: skip             # complete | skip | abort
      timeout_seconds: 90        # per-branch timeout
      when: "steps.identify_services.proceed == true"
      verifier:
        executor: gateway
        executor_config:
          agent: reviewer
        trigger:
          always: true

  - name: consolidate
    executor: gateway
    executor_config:
      agent: decision-agent
    prompt_template: |
      Branch 0 verdict: {{ steps['triage-services/0'].summary }}
      Branch 1 verdict: {{ steps['triage-services/1'].summary }}
```

### `over` resolution

The `over` value is a Jinja2 template rendered against the current step
context (the same context available in `prompt_template`). The rendered
result is interpreted as a Python list — if the agent returned a Python-repr
list (e.g. `"['a', 'b']"`), `ast.literal_eval` parses it; if it's a JSON
array, `json.loads` is the fallback. A non-list result or parse failure marks
the step as `failed`.

:::caution[Naming gotcha]
Avoid Python dict method names as extra field names. Jinja2 attribute access
(`dict.key`) tries `getattr` before `getitem`, so field names that shadow
Python dict built-ins (`items`, `keys`, `values`, `get`, `pop`, `update`,
etc.) resolve to the method object, not your data. Use descriptive names like
`services`, `alerts`, `affected_hosts` rather than `items`.
:::

### Per-branch context additions

| Variable | Value |
|---|---|
| `{{ service }}` (or whichever `as:` name you chose) | The current item value |
| `{{ fan_out_index }}` | 0-based position of this branch |
| `{{ fan_out_total }}` | Total number of branches spawned |

### Branch output references

Branch outputs are registered as `"{fan_out_name}/{index}"` — e.g.
`triage-services/0`, `triage-services/1`. Reference them downstream using
bracket notation (dot-notation breaks on `/`):

```yaml
{{ steps['triage-services/0'].summary }}
{{ steps['triage-services/1'].action }}
```

### Fan-out options

| Field | Default | Description |
|---|---|---|
| `over` | required | Jinja2 expression that resolves to a list |
| `as` | `item` | Variable name injected into each branch context |
| `join` | `all_must_pass` | `all_must_pass` \| `any_must_pass` \| `weighted_average` |
| `confidence_threshold` | `0.75` | Applied to the joined effective confidence |
| `on_low_confidence` | `escalate` | `escalate` \| `abort` \| `proceed` |
| `max_items` | `20` | Hard cap — step fails if the list is longer |
| `on_empty` | `complete` | `complete` (effective_confidence=1.0) \| `skip` (step skipped, no branch outputs) \| `abort` (step fails) |
| `timeout_seconds` | `null` | Per-branch timeout |
| `when` | `null` | Same conditional as sequential steps |
| `verifier` | `null` | Same verifier block as sequential steps — applied per branch |

See `samples/pipelines/fan-out-multi-service-triage.yaml` for a complete
worked example.
