---
title: Run detail
description: The run detail page — run log, live tail, agent trace, and accuracy feedback.
sidebar:
  order: 2
---

The run detail page (`/ui/runs/{id}`) is where you inspect a single run in full: every step's prompt, output, confidence score, verifier result, and the Trust panel explaining how each gating decision was made. This page covers its four main sections — the run log, live tail, agent trace, and accuracy feedback.

## Run log

Each completed run stores a structured event timeline in `pipeline_runs.logs`. The run detail page shows this as a collapsible log section with timestamped, colour-coded entries (info / warn / error) covering every step start, confidence score, verifier result, skip, escalation, notification, and final status.

## Live tail

While a run is in progress the run detail page shows a **Live tail** panel. It connects via Server-Sent Events (`GET /ui/runs/{id}/stream`) and streams two categories of events in real-time:

**Pipeline log events** — fire for all executor types:
`step_started`, `step_completed`, `step_failed`, `step_skipped`, `step_escalated`, `step_aborted`, `verifier_ran`, `parallel_group_started`, `parallel_group_completed`, `notification_sent`, `run_started`, `run_finished`.

**Agent trace events** — `executor: gateway` steps only. Each LLM call, thinking block, text response, tool call (with arguments), and tool result streams into the live tail as it happens — not as a batch when the step finishes. These are rendered with compact colour-coded formatting: violet for thinking, cyan for tool calls, green/red for tool results. Content is truncated at 200 chars in the live tail; the full content is in the step detail panel's Agent trace section.

Late-connecting clients receive a full history replay of everything that happened before they connected, then transition into the live stream — no events are missed.

When the run finishes the page reloads automatically to show the final state. A 5-second polling fallback (`GET /runs/{id}`) reloads the page if the SSE connection was lost.

## Agent trace

Each step's expanded detail panel includes a collapsible **Agent trace** section showing the complete internal execution trace: LLM call markers, extended thinking blocks, response text, every tool call with arguments, and every tool result. This is available for **`executor: gateway` steps only** — the gateway streams each event back to VectorStep as it fires, which stores the full trace in `pipeline_steps.agent_trace`.

The trace toggle label shows a count of LLM calls and tool calls at a glance (e.g. `3 LLM calls, 12 tool calls`). Tool result content is truncated at 3,000 chars in the stored trace; full content is always available in the gateway's own logs at `DEBUG` level.

The same events that populate this panel also appear in the **live tail** during the step's execution — the detail panel is the persistent post-run record; the live tail is the real-time view.

For `openclaw` steps, `agent_trace` is NULL — OpenClaw does not expose intermediate events to VectorStep.

## Cost

Alongside the token badge, each step and the run total show a cost figure
when [pricing](/docs/operations/cost-accounting/) is configured — 2 decimal
places normally, 4 when a step's cost would otherwise round to a
misleadingly-free $0.00. An "unpriced steps: N" note appears whenever some
steps couldn't be priced, so a partial total is never shown as if it were
complete.

If `pricing.live_pricing` is enabled, an otherwise-unpriced step's cost badge
instead shows a best-effort approximation from OpenRouter's public catalog —
**amber** for a cross-provider guess (with a hover explaining it's an
estimate), **green** if the step's provider genuinely is `openrouter` (a live
price for the exact API that was called, just not manually entered). See
[Cost accounting](/docs/operations/cost-accounting/) for the full model.

## Accuracy feedback

After a run completes, any user can mark it with a human judgement of whether the pipeline's outcome was correct. The feedback widget appears at the bottom of every finished run's detail page (hidden for `running` and `interrupted` runs).

**Outcomes:**

| Outcome | When to use |
|---|---|
| `Correct` | The pipeline did what it was supposed to do |
| `Partial` | The pipeline did useful work but didn't fully achieve the goal |
| `Incorrect` | The outcome was wrong or misleading |

An optional notes field lets you record why — useful context when reviewing patterns later. Submitting again overwrites the previous outcome (upsert).

**Where accuracy data surfaces:**

- **Run detail** — the feedback widget; shows current outcome if already marked.
- **Pipeline detail** — a colour-coded correct/partial/incorrect bar with counts, and a "View breakdown →" link.
- **Insights — Overview** — an "Accuracy" stat card showing the % correct of all marked runs in the selected time range.
- **Pipeline accuracy page** (`/ui/pipelines/{name}/feedback`) — the full breakdown:
  - Summary cards (total marked, correct, partial, incorrect with percentages)
  - Overall accuracy distribution bar
  - **Accuracy by configuration table** — runs are grouped by a fingerprint of the exact (step sequence × agents × models) combination. When you change a model, add a step, or swap an agent, the new runs fall into a new group automatically, so you can directly compare accuracy before and after any pipeline change without manually tagging versions.
  - Chronological table of every marked run with its outcome, run status, config fingerprint, and notes.

### Per-step feedback

In addition to run-level feedback, you can mark an individual step *execution* correct/partial/incorrect. The control appears inside each finished step's expanded detail panel (same collapsible body as the parsed output and agent trace), so marking is optional and sparse — mark only the step(s) you have an opinion on. Fan-out branches (`triage/0`, `triage/1`, ...) are marked independently, since each is its own step execution.

- **Steps Insights** (`/ui/insights/steps`) — the pipeline/agent/model breakdown table has an **Accuracy** column, and the per-step drilldown has an **Accuracy** mini-card, both computed as `correct / total_marked` over the selected time range, production-scoped.
- `vectorstep_step_feedback_total` exposes the same counts for Grafana/alerting.

Per-step feedback is currently pure data collection — it does not affect gating or flow control. It's a building block for future work on calibrating trust scores against real outcomes.
