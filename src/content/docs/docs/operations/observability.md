---
title: Observability
description: Prometheus metrics, OpenTelemetry tracing, and logging for the VectorStep service.
sidebar:
  order: 2
---

The service exposes three complementary ways to see what it's doing:
cumulative Prometheus metrics for trends, per-run OpenTelemetry traces for
drill-down, and rotating log files for the raw event stream. This page covers
all three.

## Prometheus metrics

`GET /metrics` exposes Prometheus text-format metrics, computed from
`pipeline_runs` / `pipeline_steps` at scrape time. All counters are cumulative
all-time totals — use `rate()`/ratios in PromQL for escalation rate, per-agent
success rate, and verifier veto frequency rather than relying on pre-baked
percentages.

Every metric below is scoped to `stage=production` — a `stage=testing`
pipeline (the default, see [Pipeline stages](/docs/concepts/stages/))
contributes to none of them, including the metrics that query
`pipeline_steps` without otherwise touching `pipeline_runs`.

| Metric | Type | Labels | Description |
|---|---|---|---|
| `vectorstep_pipeline_runs_total` | counter | `pipeline`, `status` | Total runs by pipeline and terminal status |
| `vectorstep_pipeline_runs_in_progress` | gauge | — | Runs currently in `status=running` |
| `vectorstep_pipeline_steps_total` | counter | `pipeline`, `step_name`, `executor`, `agent`, `model`, `provider`, `status` | Total steps by pipeline, step, executor, agent, model, provider, and status. `pipeline`/`step_name`/`model`/`provider` are what let a Grafana dashboard reconstruct the per-step and per-model success-rate breakdowns the Pipelines/Steps/Agents Insights UI pages compute directly from the DB — the UI is for a quick look, this metric is for a real dashboard or alert. NULL agent/model/provider (non-gateway executors, or a gateway build predating the `provider` field) are bucketed as `""`. |
| `vectorstep_pipeline_step_duration_seconds` | histogram | `pipeline`, `step_name`, `executor`, `agent`, `model`, `provider` | Step execution duration (buckets: 1, 2, 5, 10, 30, 60, 120, 300, 600, 1200, +Inf seconds) |
| `vectorstep_verifier_runs_total` | counter | `agent` | Steps where a verifier ran, by primary agent |
| `vectorstep_verifier_overrides_total` | counter | `agent` | Verifier runs where the verifier lowered the primary's effective confidence |
| `vectorstep_pipeline_tokens_total` | counter | `team`, `pipeline`, `step_name`, `executor`, `agent`, `model`, `provider`, `direction` | Cumulative input/output tokens consumed, broken down by owning team ([Team attribution](/docs/operations/teams/)) for cost attribution. `direction` is `input`/`output`. NULL team/model/provider are bucketed as `""` rather than dropped, so unattributed spend stays visible. Steps from executors that don't report tokens (`openclaw`, `human`, `webhook`) are excluded rather than padded as zero. |
| `vectorstep_human_approval_decisions_total` | counter | `team`, `pipeline`, `decision` | Cumulative `human` step approve/reject decisions. `decision` is `approved`/`rejected`, derived from `primary_confidence` (1.0/0.0 — see the executor's contract). Timeouts leave `primary_confidence` NULL and are excluded rather than miscounted as either outcome. NULL team is bucketed as `""`. |
| `vectorstep_pipeline_feedback_total` | counter | `pipeline`, `outcome` | Cumulative human accuracy feedback. `outcome` is `correct`/`partial`/`incorrect`. |
| `vectorstep_step_feedback_total` | counter | `pipeline`, `step_name`, `agent`, `model`, `provider`, `outcome` | Cumulative per-step human accuracy feedback, production-scoped. `outcome` is `correct`/`partial`/`incorrect`. |
| `vectorstep_step_grounding_score` | histogram | `pipeline`, `step_name`, `agent`, `model`, `provider` | Shadow-mode grounding score (G) distribution per step, production-scoped (buckets: 0.1, 0.2, ..., 1.0, +Inf). Only steps with a `grounding:` block that produced a score contribute — NULL/not-computed steps are excluded, not padded as zero. |
| `vectorstep_step_deterministic_check_total` | counter | `pipeline`, `step_name`, `outcome` | Cumulative whole-step deterministic-check outcomes, production-scoped. `outcome` is `passed`/`failed` — `passed` only when every declared check for that step run passed. Steps with no `deterministic_checks:` declared are excluded. |
| `vectorstep_human_approvals_pending` | gauge | `team` | Currently pending `human` step approvals, awaiting a response on whichever channel (Telegram/Slack/Teams) that team is routed to. Unlike every other metric here this isn't derived from the database — pending approvals are in-memory only — so it reflects only this process's current state, not a historical/cumulative total. NULL team is bucketed as `""`. Always emits at least a zero-valued series so the metric doesn't disappear from dashboards when nothing's pending. Excludes `stage=testing` pending approvals, same as every other series on this page. |

Dollar-cost conversion is intentionally not provided — there's no per-model
pricing table yet, so this metric is raw token counts only.

Standard `python_*` / `process_*` / `python_gc_*` process-health metrics are
included automatically via `prometheus_client`'s default collectors.

## OpenTelemetry tracing

While `/metrics` gives aggregate, all-time counters, **distributed tracing
gives a per-run drill-down** — one trace per pipeline run, with a span for
every step, branch, verifier, and underlying LLM call. Use `/metrics` to spot
trends ("escalation rate is up this week"); use traces to answer "why was
*this* run slow / why did *this* step escalate".

Tracing is **disabled by default** and adds zero overhead until enabled — the
OTel SDK's default `TracerProvider` is a no-op.

**Enabling tracing** — add to `config.yaml`:

```yaml
observability:
  otel:
    enabled: true
    exporter: otlp          # otlp | console
    endpoint: http://localhost:4318/v1/traces   # OTLP/HTTP collector endpoint
    service_name: vectorstep-service
```

`exporter: console` prints spans to stdout — useful for local verification
without a collector. `exporter: otlp` (default) sends spans via OTLP/HTTP to a
collector (e.g. Grafana Alloy/Tempo).

**Span hierarchy** — each pipeline run is its own trace root:

```
pipeline.run: <team>/<pipeline>       (vectorstep.pipeline.name, vectorstep.run.id, vectorstep.source, vectorstep.team, vectorstep.run.status)
├── <step name>                       (vectorstep.span.kind=step, vectorstep.executor, vectorstep.agent, confidences, vectorstep.model, vectorstep.provider, vectorstep.prompt_hash, vectorstep.agent_version)
│   ├── gen_ai.<executor>             (vectorstep.span.kind=gen_ai — the LLM call itself)
│   └── <step>:verifier|:independent   (vectorstep.span.kind=verifier, vectorstep.verifier.mode, vectorstep.confidence)
│       └── gen_ai.<executor>
├── <group name>                      (vectorstep.span.kind=parallel_group, vectorstep.join_strategy, vectorstep.branch_count, vectorstep.agent_version)
│   ├── <branch name>                 (vectorstep.span.kind=branch, vectorstep.executor, vectorstep.agent, vectorstep.confidence, vectorstep.model, vectorstep.provider)
│   │   └── gen_ai.<executor>
│   └── ... (concurrent siblings)
├── <fan_out name>                    (vectorstep.span.kind=fan_out, vectorstep.join_strategy, vectorstep.prompt_hash, vectorstep.agent_version)
│   ├── <fan_out name>/0              (vectorstep.span.kind=branch, vectorstep.executor, vectorstep.agent, vectorstep.confidence)
│   │   └── gen_ai.<executor>
│   └── ... (one branch per runtime list item)
└── ...
```

`vectorstep.prompt_hash`/`vectorstep.agent_version` are set on the `<step name>` span
(from that step's own `prompt_template`) and the `<fan_out name>` group span
(all branches of a fan-out share one template, so a single hash is meaningful
there) — but deliberately **not** on individual branch spans or the `<group
name>` parallel_group span's `prompt_hash`, since each parallel branch has its
own distinct template and no single hash would be meaningful at the group
level. `vectorstep.agent_version` is set wherever a single agent's output is
available, including the parallel group span. Neither is added as a
Prometheus metric label — unbounded cardinality, since every prompt/agent
edit mints a new, permanently-retained label value.

The root span name is `pipeline.run: <team>/<pipeline-name>` when a team is
attributed (e.g. `pipeline.run: payments/alert-triage-critical`), or
`pipeline.run: <pipeline-name>` for unattributed runs. This makes the Name
column in Grafana Tempo immediately useful without needing to expand
attributes. `vectorstep.team` is also set as a span attribute when present, so
traces can be filtered/grouped by team in PromQL or Tempo query expressions.

Each run's structured log event (`step_started`, `verifier_ran`,
`branch_completed`, etc. — see [Run storage](/docs/operations/runs/)) is also
recorded as a **span event** on the current span, so the structured run log
and the trace timeline tell the same story from two angles.

**`gen_ai.*` span attributes:**

| Attribute | Description |
|---|---|
| `gen_ai.system` | Executor name (`openclaw`, `openclaw_ws`, `gateway`) |
| `gen_ai.request.model` | Model override requested, if any |
| `gen_ai.response.model` | Actual model used, from executor metadata |
| `vectorstep.gateway.duration_ms` | Backend-reported call duration |
| `vectorstep.agent` | Agent name |

**Forward compatibility with the VectorStep Gateway:** every `gen_ai.*` span
injects the current `traceparent`/`tracestate` (W3C Trace Context) into the
outbound `agent` request sent to the OpenClaw/VectorStep Gateway WebSocket APIs.
Today's gateways ignore these extra params. Once the VectorStep Gateway adds its
own OTel instrumentation, its LLM/tool-call spans will automatically nest
under the corresponding `gen_ai.*` span — giving one connected trace from
webhook → pipeline → step → individual LLM/tool calls, with no further
changes needed on the VectorStep side.

## Logging

The service writes rotating log files under the directory set by
`logging.dir` (`./logs` by default, auto-created, gitignored) — omit
`logging.dir` entirely to log to stdout only, which is the usual choice
inside a container or Kubernetes pod. Two files are produced:

- **`service.log`** — application logs (rotating, 10 MB × 5 files).
- **`access.log`** — HTTP access logs, kept **separate** from `service.log`
  so a busy webhook endpoint's request/response lines don't drown out actual
  application events when you're reading through them.

Both files rotate at 10 MB, keeping 5 generations. `logging.level` controls
verbosity (`INFO` by default). See
[Deployment](/docs/operations/deployment/) for the full `logging:` block in
context, and [Configuration reference](/docs/reference/config/) for every
field.
