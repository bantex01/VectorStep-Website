---
title: Installation & development setup
description: The full setup reference for VectorStep and the VectorStep Gateway — dependencies, tests, and the SQLite-vs-Postgres choice.
sidebar:
  order: 2
---

[Quick start](/docs/getting-started/quick-start/) gets a pair of services
running fast. This page is the detailed reference to sit alongside it: the
full Gateway quick start, the service's own development setup, how to run the
test suite, and the one database decision you'll actually need to make.

## Gateway: full setup

```bash
# 1. Install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Copy and edit the config template
cp samples/config.yaml.example config.yaml
# Edit config.yaml — set your LLM provider keys and MCP servers

# 3. Create your agents directory
mkdir -p agents/my-agent
# Add agent.yaml and soul.md — see Creating Agents below

# 4. Set environment variables for any ${VAR_NAME} placeholders in config.yaml
export ANTHROPIC_API_KEY=sk-ant-...

# 5. Start the gateway (host/port come from config.yaml's `server:` section)
python -m gateway.main

# 6. Find your operator token (auto-generated on first run)
cat ~/.vectorstep-gateway/identity/device-auth.json
# Copy the 'operator' token — you'll need it for VectorStep's config
```

Both `config.yaml` and `agents/` are gitignored — they contain personal
credentials and environment-specific agent definitions. Use
`samples/config.yaml.example` as your starting point.

For agent authoring (`agent.yaml`, `soul.md`, hot reload), see
[Creating agents](/docs/gateway/agents/).

## VectorStep service: development setup

```bash
cd service
python -m venv .venv
source .venv/bin/activate
pip install -r ../requirements.txt   # requirements.txt lives at the repo root

# Run service
uvicorn src.main:app --reload --port 8000

# Test webhook (alertmanager)
curl -X POST "http://localhost:8000/webhook?source=alertmanager" \
  -H "Content-Type: application/json" \
  -d @tests/fixtures/alertmanager_critical.json

# Test webhook (generic source)
curl -X POST "http://localhost:8000/webhook?source=generic" \
  -H "Content-Type: application/json" \
  -d @tests/fixtures/generic_new_order.json
```

Running the test suite, including the Postgres test lane, is covered on
[Testing](/docs/design/testing/).

## SQLite vs. Postgres

The ORM layer (SQLAlchemy async) is dialect-agnostic — switching backends is
a `database.url` change only, no code changes. Two supported backends:

| Backend | URL | When to use |
|---|---|---|
| SQLite (`aiosqlite`) | `sqlite+aiosqlite:///./runs.db` | Local dev, zero infrastructure, single process |
| PostgreSQL (`asyncpg`) | `postgresql+asyncpg://user:pass@host:5432/dbname` | Production — concurrent writers, real backup/replication story |

:::note
For the full database setup, migration mechanism, and dedup-race hardening
details, see [Deployment](/docs/operations/deployment/).
:::
