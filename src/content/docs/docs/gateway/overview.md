---
title: Gateway overview
description: The VectorStep Gateway — agents, LLM providers, MCP tools, and the WebSocket protocol.
sidebar:
  order: 1
---

The VectorStep Gateway is a lightweight Python/FastAPI WebSocket gateway that runs
AI agents with MCP tool access. It acts as an executor backend for VectorStep
pipelines, providing an alternative to OpenClaw with support for multiple LLM
providers and configurable MCP tool servers.

The gateway sits between VectorStep and your LLM providers. VectorStep sends an agent
request over WebSocket; the gateway runs the full agentic loop (LLM calls, MCP
tool execution, multi-turn conversation) and returns the final result. VectorStep
never sees intermediate tool calls or thinking content — it gets one clean
response.

This section is the Gateway's own reference: configuration, agent authoring,
the WebSocket and REST protocols, and day-two operations. If you just want the
fastest path to a first pipeline running, see the site's
[quick start](/docs/getting-started/quick-start/) instead — this page is the
Gateway's standalone introduction.

## Quick Start

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

:::note
Both `config.yaml` and `agents/` are gitignored — they contain personal
credentials and environment-specific agent definitions. Use
`samples/config.yaml.example` as your starting point.
:::

## Directory Structure

```
VectorStep-Gateway/
├── samples/
│   └── config.yaml.example           # Config template with all options documented
├── agents/                           # Your agent definitions (gitignored)
├── config.yaml                       # Your config (gitignored)
├── gateway/
│   ├── main.py                       # FastAPI app, WebSocket endpoint, REST API
│   ├── tracing.py                    # OpenTelemetry setup and W3C trace context extraction
│   ├── auth/
│   ├── agents/
│   ├── session/
│   ├── mcp/
│   ├── llm/
│   ├── runner/
│   └── models/
└── requirements.txt
```

## Where next

- **[Configuration](/docs/gateway/configuration/)** — every `config.yaml` field.
- **[Providers](/docs/gateway/providers/)** — model routing and Azure OpenAI specifics.
- **[Creating agents](/docs/gateway/agents/)** — `agent.yaml`, `soul.md`, hot reload.
- **[WebSocket protocol](/docs/gateway/protocol/)** — the `agent` request/response contract.
- **[REST API](/docs/gateway/api/)** — health, agent management, MCP introspection.
- **[Operations](/docs/gateway/operations/)** — metrics, environment variables, performance notes.
- **[VectorStep integration](/docs/gateway/integration/)** — wiring the gateway into a pipeline.
