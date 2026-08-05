---
title: REST API
description: Management, analytics, and write endpoints for the VectorStep service.
sidebar:
  order: 1
---

The service exposes a full JSON API: run triggering and inspection, live SSE
run tailing, pipeline/step CRUD with validation, per-pipeline and per-step
analytics, calibration bins, prompt/agent version history, readiness readouts,
accuracy feedback, Prometheus metrics, and health probes.

This page covers the core management endpoints — triggering and inspecting
runs, feedback, pipeline listing, metrics, and health. For the read-only
pipeline/step/agent analytics endpoints, see
[Analytics API](/docs/reference/analytics-api/). For the endpoints that
create, update, validate, and delete pipelines and steps, see
[Write API](/docs/reference/write-api/) — both were added to back the
[VectorStep Service MCP](/docs/reference/write-api/#the-p-ork-service-mcp).

## Triggering runs

### POST /webhook?source=&lt;source&gt;

Trigger a run. Returns immediately — the pipeline runs in the background.

- → `{"status": "accepted", "run_id": "<uuid>"}`
- → `{"status": "deduplicated", "run_id": "<uuid>", "reason": "..."}` — see
  [Webhooks](/docs/integrations/webhooks/) for idempotency and deduplication.
- → `{"status": "skipped_testing", "pipeline": "...", "reason": "..."}` — see
  [Pipeline stages](/docs/concepts/stages/); pass `?allow_testing=true` to run
  a `stage: testing` pipeline from this source anyway.

### POST /pipelines/{name}/run

Manually trigger a pipeline by name — powers the UI's **Run now** button.

:::note
Not behind webhook Bearer auth. This is an internal/management action, at the
same trust boundary as `/reload` — not the public ingestion path that
`auth.teams` gates. Runs triggered here are unattributed (`team=None`).
:::

- body: same shape as a generic webhook payload (see
  [Webhooks](/docs/integrations/webhooks/)), pipeline forced from the path
- → `{"status": "accepted", "run_id": "<uuid>", ...}`

## Reload

### POST /reload

Reload the step library and all pipeline YAMLs from disk without restarting.

→ `{"status": "reloaded", "pipelines_loaded": 3}`

`SIGHUP` also triggers a reload:

```bash
kill -HUP <uvicorn-pid>
```

## Schedules

### GET /schedules

List active cron schedules.

→ `{"schedules": [{"pipeline": "...", "cron": "...", "next_run": "..."}]}`

## Runs

### GET /runs

List runs, newest first.

Filters: `?status=escalated`, `?pipeline=alert-triage-critical`,
`?team=payments`, `?stage=production|testing`.

Pagination: `?limit=50&offset=0` (max 200).

→ `{"runs": [{id, pipeline_name, source, status, team, stage, triggered_at, completed_at}, ...]}`

`stage` is `"testing"` or `"production"` (see
[Pipeline stages](/docs/concepts/stages/)), included on both this list and the
full detail response below — it's persisted per-run, so it reflects the
pipeline's stage at the time the run was triggered rather than its current
config.

### GET /runs/{run_id}

Full run detail — includes all steps with confidence scores and parsed
output.

### POST /runs/{run_id}/rerun

Re-run a pipeline from a specific step.

- body: `{"from_step": "step-name"}`

## Feedback

### POST /runs/{run_id}/feedback

Submit or update human accuracy feedback for a run (`outcome`: `correct` |
`partial` | `incorrect`).

- body: `{"outcome": "correct", "notes": "..."}`
- → `{"run_id": "...", "outcome": "correct", "notes": "...", "submitted_at": "..."}`

Upserts — submitting again overwrites the previous outcome and notes.

### GET /runs/{run_id}/feedback

Get current feedback for a run.

→ `{"feedback": {run_id, outcome, notes, submitted_at}}` or `{"feedback": null}`

### POST /runs/{run_id}/steps/{step_name}/feedback

Submit or update human accuracy feedback for a single step execution
(`outcome`: `correct` | `partial` | `incorrect`). `step_name` may contain `/`
for fan-out branches (e.g. `triage/0`) — the route uses a path converter to
match it.

- body: `{"outcome": "correct", "notes": "..."}`
- → `{"run_id": "...", "step_name": "...", "outcome": "correct", "notes": "...", "submitted_at": "..."}`

Upserts — submitting again overwrites the previous outcome and notes.

### GET /runs/{run_id}/steps/{step_name}/feedback

Get current feedback for a single step execution.

→ `{"feedback": {run_id, step_name, outcome, notes, submitted_at}}` or
`{"feedback": null}`

## Live tailing

### GET /ui/runs/{run_id}/stream

Server-Sent Events stream for live run tailing. See
[UI: run detail](/docs/ui/run-detail/).

## Pipelines and observability

### GET /pipelines

List loaded pipelines — includes `stage` and `tags` alongside
name/description/version.

### GET /metrics

Prometheus metrics — runs/steps by status, step duration histograms, verifier
veto rate.

### GET /health

Liveness/readiness probe — also surfaces in-process concurrency state.

→ `{"status": "ok", "active_runs": 0, "max_concurrent_runs": 10}`
