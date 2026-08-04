---
title: Gateway overview
description: The P-Ork Gateway — agents, LLM providers, MCP tools, and the WebSocket protocol.
sidebar:
  order: 1
---

:::caution[Content migration in progress]
This section is being migrated from the P-Ork-Gateway README. Until then, that
README is the authoritative source.
:::

The Gateway sits between P-Ork and your LLM providers. P-Ork sends an agent
request over WebSocket; the Gateway runs the full agentic loop — LLM calls, MCP
tool execution, multi-turn conversation — and returns one clean result.
Providers: Anthropic, OpenRouter, Google Gemini, Azure OpenAI, Ollama
(local + cloud), and any OpenAI-compatible endpoint. Agents are defined by an
`agent.yaml` + `soul.md` pair, hot-reloaded on SIGHUP, and content-hashed into
an `agent_version` that P-Ork's calibration keys on.
