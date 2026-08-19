---
title: Project structure
description: The full repository layout of the VectorStep engine repo — every directory and what lives in it.
sidebar:
  order: 4
---

The full tree below covers everything under `samples/` and `service/`. For a
trimmed, two-level overview alongside the request-flow diagram, see
[Architecture](/docs/design/architecture/).

```
samples/                      # Copy-and-adapt templates for new deployments (git controlled)
├── config.yaml.example         # Annotated service config template
├── pipelines/                  # Pipeline YAML templates — copy to service/pipelines/
│   ├── alert-triage-investigation-using-steps.yaml
│   ├── fan-out-multi-service-triage.yaml
│   ├── sub-pipeline-example.yaml
│   ├── generic-webhook-new-order.yaml
│   ├── human-approval-test.yaml
│   ├── otel-triage-verified.yaml
│   ├── tagged-example.yaml
│   └── stage-testing-example.yaml
└── steps/                      # Step definition templates — copy to service/steps/
    ├── first-line-triage.yaml
    ├── sre-investigation.yaml
    ├── sre-investigation-verified.yaml
    ├── order-intake.yaml
    ├── customer-comms.yaml
    └── service-health-check.yaml

service/
├── agents/                     # Agent SOUL.md drafts (copy into executor workspace)
│   ├── order-intake/SOUL.md
│   └── customer-comms/SOUL.md
├── pipelines/                  # Active pipeline configs (git controlled)
│   └── *.yaml
├── steps/                      # Reusable step library — gitignored, personal to deployment
│   └── *.yaml                  # Copy from samples/steps/ and adapt
├── src/
│   ├── main.py                 # FastAPI app entry point, lifespan, webhook endpoint
│   ├── tracing.py              # OpenTelemetry tracing setup + span helpers
│   ├── gateway.py              # Lightweight helper for calling OpenClaw Gateway WS API
│   ├── ui/                     # UI routes (pipeline/agent/step library, run history)
│   │   ├── helpers.py           # Shared template helpers, Jinja2Templates instance, agent-fetch plumbing
│   │   ├── dashboard.py         # /ui root dashboard
│   │   ├── runs.py              # Runs list/detail/log, live tail, rerun
│   │   ├── pipelines.py         # Pipeline library/detail, run-now, schedules, feedback
│   │   ├── steps.py             # Step library, calibration/feedback, marking queue
│   │   ├── agents.py            # Agent library (Gateway-backed pages)
│   │   ├── insights.py          # /ui/insights overview, pipelines, mcp, teams
│   │   ├── insights_trust.py    # /ui/insights steps, agents, providers, models (calibration/trust)
│   │   └── approvals.py         # HITL approvals pages
│   ├── analytics.py             # Shared rollup queries — feeds both /ui/insights/* and read/analytics JSON endpoints
│   ├── config_writer.py        # Atomic validated-write path for pipeline/step YAML
│   ├── normaliser/
│   │   ├── base.py             # BaseParser abstract class
│   │   ├── alertmanager.py     # Alertmanager-specific parser
│   │   └── generic.py          # Generic source parser (standardised JSON schema)
│   ├── executors/
│   │   ├── base.py             # BaseExecutor abstract class
│   │   ├── openclaw_ws.py      # OpenClaw executor — Gateway WebSocket API (Ed25519 auth)
│   │   ├── openclaw.py         # OpenClaw executor — CLI subprocess (legacy, not registered)
│   │   ├── gateway.py          # VectorStep Gateway executor — WebSocket API (token auth)
│   │   ├── human.py            # Human-in-the-loop executor (Telegram/Slack/Teams, per-team routing)
│   │   ├── pipeline.py         # Sub-pipeline executor — calls another pipeline by name
│   │   └── webhook.py          # Webhook output executor (HTTP POST)
│   ├── pipeline/
│   │   ├── loader.py           # Loads pipelines and step library; resolves use: references
│   │   ├── resolver.py         # Matches normalised context to a pipeline
│   │   ├── runner.py           # Executes pipeline steps, manages flow control, emits run log
│   │   └── context.py          # Builds and passes Jinja2 template context between steps
│   ├── models/
│   │   ├── context.py          # NormalisedContext Pydantic model
│   │   ├── pipeline.py         # PipelineConfig, StepConfig, LibraryStepConfig Pydantic models
│   │   └── llm.py              # LLMOutput Pydantic model (step output contract)
│   ├── db/
│   │   ├── database.py         # SQLAlchemy engine, session management
│   │   └── models.py           # PipelineRun, PipelineStep ORM models
│   └── notifications/
│       ├── telegram.py         # Telegram notification handler
│       ├── telegram_poller.py  # Long-poll loop for HITL Telegram button callbacks
│       ├── slack_poller.py     # Slack Socket Mode listener for HITL Slack button callbacks
│       └── webhook.py          # Webhook notification handler
├── templates/                  # Jinja2 HTML templates for the UI
├── logs/                       # Rotating log files (auto-created, gitignored)
│   ├── service.log             # Application logs (10 MB × 5 files)
│   └── access.log              # HTTP access logs, separated from service logs
├── tests/
│   └── fixtures/               # Test webhook payloads (alertmanager, generic, etc.)
├── Dockerfile
├── config.yaml                 # Service-level config — gitignored, copy from samples/config.yaml.example
└── requirements.txt
```
