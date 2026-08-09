---
title: VectorStep integration
description: Wiring the Gateway into VectorStep's executors config and pipeline YAML, how it differs from the OpenClaw executor, and the Gateway MCP for agent authoring.
sidebar:
  order: 8
---

This page is the authoritative reference for how the Gateway plugs into
VectorStep: the executor config on VectorStep's side, using it from a pipeline step,
and how it compares to the OpenClaw executor.

## 1. Configure VectorStep

In VectorStep's `config.yaml`:

```yaml
executors:
  gateway:
    url: ws://localhost:18780/rpc        # gateway WebSocket endpoint
    token: ${VECTORSTEP_GATEWAY_TOKEN}        # operator token from device-auth.json
    rest_url: http://localhost:18780    # used by the VectorStep Agents UI
```

## 2. Use in pipeline YAML

```yaml
steps:
  - name: triage
    executor: gateway
    executor_config:
      agent: sre-triage                      # must match an agent in your agents/ directory
      model: anthropic/claude-sonnet-4-6     # optional model override
      thinking_level: low                    # optional — Anthropic models only
    confidence_threshold: 0.70
    on_low_confidence: escalate
    timeout_seconds: 300
    prompt_template: |
      Alert: {{summary}}
      Service: {{labels.service}}

      Investigate and return JSON...
```

Steps within the same VectorStep pipeline can freely mix `executor: openclaw` and
`executor: gateway`.

## Differences from the OpenClaw executor

| | OpenClaw executor | Gateway executor |
|---|---|---|
| Auth | Ed25519 device signature | Bearer token |
| Session isolation | Server-side (no file clearing) | Server-side |
| Model routing | OpenClaw agent config | Gateway `providers:` config |
| MCP tools | OpenClaw MCP servers | Gateway `mcp_servers:` config |
| Thinking parameter | `thinking` | `thinkingLevel` |
| OTel trace propagation | Not supported | Supported — joins VectorStep's trace |

## Gateway MCP (agent authoring)

`VectorStep-Gateway-MCP` is a separate, standalone MCP server (own repo, own
process) that exposes this gateway's agent-management and introspection
surface to an MCP client (Claude Code/Desktop), so an agent's
`agent.yaml`/`soul.md` can be authored conversationally instead of by
hand-editing files on the host running the gateway. It talks to this gateway
only over the [REST endpoints](/docs/gateway/api/) — no shared code — and
holds the operator token, never returning it or any other `config.yaml`
secret from any tool.

For the full tool inventory, install steps, and client configuration, see
[MCP servers](/docs/integrations/mcp/).
