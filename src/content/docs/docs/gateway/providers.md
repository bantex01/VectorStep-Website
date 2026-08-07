---
title: Providers
description: How model strings route to a provider, and the Azure/OpenAI OpenAI-compat specifics.
sidebar:
  order: 3
---

For the `providers:` config block itself — the fields each provider accepts,
defaults, and endpoints — see [Configuration](/docs/gateway/configuration/#providers).
This page covers how a model string is routed to a provider, and the
specifics of running against Azure OpenAI and OpenAI.

## Model Routing

The prefix in a model string determines which provider handles the call:

| Model string | Provider | Notes |
|---|---|---|
| `anthropic/claude-sonnet-4-6` | Anthropic | Native SDK, extended thinking supported |
| `openrouter/deepseek/deepseek-chat` | OpenRouter | OpenAI-compat, thinking not supported |
| `ollama-local/qwen3:8b` | Local Ollama | OpenAI-compat via `/v1/chat/completions` |
| `ollama-cloud/gemma3:27b` | Ollama Cloud | Native Ollama `/api/chat` |
| `google/gemini-2.0-flash` | Google Gemini | OpenAI-compat |
| `azure/gpt-4o` | Azure OpenAI | OpenAI-compat; `gpt-4o` is the deployment name |
| `openai/gpt-5` | OpenAI | Native OpenAI API, OpenAI-compat |
| `yolo/some-model` | Yolo (custom endpoint) | OpenAI-compat, `base_url` from `providers.yolo` |
| `claude-sonnet-4-6` | Anthropic | Bare name (no prefix) defaults to Anthropic |

## Azure OpenAI

For Azure, the model string suffix is the **deployment name** you set up in
Azure AI Foundry (not the underlying model family name). If you deployed
GPT-4o and named the deployment `gpt-4o`, the model string is `azure/gpt-4o`.
Different deployments of the same underlying model can have different names.

```yaml
# agent.yaml
name: my-azure-agent
model: azure/gpt-4o           # deployment name from Azure AI Foundry
max_tokens: 4096
model_fallbacks:
  - azure/gpt-4o-mini         # cheaper fallback deployment
  - anthropic/claude-haiku-4-5-20251001  # cross-provider fallback
```

Azure's API is OpenAI-compatible. The differences handled internally are the
endpoint URL format, the `api-key` request header (instead of
`Authorization: Bearer`), and the `max_completion_tokens` parameter (Azure's
chat completions API, like OpenAI's, rejects `max_tokens` for reasoning-family
deployments — the provider sends `max_completion_tokens` on the wire
regardless of deployment, translated transparently from the agent's
`max_tokens` field). Extended thinking is not available on Azure OpenAI.

The key name in `providers:` config must match the prefix in the model string
exactly.

## OpenAI

`openai/` reaches OpenAI's own API directly — as opposed to routing through
`yolo/` with a custom `base_url`, or through `azure/`. The model string
suffix is OpenAI's own model name (`openai/gpt-5`, `openai/gpt-4o`), not a
deployment name.

```yaml
# agent.yaml
name: my-openai-agent
model: openai/gpt-5
max_tokens: 4096
model_fallbacks:
  - openai/gpt-4o-mini                    # cheaper fallback, same provider
  - anthropic/claude-haiku-4-5-20251001   # cross-provider fallback
```

Defaults to `base_url: https://api.openai.com/v1`; override it in
`providers.openai.base_url` to point at a proxy or OpenAI-compatible
endpoint. Auth is `Authorization: Bearer`. Like Azure, the OpenAI provider
sends `max_completion_tokens` on the wire unconditionally (translated from
the agent's `max_tokens` field) since reasoning-family models reject the
classic `max_tokens` parameter outright. Extended thinking is not available
on OpenAI — that remains an Anthropic-only feature.

:::caution[Reasoning-family models and token budgets]
Reasoning-family models/deployments (gpt-5, o1, o3) — on both `azure/` and
`openai/` — spend part of their `max_tokens` budget on hidden internal
reasoning before producing any visible output. A budget that's fine for
`gpt-4o` (e.g. `max_tokens: 200`) can come back with `stop_reason: length`
and zero visible text on `gpt-5` because reasoning consumed the whole
budget. Set `max_tokens` generously (2000+) for reasoning-family
models/deployments to leave headroom for actual output.
:::
