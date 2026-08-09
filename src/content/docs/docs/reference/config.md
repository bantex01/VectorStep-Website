---
title: Service configuration reference
description: Field-by-field reference for the VectorStep service's config.yaml — every top-level key, its sub-keys, valid values, and defaults.
sidebar:
  order: 5
---

This page is the field-by-field reference for the VectorStep service's
`config.yaml` — every top-level key and sub-key, what it does, its valid
values, and its default. For the operational how-to (where the file lives,
what you need to set to get a working deployment running end to end), see
[Deployment](/docs/operations/deployment/).

`config.yaml` lives at the service root:

```yaml
server:
  host: 0.0.0.0
  port: 8000

pipeline_config_dir: ./pipelines
step_library_dir: ./steps            # reusable step definitions; omit to disable library

database:
  url: sqlite+aiosqlite:///./runs.db
  # url: postgresql+asyncpg://user:password@localhost:5432/vectorstep   # production

notifications:
  telegram:
    bot_token: ${TELEGRAM_BOT_TOKEN}
    chat_id: ${TELEGRAM_CHAT_ID}

executors:
  openclaw:
    url: ws://127.0.0.1:18789/rpc      # OpenClaw Gateway WebSocket URL
  gateway:
    url: ws://localhost:18780/rpc        # VectorStep Gateway WebSocket URL
    token: ${VECTORSTEP_GATEWAY_TOKEN}        # Bearer token; empty string for local dev
    rest_url: http://localhost:18780    # VectorStep Gateway REST base URL (used by Agents UI)

logging:
  level: INFO
  dir: ./logs                          # omit to disable file logging (stdout only)
                                       # creates service.log and access.log (rotating, 10 MB × 5)

artifacts:
  dir: ./artifacts                     # omit this block entirely to disable artifact storage
  retention_days: 7                    # artifact directories older than this are removed daily at 02:00

dedup:
  enabled: true                        # omit this block (or set false) to disable dedup entirely
  window_seconds: 300                  # overridable per-pipeline via trigger.dedup

concurrency:
  max_runs: 10                         # maximum simultaneous pipeline executions (default: 10).
                                       # POST /webhook returns 429 when at capacity.
                                       # GET /health exposes active_runs / max_concurrent_runs.

auth:
  teams:                               # per-team tokens. Each team's token resolves
                                       # the `team` attribution on every run it authenticates.
    - name: payments
      token: ${VECTORSTEP_WEBHOOK_TOKEN_PAYMENTS}
    - name: platform
      token: ${VECTORSTEP_WEBHOOK_TOKEN_PLATFORM}
  # token: ${VECTORSTEP_WEBHOOK_TOKEN}       # legacy single-token form — still supported if `teams`
                                       # is omitted; every run's team is then unattributed (None).
                                       # If both `teams` and `token` are set, `teams` wins.
                                       # Omit this whole block (or leave empty) to run unauthenticated.
                                       # Alertmanager sends its token via http_config.authorization.credentials —
                                       # route different teams' alerts to different receivers with different tokens.

observability:
  otel:
    enabled: false                     # omit this block (or set false) to disable tracing entirely
    exporter: otlp                     # otlp | console
    endpoint: http://localhost:4318/v1/traces
    service_name: vectorstep-service

calibration:                           # omit this block entirely for the defaults shown below
  n_min: 20                            # marked outcomes required before a bucket is "validated"
  bin_width: 0.1                       # must evenly divide 1.0
  cache_ttl_seconds: 300                # how long the in-process bucket cache is reused before refetching

pricing:                               # omit this whole block to run fully unpriced
  currency: USD                        # display label only — no FX conversion anywhere
  models:
    - match: {provider: anthropic, model: "claude-sonnet-4-6"}
      input_per_mtok: 3.00              # currency units per 1,000,000 input tokens
      output_per_mtok: 15.00
  team_budgets:
    payments: 500                      # currency units per calendar month, UTC — advisory only
  live_pricing:
    enabled: false                     # optional — best-effort APPROXIMATE cost from OpenRouter's public catalog
    refresh_interval_seconds: 3600
```

`${ENV_VAR}` placeholders are resolved at startup. Unresolved placeholders
become `""`.

## server

| Key | Values | Default |
|---|---|---|
| `host` | bind address | `0.0.0.0` |
| `port` | bind port | `8000` |

## pipeline_config_dir / step_library_dir

- `pipeline_config_dir` — directory pipeline YAMLs are loaded from.
- `step_library_dir` — directory reusable step definitions are loaded from.
  Omit to disable the step library. See [Steps](/docs/pipelines/steps/).

## database

