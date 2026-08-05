---
title: Testing vs production stages
description: Pipeline stages, what stage gates, and how runs are attributed to the stage they ran under.
sidebar:
  order: 3
---

Every pipeline declares `stage: testing` or `stage: production`. Stage controls
which webhook sources may trigger it, keeps testing runs out of production
rollups, and is persisted per-run — a run permanently records the stage its
pipeline had when it was triggered.

Every pipeline has a `stage: testing | production` field. `testing` is the
**default** — an unmarked or newly-authored pipeline is fully executable and
fully observable inside VectorStep's own UI, but inert to the outside world and
excluded from every aggregate metric. `production` is today's pre-existing
behaviour. Promotion is a one-line YAML diff, reviewed in git like any other
config change, applied with `POST /reload`/SIGHUP — **there is no UI toggle**,
consistent with `tags`/`version` staying git-controlled.

```yaml
name: my-pipeline
stage: testing        # testing (default) | production
...
```

`stage` is **pipeline-level only** — there is no step-level override. It is
persisted on the run row at trigger time (`pipeline_runs.stage`), not derived
by joining against the current pipeline config, so promoting a pipeline to
`production` never retroactively reclassifies its prior testing runs.

## What `testing` mutes

Four independent outbound paths are gated — every one of them logs what *would*
have happened instead of silently doing nothing:

| Path | Testing behaviour |
|---|---|
| `notifications:` block (see [Notifications](/docs/pipelines/notifications/)) | Forced to the `log` channel regardless of configured channel; run log gets a `notification_suppressed_testing` event instead of `notification_sent`. |
| `executor: notify` (see [Flow control](/docs/pipelines/flow-control/)) | The HTTP call is skipped; the rendered body is logged and the step returns a synthetic success (`confidence=1.0`, `raw_response.suppressed_testing=true`) so downstream steps still run. |
| Step-level `on_failure.webhook` (see [Flow control](/docs/pipelines/flow-control/)) | Skipped entirely; a `step_failure_webhook_suppressed_testing` run-log event records the URL that would have been called. |
| `executor: human` (see [Human in the loop](/docs/pipelines/human-in-the-loop/)) | The external channel (Telegram/Slack/Teams) is **not** sent — but the approval is still registered in VectorStep's own UI (`/ui/approvals` and the run-detail banner), so a real Approve/Reject decision can be made. A Reject still resolves to `confidence=0.0` and drives `on_low_confidence`/downstream `when:` exactly as in production. Unlike production, a timeout **auto-approves** (`confidence=1.0`) rather than failing the step, so a forgotten testing approval never wedges the pipeline. A testing pipeline with no `human_approval` config at all still works — the channel is never resolved/built when testing. |

All four gates key off a single `_testing` boolean the runner injects into every
step's Jinja2/executor context (`{{ _testing }}` is available in prompts, though
the muting itself is automatic — pipeline authors don't need to reference it).

## Trigger gating

A `stage: testing` pipeline does not fire from real ingestion traffic:

```bash
POST /webhook?source=alertmanager
# → {"status": "skipped_testing", "pipeline": "...", "reason": "..."}

POST /webhook?source=alertmanager&allow_testing=true
# → {"status": "accepted", "run_id": "..."}   — deliberately opted in
```

The **Run now** button (`POST /pipelines/{name}/run`) and re-run
(`POST /runs/{run_id}/rerun`) always run a testing pipeline — both are
deliberate manual actions, not real ingestion traffic.

## Metrics and UI exclusion

A `stage: testing` run contributes **zero** to every aggregate/rollup surface:
`GET /metrics` (all series, including `vectorstep_human_approvals_pending`, which
excludes testing approvals from its in-memory gauge the same way the
DB-backed counters do), the dashboard's stat cards and top-agents/top-tools
cards, the runs-page stat cards, pipeline success/accuracy bars, the
config-fingerprint accuracy comparison on `/ui/pipelines/{name}/feedback`, and
every Insights sub-page (`/ui/insights/pipelines`, `/steps`, `/agents`, `/models`, `/providers`, `/mcp`, `/teams`).

**Browse surfaces are the exception** — the runs list, dashboard's recent-runs
table, a pipeline's recent-runs table, and the chronological "every marked
run" table on the feedback page all show testing runs too, marked with an
amber **TESTING** badge, so testing activity stays fully visible for
debugging. `/ui/runs` has a `?stage=testing|production` filter (mirroring the
existing `team` filter) for browsing one stage at a time; the stat cards atop
that page always reflect production only, independent of this filter.

## Promotion workflow

1. Develop and exercise a pipeline with the default `stage: testing` (or set
   it explicitly) — run it via **Run now** or `?allow_testing=true`, watch it
   in the UI, confirm accuracy feedback looks right.
2. When ready, change one line: `stage: production`.
3. `POST /reload` (or SIGHUP). The pipeline now fires from real traffic, its
   outbound notifications/webhooks/approvals go out for real, and new runs
   count toward every metric and rollup. Prior testing runs are unaffected —
   the DB already recorded them as `stage=testing`.

See `samples/pipelines/stage-testing-example.yaml` for a complete worked example
covering all three testing-gated executor paths (`notify`, `on_failure.webhook`,
`human`) plus muted pipeline `notifications:`, with the promotion comment inline.
