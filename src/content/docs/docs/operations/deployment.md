---
title: Deployment
description: Service configuration, database setup, Docker and Kubernetes deployment.
sidebar:
  order: 1
---

Local development runs on SQLite with zero infrastructure. Production runs on
PostgreSQL (`asyncpg`), with Prometheus metrics at `/metrics`, optional
OpenTelemetry tracing, rotating file logs, and a liveness/readiness probe at
`/health`.

This page walks through setting up the service's `config.yaml` in the order
you'd actually configure it, the SQLite-vs-Postgres decision, and deploying to
Kubernetes. For the exhaustive field-by-field reference of every key in
`config.yaml`, see [Configuration reference](/docs/reference/config/).

## Service configuration

`config.yaml` lives at the service root. Start from
`samples/config.yaml.example` and work through it top to bottom:

```yaml
server:
  host: 0.0.0.0
  port: 8000

pipeline_config_dir: ./pipelines
step_library_dir: ./steps            # reusable step definitions; omit to disable library

database:
  url: sqlite+aiosqlite:///./runs.db
  # url: postgresql+asyncpg://user:password@localhost:5432/vectorstep   # production — see Database below
  # auto_migrate: true   # run pending migrations on boot; false hands control to a DBA

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
  teams:                               # per-team tokens — see /docs/operations/teams/. Each team's
                                       # token resolves the `team` attribution on every run it authenticates.
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
    exporter: otlp                     # otlp | console — see /docs/operations/observability/
    endpoint: http://localhost:4318/v1/traces
    service_name: vectorstep-service

calibration:                           # omit this block entirely for the defaults shown below
  n_min: 20                            # marked outcomes required before a bucket is "validated"
  bin_width: 0.1                       # must evenly divide 1.0 — see Calibration
  cache_ttl_seconds: 300                # how long the in-process bucket cache is reused before refetching
```

`${ENV_VAR}` placeholders are resolved at startup. Unresolved placeholders
become `""`.

The order above roughly matches setup order in practice: get `server` and
`database` right first, wire up an executor so steps can actually run, add
`auth.teams` once you're ready to accept real webhooks from more than one
team, and turn on `observability`/`calibration` once the basics are working.
For the meaning of every individual field, see
[Configuration reference](/docs/reference/config/).

## Database

The ORM layer (SQLAlchemy async) is dialect-agnostic — switching backends is a
`database.url` change only, no code changes. Two supported backends:

| Backend | URL | When to use |
|---|---|---|
| SQLite (`aiosqlite`) | `sqlite+aiosqlite:///./runs.db` | Local dev, zero infrastructure, single process |
| PostgreSQL (`asyncpg`) | `postgresql+asyncpg://user:pass@host:5432/dbname` | Production — concurrent writers, real backup/replication story |

**Setup (Postgres):**

```bash
createdb vectorstep
# config.yaml:
database:
  url: postgresql+asyncpg://user:password@localhost:5432/vectorstep
```

Schema migrations run automatically on startup via
[Alembic](https://alembic.sqlalchemy.org/) (`create_tables()` in
`service/src/db/database.py`, calling `alembic upgrade head` programmatically)
— same as SQLite, no manual step for a normal boot.

**Migration mechanism.** `service/migrations/` holds the revision history;
`Base.metadata` (`service/src/db/models.py`) is the source of truth for the
ORM models, and revisions are generated with `alembic revision --autogenerate`
and reviewed, never trusted blind. On boot, `create_tables()` adopts whatever
state the database is already in:

- Already stamped at head → no-op.
- A brand-new, empty database → `alembic upgrade head` from scratch.
- Any pre-Alembic deployment (tables exist, no `alembic_version` table) — i.e.
  every database created by a VectorStep version older than this mechanism —
  gets a one-time legacy shim that brings it to exactly the baseline
  revision's shape (this is the old add-column/add-index mechanism: Postgres
  used native `ADD COLUMN IF NOT EXISTS`, SQLite fell back to a plain
  `ADD COLUMN` with the "already exists" error swallowed), stamps it at that
  baseline, then upgrades to head like any other database. Retained for one
  release cycle's worth of specs, then removed — by then every deployment
  that's booted at least once has been adopted.

Set `database.auto_migrate: false` (default `true`) to take migrations out of
the boot path entirely — for a DBA-controlled deployment. Startup then fails
fast, naming the pending revisions, if the schema is behind head, instead of
migrating it for you. Run migrations yourself with:

```bash
cd service && alembic upgrade head
```

**Dedup race hardening:** a partial unique index —
`UNIQUE (pipeline_name, fingerprint) WHERE status = 'running'` — closes a
TOCTOU race at the database layer, not just the application-level pre-check.
See [Webhooks](/docs/integrations/webhooks/) for the full dedup mechanism.

## Docker

The service ships a `Dockerfile` at `service/Dockerfile`, used as the base for
the Kubernetes build below.

## Kubernetes deployment

Target: ARM64 home lab cluster (Ubuntu snap k8s).

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/
COPY config.yaml .
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build for ARM64:

```bash
docker buildx build --platform linux/arm64 -t orchestration-service:latest .
```

Pipeline configs (from `samples/pipelines/` or your own) delivered via
Kubernetes ConfigMap mounted at `/app/pipelines/`. Step library (from
`samples/steps/` or your own) delivered via a separate ConfigMap mounted at
`/app/steps/`. Database: SQLite on a PersistentVolumeClaim for a
single-replica deployment, or PostgreSQL (in-cluster or managed) for
multi-replica — see [Database](#database) above. PostgreSQL is the only
option once you run more than one replica, since SQLite has no concept of a
network connection. Secrets (tokens) via Kubernetes Secrets as environment
variables. Log files written to a PersistentVolumeClaim or redirected to
stdout by omitting `logging.dir`.
