---
title: Insights
description: The eight Insights pages — overview, pipelines, steps, agents, models, providers, MCP, teams — and the Agent Library.
sidebar:
  order: 3
---

The Insights section (`/ui/insights/*`) is a set of eight pages giving cross-pipeline rollups over runs, steps, agents, models, providers, MCP tool usage, and teams. Every Insights page is scoped to `stage: production` runs only — testing-stage runs are excluded from all totals and drilldowns, consistent with every other rollup surface in the UI.

## Insights — Overview

`/ui/insights` shows run/failure/token/accuracy totals, runs by team, and MCP tool-use counts, over a selectable time range (24h/7d/30d/all-time). This is the landing page for the section — a single screen of the numbers you'd otherwise have to piece together from the Runs and Pipelines pages.

When `pricing.live_pricing.enabled` is set (see [Cost accounting](/docs/operations/cost-accounting/)), this page also shows a **Live reference pricing** panel — OpenRouter's current list price for every model in use that could be fuzzy-matched, clearly disclaimed as approximate and not necessarily what you actually pay.

## Insights — Pipelines

`/ui/insights/pipelines` shows per-pipeline run/failure/duration/token/cost totals and a top-pipelines table. Drilling into a pipeline gives a status/accuracy breakdown, a timeseries, recent runs, and a step/agent/model breakdown table for that pipeline specifically.

## Insights — Steps

`/ui/insights/steps` shows per-step run/failure/duration/token totals and a top-steps table. The per-step drilldown gives a status breakdown, a timeseries, recent executions, and a pipeline/agent/model breakdown table — this is also where calibration bins for every agent/model/prompt-version combination live (see [How confidence and calibration work](/docs/concepts/confidence/)).

## Insights — Agents

`/ui/insights/agents` shows per-agent step/success-rate/duration/token totals and a top-agents table. The per-agent drilldown gives a status breakdown, a timeseries, recent executions, and a pipeline/step/model breakdown table.

## Insights — Models

`/ui/insights/models` shows per-model (provider-qualified — see [Agent Library — model display](#model-display-and-the-provider-column)) success-rate/duration/token/cost totals and a top-models table, with a per-model drilldown (status breakdown, timeseries, recent calls, and a pipeline/step/agent breakdown table). This page is **production only** and **`executor: gateway` steps only** — it has no data for OpenClaw-executed steps, since only the gateway executor records a model per step.

## Insights — Providers

`/ui/insights/providers` groups calls/success-rate/duration/token/cost totals by LLM provider (`anthropic`, `openrouter`, `azure`, etc.), with a top-providers table and a per-provider drilldown of the same shape as the other Insights pages.

This page folds in what used to be the standalone `/ui/providers` page — old links redirect here. It also has one piece of special-casing not found on any other Insights page: **it falls back to a best-effort provider guess parsed from the model string for pre-migration rows that have no `provider` value recorded**, since the entire point of this page is bucketing by provider, and a page that couldn't bucket older rows at all would undercount them. Every other Insights page instead leaves an unrecorded provider as a bare model name rather than guessing — this page is the deliberate exception, because guessing here is strictly better than an artificial gap in the provider totals.

Like Models, this page is production only and `executor: gateway` steps only.

## Insights — MCP

`/ui/insights/mcp` shows tool call usage extracted from the agent trace on `executor: gateway` steps — calls/errors by tool and by server, and a per-tool drilldown showing which pipelines/steps/agents call it, over a selectable time range. OpenClaw steps don't expose intermediate events, so they contribute nothing here. This page is analytics on tool *usage*; for the live tool/server registry (schemas, running/pid/restart_count), see the [MCP Tools page](/docs/ui/overview/) (`/ui/mcp`).

## Insights — Teams

`/ui/insights/teams` shows per-team run/success-rate/duration/token/cost totals and a top-teams table. The per-team drilldown gives a complete picture of what a team uses and where — pipelines used, and a pipeline/step/agent/model breakdown table — plus its token/cost spend, for informed cost decisions. A NULL team is bucketed as "Unattributed" rather than dropped.

If `pricing.team_budgets` is configured, this page also shows a **month-to-date budgets** section — a spend-vs-budget bar per team, advisory only (see [Cost accounting](/docs/operations/cost-accounting/)).

## Agent Library

The `/ui/agents` page provides a unified library of agents across all configured executor backends. Agents are fetched live from each backend and merged into a single list with executor badges.

Agents are uniquely identified by `executor:name` — e.g. `openclaw:sre-investigation` and `gateway:sre-investigation` are treated as distinct agents. This prefix is stored in `pipeline_steps.agent` so run history, success rates, and model usage are attributed correctly per backend.

| Executor | Agent list | Agent files |
|---|---|---|
| `openclaw` | OpenClaw Gateway WS — `agents.list` RPC | `agents.files.get` RPC — `SOUL.md`, `TOOLS.md`, `IDENTITY.md` tabs |
| `gateway` | VectorStep Gateway REST — `GET /agents` | `GET /agents/{name}/soul` (Soul tab) · `GET /agents/{name}/agent` (Config tab — raw `agent.yaml`) |

Both backends are queried concurrently. If one is unreachable, the other's agents still show with a warning banner. If both fail, stub entries from DB run history are surfaced.

The **Config** tab on a gateway agent detail page shows the raw `agent.yaml` — model, `max_tokens`, and the list of MCP tool names the agent has access to.

**Overview tab** — a per-model breakdown table (runs, succeeded, failed, success rate, avg duration, avg tokens in/out, last run), two "usage over time" line charts (runs and tokens, both split by model), and a **recent activity** list of the last 15 steps this agent ran across any pipeline — each row links to its pipeline and its run detail page.

**Steps tab** — which pipeline steps this agent executes, broken down by pipeline and model (runs, success rate, avg tokens, last run). The same step name can be wired to a different model in different pipelines, so pipeline is a first-class column here rather than folded away.

All of the above is scoped to `stage=production` runs, same as every other rollup surface.

### Model display and the `provider` column

Wherever a model name is shown alongside run history (this page, `/ui/steps`, and the Insights pages), it's prefixed with its provider when the DB actually recorded one — e.g. `anthropic/claude-sonnet-5`, `openrouter/deepseek/deepseek-v4-pro`. `pipeline_steps.provider` is only populated for `executor: gateway` steps (from the Gateway's `agentMeta.provider`); other executors, or steps run on an older Gateway build that predates this field, leave it NULL and the bare model name is shown as-is — the UI does not guess a provider it has no evidence for, since a wrong guess is worse than no answer. (The one deliberate exception to that policy is the Insights — Providers page above.)
