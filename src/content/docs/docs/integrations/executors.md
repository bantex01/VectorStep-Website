---
title: Executors
description: The executor adapter pattern — Gateway, OpenClaw, human-in-the-loop, webhook, sub-pipeline.
sidebar:
  order: 2
---

AI backends are adapters behind a common interface; steps in the same pipeline
can mix executors freely: `gateway` (VectorStep Gateway agents), `openclaw`,
`human` (Telegram/Slack/Teams approvals), `webhook` (HTTP POST out),
`pipeline` (sub-pipelines), and `notify`.

## Executor adapter pattern

All executors implement `BaseExecutor`:

```python
class BaseExecutor(ABC):
    @abstractmethod
    async def execute(self, step: StepConfig, context: dict) -> LLMOutput:
        pass
```

Executors are registered by name in `src/executors/__init__.py` and referenced by name in pipeline YAML step `executor:` fields. Steps within the same pipeline can freely mix executors. Registered executors: `openclaw`, `gateway`, `human`, `webhook`, `notify`, `pipeline`.

### `openclaw` — OpenClaw Gateway WebSocket

**`executor: openclaw`** — Invokes OpenClaw agents via the OpenClaw Gateway WebSocket API (`ws://127.0.0.1:18789/rpc`). Uses Ed25519 device-signature auth from `~/.openclaw/identity/`. Fires an `agent` call and waits for the final result frame. Session isolation is server-side — no file deletion needed. Scans payloads in reverse for the last valid JSON block.

`executor_config` keys:

| Key | Required | Description |
|---|---|---|
| `agent` | **Yes** | OpenClaw agent name |
| `session_key` | No | Jinja2 template; must start with `agent:{agent-name}:`. Default: `agent:{{agent}}:pipeline:{{pipeline_run_id}}:{{current_step}}` |
| `model` | No | Model override, e.g. `anthropic/claude-sonnet-4-6`. Overrides the agent's configured model. |
| `thinking_level` | No | `off\|minimal\|low\|medium\|high\|xhigh` — controls model thinking budget |

**Service-level config** (under `executors.openclaw` in `config.yaml`, not per-step):

| Key | Default | Description |
|---|---|---|
| `url` | `ws://127.0.0.1:18789/rpc` | OpenClaw Gateway WebSocket URL |
| `identity_dir` | `~/.openclaw/identity` | Path to the directory containing `device.json` and `device-auth.json`. Override when OpenClaw is on a different machine and you have copied the identity files to a custom path. |

### `gateway` — VectorStep Gateway WebSocket

**`executor: gateway`** — Invokes agents via the VectorStep Gateway WebSocket API. Token-based auth (no device identity required). The VectorStep Gateway is a separate service that can run different model backends (Anthropic, OpenRouter, Ollama, Google) and MCP tool configurations independent of OpenClaw.

`executor_config` keys:

| Key | Required | Description |
|---|---|---|
| `agent` | **Yes** | VectorStep Gateway agent name |
| `session_key` | No | Jinja2 template; must start with `agent:{agent-name}:`. Default: `agent:{{agent}}:pipeline:{{pipeline_run_id}}:{{step_name}}` |
| `model` | No | Model override string, e.g. `anthropic/claude-sonnet-4-6`, `openrouter/...`, `ollama-cloud/...` |
| `thinking_level` | No | Thinking level override: `low\|medium\|high` etc. |
| `timeout_seconds` | No | Per-request timeout override (default: 1200) |
| `trace_max_chars` | No | Overrides the Gateway's `limits.trace_tool_result_max_chars` (default 3000) for this step's `tool_result` trace events only — sent as `traceToolResultMax` on the agent request. Only affects the trace copy recorded/streamed for observability (and what `grounding.max_trace_chars` has available to hand the judge — see [Confidence & the trust vector](/docs/concepts/confidence/)). The agent's own conversation always sees the full, untruncated tool output regardless of this setting. Raise it on steps whose tools return long content if grounding or a human reviewing the trace is drawing false conclusions from evidence that was cut off before the Gateway ever sent it to VectorStep. |

Requires `executors.gateway.url` (WebSocket) and `executors.gateway.rest_url` (REST) in `config.yaml`.

The VectorStep Gateway exposes three REST endpoints consumed by VectorStep:

| Endpoint | Purpose |
|---|---|
| `GET /agents` | Agent list (name, model, model_fallbacks, tools) |
| `GET /agents/{name}/soul` | `soul.md` content — shown in the Soul tab of the agent detail page |
| `GET /agents/{name}/agent` | Raw `agent.yaml` content — shown in the Config tab of the agent detail page |

#### Differences from the OpenClaw executor

| | OpenClaw executor | Gateway executor |
|---|---|---|
| Auth | Ed25519 device signature | Bearer token |
| Session isolation | Server-side (no file clearing) | Server-side |
| Model routing | OpenClaw agent config | Gateway `providers:` config |
| MCP tools | OpenClaw MCP servers | Gateway `mcp_servers:` config |
| Thinking parameter | `thinking` | `thinkingLevel` |
| OTel trace propagation | Not supported | Supported — joins VectorStep's trace |

### `human` — Human-in-the-Loop (Telegram, Slack, Microsoft Teams)

**`executor: human`** — Sends an approval request and pauses the pipeline until the operator approves or rejects, or `timeout_seconds` elapses. Which channel a run uses is resolved per-team (Telegram, Slack, or Microsoft Teams), not per-pipeline, so the same `executor: human` step works unchanged for every team. Testing-stage pipelines behave differently here too — approvals still fire, but routing and defaults account for the pipeline not yet being promoted to production.

