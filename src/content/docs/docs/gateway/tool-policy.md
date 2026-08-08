---
title: Tool policy
description: Operator-owned allow/deny rules evaluated on every tool call, independent of any agent's own tools allowlist.
sidebar:
  order: 4.5
---

Agent authors control what an agent *can* call via its `tools:` allowlist in
`agent.yaml` — but that's authoring-time surface, writable via the REST API or
the [Gateway MCP](/docs/gateway/integration/#3-gateway-mcp-agent-authoring).
`tool_policy` is a separate, operator-owned backstop in `config.yaml`: a rule
set that every tool call passes through **regardless of which agent is
calling or how its `tools:` list is configured**. Use it for deployment-wide
constraints an agent author shouldn't be able to loosen — *"no agent may ever
call `jira_delete_issue`"*, *"any `execute_promql` call containing
`delete_series` is blocked"*.

It's entirely optional. Omit `tool_policy` from `config.yaml` and every tool
call executes exactly as before this feature existed — a zero-cost
passthrough, not an empty policy silently evaluating rules.

## Schema

```yaml
tool_policy:
  default: allow            # allow | deny — applies when no rule matches
  rules:
    - deny:  {server: atlassian, tool: jira_delete_issue}
      reason: "Destructive Jira operations are operator-only"
    - deny:  {tool: "execute_*", input_regex: "(?i)delete|drop"}
      reason: "Mutating queries blocked by policy"
    - allow: {server: grafana}          # useful under default: deny
    - deny:  {agent: experimental-*}
      reason: "Experimental agents run toolless in this deployment"
```

| Field | Description |
|---|---|
| `default` | `allow` or `deny` — the decision when no rule matches. Defaults to `allow`. |
| `rules` | Ordered list. **First match wins.** |
| `rules[].allow` / `rules[].deny` | Exactly one per rule — the action to take when this rule's match block matches. |
| `rules[].reason` | **Required** on `deny` (shown to the LLM in the blocked tool result and written to the log). Optional on `allow`. |

Each rule's match block has four optional fields; **all present fields must
match (AND)**:

| Match field | Type | Matches against |
|---|---|---|
| `server` | exact string | The MCP server name (as configured under `mcp_servers:`) |
| `tool` | [`fnmatch`](https://docs.python.org/3/library/fnmatch.html) glob | The **unscoped** tool name — e.g. `jira_search`, not the internal `atlassian__jira_search` namespaced form |
| `agent` | `fnmatch` glob | The calling agent's `name` |
| `input_regex` | `re.search` pattern | The tool's input, JSON-serialised as `json.dumps(input, sort_keys=True)` for deterministic matching |

A misspelled match key (`sever:` instead of `server:`) is a config validation
error at gateway startup, not a silently-inert rule — fail closed on typos.

## How a call is evaluated

Policy is evaluated once per tool call, at the single seam in the agent loop
right before dispatch to the MCP server — after the LLM has requested the
call, before it executes. Parallel tool calls within one LLM turn are
evaluated independently.

Rules are checked in order; the first one whose match block matches decides
the outcome. If no rule matches, `default` applies.

**A denial is a tool result, not a run failure.** The calling LLM receives an
`is_error: true` tool result:

```
Blocked by gateway tool policy: Destructive Jira operations are operator-only
```

The agentic loop continues exactly as it would after any other failing tool
call — the LLM can route around the block or report it in its final answer.
This keeps policy orthogonal to VectorStep's step-level governance (confidence
gates, verifiers, HITL approval): a step whose agent couldn't do the blocked
thing will, correctly, report low confidence or a blocked-action summary, and
those existing gates take over from there. Nothing about the run's terminal
status changes because of a denial.

### `input_regex` and the serialisation cap

`input_regex` runs `re.search` against the tool input serialised with
`json.dumps(input, sort_keys=True)`, capped at 1&nbsp;MB. Beyond the cap, the
rule is treated as non-matching (skipped) and a `WARNING` is logged once per
gateway run — not once per call, to avoid log spam from a single pathological
input being retried. The cap exists to bound regex cost against oversized
inputs; it is **not** a security boundary, and oversized inputs are not
otherwise blocked by it.

## Audit trail

Every denial is recorded three ways:

1. **Trace event** `tool_denied` — `{type, name, server, rule_index, reason}`.
   Streamed like every other trace event (see the
   [WebSocket protocol](/docs/gateway/protocol/#trace-event-types)), so
   VectorStep persists it in `agent_trace` with zero changes on that side. The
   call's input is not re-echoed here — it's already in the `tool_call` event
   that preceded it. No `tool_result` event follows a `tool_denied` event; the
   synthetic error result is what the LLM sees instead.
2. **Log line** — `WARNING`, with agent, tool, rule index, and reason.
3. **Metric** — `vectorstep_gateway_tool_denials_total{mcp_server, tool, agent}`
   (see [Operations](/docs/gateway/operations/#prometheus-metrics)).

Allowed calls aren't separately audited beyond the existing `tool_call` /
`tool_result` trace events — recording every rule hit for an allow would just
be noise.

## Tool visibility under `default: deny`

Under `default: allow` (the default), tool schemas are presented to the LLM
exactly as today — a category of tool being blockable doesn't hide it, since
most calls will still be allowed. Denials happen purely at call time.

Under `default: deny`, a tool that **no** rule could ever allow for a given
agent is filtered out of the schema list handed to the LLM entirely —
presenting a tool that's categorically blocked just burns context and invites
doomed calls the agent will only have to work around. The filter is
conservative: a tool stays visible if *any* `allow` rule's `server`/`tool`/
`agent` fields could match it, even if that same rule also has an
`input_regex` — `input_regex` can't be evaluated without a real call, so it
never hides a tool, only narrows what's allowed once the agent actually calls
it.

## Restart required

`config.yaml` — and therefore `tool_policy` — is loaded once at gateway
startup and is not writable via any API. That's deliberate: it's what makes
this an operator control an agent author can't loosen through the REST API or
Gateway MCP. Changing the policy needs a gateway restart, the same as adding
or removing an `mcp_servers` entry.

Inspect the currently-active policy at runtime (read-only) via:

```
GET /tool-policy
```

Returns the parsed rules with reasons included and regex/glob patterns as
plain strings. There is no write endpoint.

## What's not built yet

The schema reserves a third rule action, `require_approval`, for a future
phase: pausing an in-flight tool call on an approval decision from a human
(surfaced through VectorStep's HITL UI) rather than allowing or denying it
outright. It parses today so a config written now won't need editing later,
but the gateway rejects it at startup with a clear "not yet supported" error
— no pause/resume machinery exists yet.
