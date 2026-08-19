---
title: Linux
description: From-source development setup for both services, plus a systemd path for a plain VM with no container runtime.
sidebar:
  order: 4
---

## Prerequisites

**Python 3.11+** and **`git`** — the one-liners below clone each repo and
need both present on `PATH`; they'll fail with a clear message naming
whichever is missing.

## Development setup

### Gateway

```bash
curl -sSL https://raw.githubusercontent.com/bantex01/VectorStep-Gateway/main/install-gateway.sh | bash
```

Then edit `~/.vectorstep-gateway/config.yaml` with your LLM provider keys,
add a first agent under `agents/` (see [Creating agents](/docs/gateway/agents/)),
export your provider key, and start it:

```bash
cd ~/.vectorstep-gateway
export ANTHROPIC_API_KEY=sk-ant-...
source .venv/bin/activate && python -m gateway.main

# Find your operator token (auto-generated on first run)
cat ~/.vectorstep-gateway/identity/device-auth.json
# Copy the 'operator' token — you'll need it for VectorStep's config
```

<details>
<summary>What the one-liner does, or set it up by hand</summary>

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

</details>

### VectorStep service

```bash
curl -sSL https://raw.githubusercontent.com/bantex01/VectorStep/main/install-service.sh | bash
```

Then start it and try a test webhook:

```bash
cd ~/.vectorstep/service
source .venv/bin/activate && uvicorn src.main:app --reload --port 8000

# Test webhook (alertmanager)
curl -X POST "http://localhost:8000/webhook?source=alertmanager" \
  -H "Content-Type: application/json" \
  -d @tests/fixtures/alertmanager_critical.json

# Test webhook (generic source)
curl -X POST "http://localhost:8000/webhook?source=generic" \
  -H "Content-Type: application/json" \
  -d @tests/fixtures/generic_new_order.json
```

<details>
<summary>What the one-liner does, or set it up by hand</summary>

```bash
cd service
python -m venv .venv
source .venv/bin/activate
pip install -r ../requirements.txt   # requirements.txt lives at the repo root

# Run service
uvicorn src.main:app --reload --port 8000
```

</details>

Running the test suite, including the Postgres test lane, is covered on
[Testing](/docs/design/testing/).

### SQLite vs. Postgres

The ORM layer (SQLAlchemy async) is dialect-agnostic — switching backends is
a `database.url` change only, no code changes. SQLite (zero infrastructure)
is right for this local setup; Postgres is for production.

:::note
For the full database setup, migration mechanism, and dedup-race hardening
details, see [Deployment](/docs/operations/deployment/#database).
:::

## Production (systemd)

For a plain VM or instance without a container runtime, both repos ship
systemd units and a step-by-step install guide under `deploy/systemd/`
(`install.md`, `*.service`, `env.example`) — code in
`/opt/vectorstep/<service>`, config in `/etc/vectorstep/<service>/`, state in
`/var/lib/vectorstep/<service>/`, logs in `/var/log/vectorstep/<service>/`.
Both units support `systemctl reload` (pipelines/steps for VectorStep,
agents for the Gateway) without dropping the process; a code, dependency, or
database change needs `systemctl restart`.

## Where next

- **[Deployment](/docs/operations/deployment/)** — the full `config.yaml`
  reference and database/migration mechanics.
- **[Docker](/docs/installation/docker/)** / **[Kubernetes](/docs/installation/kubernetes/)**
  — containerized alternatives to both paths above.