- `url` — a SQLAlchemy async database URL.
  - Local dev default: `sqlite+aiosqlite:///./runs.db` — zero infrastructure.
  - Production: `postgresql+asyncpg://user:password@localhost:5432/vectorstep` —
    same code path, dialect swap via config only. See
    [Deployment](/docs/operations/deployment/) for the operational detail on
    making this switch.
- `auto_migrate` — run pending Alembic migrations automatically on boot.
  Default `true`. Set `false` to hand migrations to a DBA — startup then
  fails fast, naming the pending revisions, instead of applying them. See
  [Deployment](/docs/operations/deployment/#database) for the full adoption
  mechanism.

## notifications

Per-channel notification config. The example above shows `telegram`
(`bot_token`, `chat_id`); see
[Pipeline notification channels](/docs/pipelines/notifications/) for the
full set of supported channels and how pipelines and steps route to them.

## executors

- `openclaw.url` — OpenClaw Gateway WebSocket URL.
- `gateway.url` — VectorStep Gateway WebSocket URL.
- `gateway.token` — Bearer token for the Gateway (`${VECTORSTEP_GATEWAY_TOKEN}`);
  empty string is fine for local dev.
- `gateway.rest_url` — VectorStep Gateway REST base URL, used by the Agents UI.

See [Executors](/docs/integrations/executors/) for the adapter pattern these
keys configure.

## logging

- `level` — log level, e.g. `INFO`.
- `dir` — directory for log files. Omit to disable file logging (stdout
  only). When set, creates `service.log` and `access.log` (rotating, 10 MB ×
  5 — `uvicorn.access` noise is kept out of `service.log`).

## artifacts

- `dir` — directory step artifacts are written to. Omit this block entirely
  to disable artifact storage.
- `retention_days` — artifact directories older than this are removed daily
  at 02:00. Default: `7`.

See [Artifact storage](/docs/operations/runs/) for the full artifact model.

## dedup

- `enabled` — `true`/`false`. Omit this block (or set `false`) to disable
  dedup entirely. Default: `true`.
- `window_seconds` — dedup window in seconds; overridable per-pipeline via
  `trigger.dedup`. Default: `300`.

See [Webhooks](/docs/integrations/webhooks/) for idempotency and
deduplication semantics.

## concurrency

- `max_runs` — maximum simultaneous pipeline executions. Default: `10`.
  `POST /webhook` returns 429 when at capacity; `GET /health` exposes
  `active_runs`/`max_concurrent_runs`.

## auth

- `teams` — list of `{name, token}` entries. Each team's token resolves the
  `team` attribution on every run it authenticates. See
  [Team attribution](/docs/operations/teams/).
- `token` — legacy single-token form, still supported if `teams` is omitted;
  every run's team is then unattributed (`None`). If both `teams` and
  `token` are set, `teams` wins.
- Omit this whole block (or leave it empty) to run unauthenticated.

:::note
Alertmanager sends its token via `http_config.authorization.credentials` —
route different teams' alerts to different receivers with different tokens.
:::

## observability

- `otel.enabled` — `true`/`false`. Omit this block (or set `false`) to
  disable tracing entirely. Default: `false`.
- `otel.exporter` — `otlp` | `console`.
- `otel.endpoint` — OTLP endpoint, e.g. `http://localhost:4318/v1/traces`.
- `otel.service_name` — service name reported to the tracing backend.

See [Observability](/docs/operations/observability/) for the full
metrics/tracing reference.

## calibration

Omit this block entirely for the defaults shown below.

- `n_min` — marked outcomes required before a bucket is "validated".
  Default: `20`.
- `bin_width` — width of each confidence bucket; must evenly divide 1.0.
  Default: `0.1`.
- `cache_ttl_seconds` — how long the in-process calibration bucket cache is
  reused before refetching. Default: `300`.

See [Calibration](/docs/pipelines/calibration/) for what these buckets
measure and how they're used.

## pricing

- `currency` — display label only, no FX conversion. Default: `USD`.
- `models` — the rate table: a list of `{match: {provider, model}, input_per_mtok,
  output_per_mtok}` entries, resolved by longest-prefix match on the step's
  model string, scoped by provider.
- `team_budgets` — `{team: amount}` map, currency units per calendar month
  (UTC). Advisory only, never blocks a run.
- `live_pricing.enabled` / `live_pricing.refresh_interval_seconds` — optional,
  best-effort *approximate* cost from OpenRouter's public catalog for
  otherwise-unpriced steps. Off by default.

Omit this whole block to run fully unpriced (every step's cost stays `NULL`,
every money surface shows "unpriced"). See
[Cost accounting](/docs/operations/cost-accounting/) for the full pricing
model, budget guardrails, and live/approximate pricing semantics.
