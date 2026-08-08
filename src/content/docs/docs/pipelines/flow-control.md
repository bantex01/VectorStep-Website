---
title: Flow control
description: How the runner decides what happens next after every step — statuses, conditionals, failure policy, and retries.
sidebar:
  order: 5
---

The `runner` controls all step execution and flow decisions. Agents never
decide what happens next — they only report findings and score confidence.
For each step:

0. Evaluate optional `when:` condition — if false, skip the step entirely
1. Parse and validate the LLM response as `LLMOutput` via Pydantic
2. Run verifier if configured and trigger fires
3. Check `effective_confidence` against `confidence_threshold`
4. If below threshold, apply `on_low_confidence` action (`escalate | abort | proceed`)
5. If confidence passes, check `proceed`:
   - `proceed: false` → pipeline stops with status `stopped`
   - `proceed: true` → continue to next step
6. If the executor raised an error (step status = `failed`), check `on_failure`:
   - `on_failure: abort` (default) → abort the pipeline
   - `on_failure: continue` → log and continue to next step
   - If `on_failure.webhook` is set, fire that callback regardless of policy
7. Record step result to SQLite before proceeding

## Step and run status reference

**Step statuses:**

| Status | Set when | Counts as failure? |
|---|---|---|
| `completed` | Step ran successfully and `proceed: true` | No |
| `stopped` | Step ran successfully and returned `proceed: false` | No |
| `escalated` | Confidence below threshold and `on_low_confidence: escalate` | No |
| `aborted` | Confidence below threshold and `on_low_confidence: abort` | No |
| `failed` | Executor exception, timeout, bad JSON, or schema validation error | **Yes** |

For agent success rate calculations, `failed` is the only status that counts
against a model.

**Pipeline run statuses:**

| Status | Meaning |
|---|---|
| `completed` | All steps ran to completion |
| `stopped` | A step returned `proceed: false` — clean intentional stop |
| `escalated` | A step was escalated — run halted, human notified |
| `aborted` | A step aborted due to low confidence |
| `failed` | A step raised an unhandled error |
| `running` | Currently in progress |
| `interrupted` | Service restarted/crashed mid-run — set by the startup sweep, not the runner. A pipeline with `durable:` set resumes instead of landing here, unless the guard conditions in [Durability & resume](/docs/operations/durability/) rule it out |

## Conditional steps (`when:`)

Any sequential step or parallel group can have an optional `when:` field
containing a Jinja2-compatible boolean expression. A false result skips the
step cleanly — no DB row, no executor call, invisible to subsequent steps.

```yaml
steps:
  - name: triage
    executor: openclaw
    executor_config:
      agent: sre-triage
    prompt_template: |
      Analyse the alert. Return JSON with an "action" field: "remediate" | "escalate_human" | "ignore"

  - name: auto-remediation
    when: "steps.triage.action == 'remediate'"
    executor: openclaw
    executor_config:
      agent: sre-remediator
    prompt_template: |
      Triage says: {{steps.triage.summary}}. Attempt remediation.

  - name: page-oncall
    when: "steps.triage.action == 'escalate_human'"
    executor: human
    prompt_template: |
      <b>Page oncall?</b> Triage: {{steps.triage.summary}}
```

**`when:` vs `proceed: false`:**
- `when:` — pipeline author decides in advance which steps are relevant given
  prior step outputs
- `proceed: false` — the agent signals the pipeline is complete and no
  further steps are warranted

## Per-step failure policy (`on_failure`)

By default a failed step (executor exception, timeout) aborts the pipeline.
For non-critical steps — enrichment lookups, external API calls,
notifications — you can allow failures to pass through:

```yaml
- name: enrich-from-cmdb
  executor: webhook
  on_failure: continue       # pipeline keeps running if this step fails
  executor_config:
    url: "https://cmdb.internal/api/enrich"
```

The step is still recorded in run history with `status: failed` and the
error message is available in `step_outputs[name].summary` for downstream
`when:` conditions or prompt templates.

`on_failure` only applies to executor errors. Low-confidence results that
trigger `on_low_confidence: abort` are LLM-quality decisions and are always
pipeline-stopping regardless of this setting.

### Step-level failure webhook callback

Attach a webhook to any step that fires when that step fails, without adding
a separate notify step to the pipeline. The callback fires before the
pipeline decides whether to abort or continue, so it always goes out
regardless of the policy.

```yaml
- name: triage
  executor: gateway
  executor_config:
    agent: sre-triage
  on_failure:
    policy: continue        # pipeline continues even if this step fails
    webhook:
      url: "${PAGERDUTY_URL}"
      headers:
        Authorization: "Token ${PAGERDUTY_TOKEN}"
      payload:
        summary: "Triage step failed: {{step_failure.summary}}"
        severity: critical
```

`on_failure` as a block:

| Field | Default | Description |
|---|---|---|
| `policy` | `abort` | `abort` or `continue` — what the pipeline does after the failure |
| `webhook.url` | required | Outbound URL (`${ENV_VAR}` expansion supported) |
| `webhook.method` | `POST` | HTTP method |
| `webhook.headers` | `{}` | Header dict; values support `${ENV_VAR}` expansion |
| `webhook.payload` | `{}` | JSON body dict; string values are Jinja2 templates |
| `webhook.timeout_seconds` | `30` | Request timeout |

String shorthand (`on_failure: continue` or `on_failure: abort`) is
equivalent to setting `policy` only with no webhook.

The Jinja2 context for the webhook payload includes all standard step context
variables plus `step_failure.step`, `step_failure.summary`, and
`step_failure.status`. Webhook delivery failures are logged as a
`step_failure_webhook_failed` run-log event and never abort the pipeline.

:::note
`executor: notify` — a separate, first-class outbound-notification step type
for sending structured JSON payloads (Slack, PagerDuty, Teams, Jira) — is
covered on its own page: [Notifications](/docs/pipelines/notifications/).
:::

## Retry logic

Optional `retry:` block on any step. Retries wrap the executor call only —
low-confidence results are valid outputs and are never retried.

```yaml
retry:
  attempts: 3
  backoff: exponential   # fixed | exponential
  delay_seconds: 2.0
```
