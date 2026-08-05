---
title: Notifications
description: Wiring pipeline state transitions to outbound channels, and sending structured outbound webhooks with executor:notify.
sidebar:
  order: 9
---

VectorStep has two related but distinct ways to send something out of a pipeline:
a `notifications:` block that reacts to pipeline state transitions
(escalate, abort, stop, notify), and a first-class `executor: notify` step for
sending a structured outbound webhook as part of the pipeline's own step
sequence. This page covers both.

## Pipeline notification channels

The `notifications:` block in a pipeline YAML wires pipeline state
transitions (escalate, abort, stop, notify) to outbound channels. Three
channels are available:

| Channel | Config required | Description |
|---|---|---|
| `log` | None | Writes to the application logger — always available, zero dependencies |
| `telegram` | `notifications.telegram` in `config.yaml` | Sends a Telegram message via bot API |
| `webhook` | `url` in per-notification `config:` | POSTs the rendered template as an HTTP request body |

A single action can fan out to multiple channels by providing a list:

```yaml
notifications:
  escalate:
    - channel: log
      template: "ESCALATED: {{pipeline_name}} — {{step_summary}}"
      config:
        level: error
    - channel: telegram
      template: "🚨 {{pipeline_name}}: {{step_summary}}"
    - channel: webhook
      template: '{"text": "{{pipeline_name}} escalated: {{step_summary}}"}'
      config:
        url: https://hooks.slack.com/services/...
```

### `log` channel

Always registered — no `config.yaml` entry needed to enable it. The rendered
template is emitted via Python's standard `logging` module, landing in
whatever log aggregation stack (stdout, rotating file, Loki, CloudWatch) the
service ships to.

Per-notification `config:` keys:

| Key | Default | Description |
|---|---|---|
| `level` | `warning` | Log level: `debug` / `info` / `warning` / `error` / `critical`. Also accepts `warn` as an alias. |
| `logger` | `vectorstep.notifications` | Logger name. Override to route to a specific logger hierarchy. |

```yaml
notifications:
  escalate:
    - channel: log
      template: |
        ESCALATED: {{pipeline_name}} — {{step_summary}}
        Alert: {{context.summary}}  Confidence: {{confidence}}
      config:
        level: error

  notify:
    - channel: log
      template: "PIPELINE ABORTED: {{pipeline_name}} — {{step_summary}}"
      config:
        level: warning
        logger: vectorstep.ops            # route to a separate logger for ops tooling
```

The `log` channel is the recommended zero-setup choice for development and
for production environments that already aggregate application logs
centrally. Add `telegram` or `webhook` alongside it for real-time alerting.

### `telegram` channel

Requires `notifications.telegram.bot_token` and `notifications.telegram.chat_id`
in `config.yaml`. Messages use Telegram's HTML parse mode — `<b>`, `<code>`,
and `<a href>` tags work in templates. Messages longer than 4096 characters
are truncated with a `[truncated]` suffix.

### `webhook` channel

POSTs the rendered `template` string as the raw request body. Per-notification
`config:` keys match those of `executor: webhook` (url, method, content_type,
headers, timeout_seconds). For structured JSON payloads it is cleaner to use
an `executor: notify` step (see below) which renders a `payload:` dict rather
than requiring inline JSON in a template string.

## Outbound notification steps (`executor: notify`)

`executor: notify` is a first-class pipeline step that sends an outbound HTTP
webhook with a structured payload. Unlike `executor: webhook` (which uses
`prompt_template` as the raw request body), `notify` takes a `payload:` dict
in `executor_config` and recursively renders every string value as a Jinja2
template before JSON-encoding the body.

This makes it ergonomic for services that expect structured JSON
payloads — Slack blocks, PagerDuty events, Teams Adaptive Cards, Jira
tickets, etc. — without the author having to inline raw JSON inside a YAML
string.

```yaml
steps:
  - name: alert-pagerduty
    executor: notify
    when: "context.severity == 'critical'"
    on_failure: continue           # notification failure should not abort the run
    executor_config:
      url: "${PAGERDUTY_EVENTS_URL}"
      headers:
        Authorization: "Token token=${PAGERDUTY_TOKEN}"
      payload:
        routing_key: "${PAGERDUTY_ROUTING_KEY}"
        event_action: trigger
        payload:
          summary: "{{context.summary}}"
          severity: "{{context.severity}}"
          source: vectorstep
          custom_details:
            triage_summary: "{{steps.triage.output.summary}}"
            confidence: "{{steps.triage.output.confidence}}"

  - name: notify-slack
    executor: notify
    on_failure: continue
    executor_config:
      url: "${SLACK_WEBHOOK_URL}"
      payload:
        blocks:
          - type: section
            text:
              type: mrkdwn
              text: "*Alert:* {{context.summary}}\n*Triage:* {{steps.triage.output.summary}}"
```

`executor_config` keys:

| Key | Default | Description |
|---|---|---|
| `url` | required | Target URL (`${ENV_VAR}` expansion supported) |
| `method` | `POST` | HTTP method |
| `headers` | `{}` | Header dict; values support `${ENV_VAR}` expansion |
| `payload` | `{}` | Body dict; all string values are recursively rendered as Jinja2 templates |
| `content_type` | `application/json` | `Content-Type` header shorthand |
| `timeout_seconds` | `30` | Request timeout |

The step returns `confidence: 1.0` on success so it never triggers
low-confidence escalation. HTTP errors (non-2xx) propagate as executor
exceptions; combine with `on_failure: continue` so notification failures
never abort a pipeline run.

:::note[When to use `executor: notify` vs `executor: webhook`]
- Use `notify` when the target expects a structured JSON payload that you
  want to compose in YAML (Slack, PagerDuty, Teams, Jira, etc.)
- Use `webhook` when you need full control over the raw body and prefer
  rendering it as a `prompt_template` string
:::

## Where next

- **[Human-in-the-loop](/docs/pipelines/human-in-the-loop/)** — approval
  requests over Telegram, Slack, and Microsoft Teams, a different mechanism
  from the notification channels above.
- **[Flow control](/docs/pipelines/flow-control/)** — `on_failure` and the
  abort/escalate/stop transitions that the `notifications:` block reacts to.
