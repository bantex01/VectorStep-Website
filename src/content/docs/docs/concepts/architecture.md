---
title: Architecture
description: How VectorStep is put together — project overview, tech stack, directory layout, and the request flow from webhook to agent execution.
sidebar:
  order: 2
---

This page is the map: what VectorStep is, what it's built with, how the codebase
is laid out, and — in prose and a diagram — the path a single webhook takes
from arrival to a finished, confidence-scored pipeline run.

## Project overview

A **webhook-triggered, YAML-configured AI pipeline orchestration service**
built in Python with FastAPI. It receives webhooks from any source
(Alertmanager, Grafana, Atlassian, etc.), normalises the payload, resolves a
named pipeline config, and executes a multi-step AI pipeline using pluggable
agent executor backends.

The service is designed to be:

- **Source agnostic** — any webhook source is supported via pluggable parsers
- **Executor agnostic** — AI backends are adapters behind a common interface;
  steps in the same pipeline can mix executors freely
- **Config driven** — all pipeline logic lives in YAML files, not code
- **Modular** — adding a new source parser or executor adapter requires no
  changes to core logic

Primary use case is observability automation (alert triage, Grafana
investigation, bounded remediation) but the design is intentionally general
purpose.

## Tech stack

- **Python 3.11+**
- **FastAPI** — webhook endpoint, status/runs API, and UI routes
- **Pydantic v2** — normalised context schema, pipeline config models, LLM
  output validation
- **SQLAlchemy (async)** — pipeline run storage; SQLite (`aiosqlite`) for
  zero-infra local dev, PostgreSQL (`asyncpg`) recommended for production —
  see [Installation](/docs/getting-started/installation/#sqlite-vs-postgres)
- **httpx** — async HTTP client for webhook executor and notification
  delivery
- **websockets** — async WebSocket client for OpenClaw and VectorStep Gateway
  executors
- **Jinja2** — prompt template rendering (`{{variable}}` syntax in YAML
  configs) and HTML UI templates
- **PyYAML** — pipeline config loading
- **APScheduler 3.x** — in-process cron scheduler for time-triggered pipeline
  runs
- **uvicorn** — ASGI server for local development
- **OpenTelemetry** — optional per-run distributed tracing (disabled by
  default)

## Project structure

The tree below is trimmed to two levels — see
[Project structure](/docs/design/project-structure/) for the full layout of
`src/`, `samples/`, and friends.

```
samples/                      # Copy-and-adapt templates for new deployments (git controlled)
├── config.yaml.example         # Annotated service config template
├── pipelines/                  # Pipeline YAML templates — copy to service/pipelines/
└── steps/                      # Step definition templates — copy to service/steps/

service/
├── agents/                     # Agent SOUL.md drafts (copy into executor workspace)
├── pipelines/                  # Active pipeline configs (git controlled)
├── steps/                      # Reusable step library — gitignored, personal to deployment
├── src/                        # Application code — normaliser, executors, pipeline runner, models, db
├── templates/                  # Jinja2 HTML templates for the UI
├── logs/                       # Rotating log files (auto-created, gitignored)
├── tests/                      # Test suite and fixtures
├── Dockerfile
├── config.yaml                 # Service-level config — gitignored, copy from samples/config.yaml.example
└── requirements.txt
```

## The request flow

A single webhook's trip through the system touches every major subsystem in
order. In plain terms:

1. **Webhook** — a source (Alertmanager, Grafana, a generic JSON producer,
   anything) `POST`s to `/webhook?source=<name>`. This is the single entry
   point regardless of source.
2. **Normalise** — a source-specific parser (or the generic fallback)
   converts the raw payload into a `NormalisedContext`: a standard shape the
   rest of the system can reason about without caring where the alert came
   from.
3. **Resolve** — the resolver matches the normalised context against
   configured pipelines' trigger conditions and picks exactly one pipeline to
   run (subject to dedup/idempotency checks so the same incident doesn't fire
   the same pipeline twice).
4. **Run steps** — the pipeline runner walks the pipeline's step list in
   order (or in parallel groups), building up Jinja2 template context as each
   step completes so later steps can reference earlier outputs.
5. **Executors** — each step delegates the actual work to a pluggable
   executor adapter. Some executors call out to an agent backend; others
   (`webhook`, `notify`, `human`, `pipeline`) do something else entirely
   (an HTTP call, a notification, a human approval, a sub-pipeline).
6. **Gateway** — for steps using the `gateway` executor, the request goes
   over WebSocket to the VectorStep Gateway, which owns the full agentic loop.
7. **Providers / MCP** — the Gateway drives an LLM provider (Anthropic,
   OpenRouter, Google, Azure OpenAI, Ollama) through as many tool-calling
   turns as the agent needs, using MCP servers for tool access, and returns
   one clean, finished result back to VectorStep — no intermediate tool calls or
   thinking content cross that boundary.

Each step's result then feeds VectorStep's confidence machinery (self-report,
optional verifier, optional grounding, optional deterministic checks,
optional calibration — see [Confidence](/docs/concepts/confidence/)) before
the runner decides whether to proceed, escalate, or abort.

```
 source (Alertmanager, Grafana, generic JSON, ...)
        │
        │  POST /webhook?source=<name>
        ▼
 ┌───────────────┐
 │   Webhook      │  single entry point, all sources
 │   intake       │
 └───────┬───────┘
         ▼
 ┌───────────────┐
 │  Normalise     │  source parser → NormalisedContext
 └───────┬───────┘
         ▼
 ┌───────────────┐
 │  Resolve       │  match context → one pipeline (dedup/idempotency applied)
 └───────┬───────┘
         ▼
 ┌───────────────┐
 │  Run steps     │  pipeline runner walks steps / parallel groups
 └───────┬───────┘
         ▼
 ┌───────────────┐
 │  Executors     │  gateway | openclaw | webhook | notify | human | pipeline
 └───────┬───────┘
         │  (executor: gateway)
         ▼
 ┌───────────────┐
 │   Gateway      │  owns the full agentic loop over WebSocket
 └───────┬───────┘
         ▼
 ┌───────────────┐
 │ Providers/MCP  │  LLM calls + MCP tool execution, multi-turn
 └───────┬───────┘
         │
         ▼
   one clean result back to VectorStep
   (confidence scoring → proceed / escalate / abort)
```