The full mechanics — outcome/confidence mapping, per-team channel config, the Telegram/Slack/Teams credential requirements, and the `/ui/approvals` review flow — live on their own page: see [Human-in-the-loop](/docs/pipelines/human-in-the-loop/).

### `webhook` — HTTP POST Output

**`executor: webhook`** — POSTs the rendered `prompt_template` as the request body to a URL. Returns `confidence=1.0` on any HTTP 2xx. Non-2xx raises and triggers the step's retry/fail flow. The response body (up to 500 chars) is stored in `next_step_context` so downstream steps can reference it.

`executor_config` keys:

| Key | Required | Description |
|---|---|---|
| `url` | **Yes** | Target URL |
| `method` | No | HTTP method (default: `POST`) |
| `content_type` | No | Content-Type header (default: `application/json`) |
| `headers` | No | Extra headers; `${ENV_VAR}` substitution supported |
| `timeout_seconds` | No | Per-request timeout (default: 30) |

```yaml
- name: notify-slack
  executor: webhook
  executor_config:
    url: https://hooks.slack.com/services/...
    headers:
      Authorization: ${SLACK_TOKEN}
  confidence_threshold: 0.0
  on_low_confidence: proceed
  prompt_template: |
    {"text": "Alert resolved: {{labels.service}} — {{steps.triage.summary}}"}
```

### `pipeline` — Sub-Pipeline Call

**`executor: pipeline`** — Calls another named pipeline as a sub-pipeline. The sub-pipeline runs through the standard runner — full step execution, DB row, tracing — and its final step's `LLMOutput` becomes the current step's output. This turns pipelines into composable building blocks.

`executor_config` keys:

| Key | Required | Description |
|---|---|---|
| `pipeline` | **Yes** | Name of the pipeline to call. Must be loaded and present in the pipeline registry at call time. |
| `context` | No | `NormalisedContext` field overrides. Scalar fields are Jinja2-rendered strings. `labels` and `metadata` are dicts — rendered keys are **merged** with the parent values (parent keys preserved; overrides add or replace individual keys). |

The sub-pipeline inherits the parent's `NormalisedContext` by default. The `pipeline` and `source` fields are updated (`source` → `"sub-pipeline"`) and `fingerprint` is cleared (bypasses dedup). `team` is inherited unchanged like `labels`/`metadata`, so a shared sub-pipeline's token spend rolls up to whichever team's call triggered it — overridable via `context: {team: "..."}` like any other field. Use `context:` to pass step-specific values:

```yaml
- name: triage
  executor: pipeline
  executor_config:
    pipeline: shared-triage
    context:
      # Scalar field override — Jinja2-rendered
      summary: "{{ steps.pre_filter.next_step_context }}"
      # Dict field override — merged with parent labels
      labels:
        routed_by: "{{ pipeline_name }}"
      metadata:
        focus: "Check database connection pool first"
  confidence_threshold: 0.75
  on_low_confidence: escalate
```

**Sub-pipeline DB linkage:** the sub-pipeline runs with its own `run_id`, stored in `pipeline_runs` with `parent_run_id` set to the parent run's ID. This makes sub-pipeline runs fully traceable — you can query `SELECT * FROM pipeline_runs WHERE parent_run_id = '<parent-run-id>'` to see all sub-pipeline invocations for a parent run.

**Extra fields on the parent step output:**

| Field | Description |
|---|---|
| `sub_run_id` | The `run_id` assigned to the sub-pipeline run |
| `sub_pipeline_status` | Terminal status of the sub-pipeline (`completed`, `failed`, `escalated`, etc.) |

These are available downstream as `{{ steps.triage.sub_run_id }}` and `{{ steps.triage.sub_pipeline_status }}`.

**Failure behaviour:** if the sub-pipeline has a `final_output` (its last step ran and produced output), that output is used as-is regardless of sub-pipeline status. If the sub-pipeline has no `final_output` (it was aborted/escalated before any step completed), the parent step synthesises an `LLMOutput` with `confidence=1.0` (completed) or `confidence=0.0` (any other status).

**Hot reload:** `POST /reload` and SIGHUP update the pipeline registry, so changes to a sub-pipeline YAML take effect immediately without restarting the service.

**Using `executor: pipeline` in a fan-out:** each fan-out branch can delegate to a sub-pipeline, passing the branch item via `context:`:

```yaml
- fan_out:
    name: per-service-triage
    over: "{{ steps.identify_services.services }}"
    as: service
    executor: pipeline
    executor_config:
      pipeline: shared-triage
      context:
        labels:
          service: "{{ service }}"
        metadata:
          focus: "Focus specifically on {{ service }}"
    join: all_must_pass
    confidence_threshold: 0.75
    on_low_confidence: escalate
```

See `samples/pipelines/sub-pipeline-example.yaml` for a complete worked example including conditional routing based on sub-pipeline output.

## Adding a new executor

1. Create `src/executors/<name>.py`
2. Implement `BaseExecutor` — accept `StepConfig` + context dict, return `LLMOutput`
3. Register in `src/executors/__init__.py` executor map
4. Reference by name in pipeline YAML step `executor:` field

No other changes required. See [Extending VectorStep](/docs/design/extending/) for
the full checklist shared across executors, parsers, and library steps.
