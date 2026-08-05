---
title: MCP servers
description: Two standalone MCP servers — VectorStep Service MCP and VectorStep Gateway MCP — that expose pipeline and agent authoring to AI coding assistants.
sidebar:
  order: 3
---

VectorStep ships two separate, standalone [MCP](https://modelcontextprotocol.io)
servers — each its own repository and process — that expose VectorStep/Gateway
functionality to MCP clients such as Claude Code and Claude Desktop, so
pipelines, steps, and agents can be authored conversationally instead of by
hand-editing files:

- **[VectorStep Service MCP](#p-ork-service-mcp)** — pipelines, steps, runs, and
  analytics.
- **[VectorStep Gateway MCP](#p-ork-gateway-mcp)** — agents (`agent.yaml` +
  `soul.md`), MCP tool/provider introspection.

The two have clean, non-overlapping tool sets: agents live in the Gateway MCP,
pipelines/steps live in the Service MCP. Each is a thin HTTP client against
its respective service's REST API — neither imports the other's code, and
each can be developed, versioned, and deployed independently.

## VectorStep Service MCP

An MCP server that exposes VectorStep — a webhook-triggered, YAML-configured AI
pipeline orchestration service — to MCP clients such as Claude Code and Claude
Desktop.

It lets an MCP client:

- create and edit pipelines and step-library definitions, with the same
  validation VectorStep itself uses,
- inspect runs, steps, and their outcomes,
- answer operational and quality questions — "how many times has this
  pipeline failed", "how accurate is it", "which pipeline burns the most
  tokens", "what's its p95 duration" — and
- trigger runs and submit human feedback.

Agents (executors, backends, providers) are **not** authored here — that's the
job of the companion VectorStep Gateway MCP, below. This server may *read* agents
(to help author pipelines that reference them) but never creates or edits
them.

### Interpreting results — the `explain` tool

Several fields VectorStep returns are easy to misread without context — most
notably, a pipeline's `success_rate` (operational) and `accuracy` (human-
judged) are **independent**: a pipeline that always escalates to a human
rather than completing on its own can have a 0% success_rate while being
100% judged-accurate, if a human confirms escalating was the right call
every time. That's not a contradiction, and a low success_rate alone isn't
evidence of a broken pipeline.

Rather than relying on the model to infer this from field names, this
server ships a small `explain(topic)` / `list_doc_topics()` tool pair backed
by curated markdown docs (`src/vectorstep_service_mcp/docs/`) that the model can
call mid-task before drawing a conclusion — analogous to how `validate_pipeline`
lets it check its work before writing. Current topics:

- `statuses-and-accuracy` — the independence above, plus the full run/step status reference.
- `confidence-and-trust-vector` — what `primary_confidence`/`verifier_confidence`/`grounding_score`/`deterministic_passed`/`trust_report` each measure and how they combine.
- `stages-and-scoping` — why a pipeline with real history can show `runs_total: 0` (testing-stage runs and the 7-day default window are excluded unless asked for).
- `prompt-versions` — why a calibration bucket resets when a step's prompt or a Gateway agent's config changes, why a small bucket isn't a bad one, and why `agent_version` changes originate in the Gateway repo, invisible in VectorStep's own YAML.
- `promotion-readiness` — the four independent readiness tiers, the verdict vocabulary, the per-band (not total) `n_min` trap, and `require_current_config`/`require_own_evidence`.

The relevant analytics/`get_run` tool docstrings point at these explicitly.
Add a new topic by dropping a `.md` file in `docs/` and registering it in
`tools/docs.py`'s `_TOPICS` dict.

Same principle applies to calibration: don't reconstruct a step's
calibration picture by sampling `get_run` across many runs one bin at a
time — call `get_step_calibration(name)` directly for the full per-(agent,
model, provider) breakdown in one call.

### Relationship to VectorStep

This is a **separate, standalone repository and process**. It is not a
package inside the main VectorStep repo and has **no import-level dependency** on
it. The two are coupled *only* over HTTP: this server is a thin `httpx`
client against VectorStep's JSON API.

```
Claude Code/Desktop  <--stdio (MCP)-->  vectorstep-service-mcp  <--HTTP-->  VectorStep service
```

Because the coupling is HTTP-only, this repo can be developed, versioned, and
deployed independently of VectorStep.

### Tool inventory

Read + analytics tools: `list_pipelines`, `get_pipeline`, `list_steps`,
`get_step`, `list_agents`, `list_runs`, `get_run`, `get_pipeline_stats`,
`list_pipeline_stats`, `get_step_stats`, `get_step_model_breakdown`,
`get_step_calibration`, `get_step_versions`, `get_agent_versions`,
`get_promotion_readiness`, `preview_promotion_readiness`, `get_run_feedback`
— plus the `explain`/`list_doc_topics` pair above.
`get_promotion_readiness`/`preview_promotion_readiness` are strictly
advisory — a read-only readout of a pipeline's owner-defined promotion bar,
plus a candidate-config preview that writes nothing. See
`explain("promotion-readiness")`.

Write/validate/action tools: `create_pipeline`, `update_pipeline`,
`create_step`, `update_step`, `validate_pipeline`, `validate_step`, `reload`,
`run_pipeline`, `submit_run_feedback`, `delete_pipeline`, `delete_step`.
Writes use atomic validated-rollback: schema/reference validation happens
before anything touches disk. Destructive tools (`delete_pipeline`/
`delete_step`) refuse to call VectorStep at all without an explicit `confirm=True`.

### Configuration

Set via environment variables:

| Variable | Default | Purpose |
|---|---|---|
| `VECTORSTEP_BASE_URL` | `http://127.0.0.1:8000` | Base URL of the VectorStep service this server talks to. |
| `VECTORSTEP_WEBHOOK_TOKEN` | *(unset)* | Bearer token sent on every VectorStep call. Only required where VectorStep itself requires auth (e.g. `POST /webhook`); most endpoints this server uses (reads, `/pipelines/{name}/run`, write endpoints) are unauthenticated today, per VectorStep's current auth posture — see [team attribution](/docs/operations/teams/). If VectorStep has `auth.teams` configured, the token held here determines which team manual runs and writes triggered by this server are attributed to. |

### Installing

This isn't published to PyPI — install it from the checked-out repo into its
own virtualenv:

```bash
cd VectorStep-Service-MCP
python3 -m venv .venv
.venv/bin/pip install -e .
```

That gives you a `python -m vectorstep_service_mcp` entry point at
`.venv/bin/python`. Note the **absolute path** to that interpreter — you'll
need it below, since MCP clients spawn the server directly (no shell/profile
sourced, so a bare `python` on your `$PATH` won't reliably resolve).

Also make sure a VectorStep instance is actually running for it to talk to
(`uvicorn src.main:app --reload --port 8000` in the `VectorStep/service`
directory) — the MCP is just a client; it has nothing to do without a VectorStep
to call.

### Configuring your MCP client

**Claude Code**, from the repo root (or anywhere, using absolute paths):

```bash
claude mcp add vectorstep-service \
  --env VECTORSTEP_BASE_URL=http://127.0.0.1:8000 \
  --env VECTORSTEP_WEBHOOK_TOKEN=<your-token-if-auth.teams-is-configured> \
  -- /absolute/path/to/VectorStep-Service-MCP/.venv/bin/python -m vectorstep_service_mcp
```

Or add it by hand to `.mcp.json` (project-scoped) or `~/.claude.json`
(user-scoped, under `mcpServers`):

```json
{
  "mcpServers": {
    "vectorstep-service": {
      "command": "/absolute/path/to/VectorStep-Service-MCP/.venv/bin/python",
      "args": ["-m", "vectorstep_service_mcp"],
      "env": {
        "VECTORSTEP_BASE_URL": "http://127.0.0.1:8000",
        "VECTORSTEP_WEBHOOK_TOKEN": ""
      }
    }
  }
}
```

**Claude Desktop** — same `mcpServers` shape, in
`~/Library/Application Support/Claude/claude_desktop_config.json` (macOS).

`VECTORSTEP_WEBHOOK_TOKEN` can be omitted (or left empty) entirely if VectorStep's
`auth.teams` isn't configured — see the Configuration table above.

:::note[stdio isn't a REPL]
Don't run `python -m vectorstep_service_mcp` directly in a terminal expecting a
REPL. stdio MCP servers aren't interactive — they read framed JSON-RPC
messages from stdin, written by an MCP *client* (Claude Code, Claude
Desktop, or a debug tool), not typed by a human. If you run it manually,
it'll just sit there; pressing Enter sends an empty line, which isn't
valid JSON-RPC and logs a `json_invalid` error (harmless — it doesn't
crash the server, it just means you sent it garbage).

To actually exercise it:
- **Through Claude Code**, once registered (above) — just ask it to use a
  `vectorstep-service` tool in a normal session.
- **Standalone, for debugging** — use the
  [MCP Inspector](https://github.com/modelcontextprotocol/inspector):
  ```bash
  npx @modelcontextprotocol/inspector /absolute/path/to/.venv/bin/python -m vectorstep_service_mcp
  ```
  which opens a web UI to call tools one at a time and see raw request/response.
:::

### Dependencies & transport

- **MCP SDK**: pinned to `mcp==1.28.1` (the latest release at the time this
  project was created — see `pyproject.toml`/`requirements.txt`). Bump
  deliberately and re-test the stdio transport when upgrading.
- `httpx` for the VectorStep HTTP client.
- `pyyaml` for local YAML handling (e.g. any client-side pre-validation).

**stdio only**, for v1. This is what Claude Code/Desktop expect for a locally
spawned MCP server. A streamable-HTTP transport (for a remotely hosted server
shared by multiple clients) is a plausible future addition but is
intentionally **not built** in this version — stdio covers the current
single-operator, locally-spawned use case.

### Write-path design notes

- **Git awareness.** In the VectorStep repo, `service/pipelines/` is
  git-controlled and `service/steps/` is gitignored. Writing a pipeline or
  step through this server's tools does **not** commit it — every
  `create_*`/`update_*` result says so explicitly. This server never runs
  `git commit`.
- **Secrets.** VectorStep configs use `${ENV_VAR}` placeholders for secrets. This
  server preserves them verbatim and never resolves or inlines an env value
  into a stored file.
- **Destructive operations.** `delete_pipeline`/`delete_step` require an
  explicit `confirm=true` and return the deleted YAML so the operation is
  auditable and recoverable. `overwrite=true` on create is likewise explicit
  and non-default.

## VectorStep Gateway MCP

An MCP server that exposes the VectorStep Gateway — a WebSocket gateway that runs
AI agents with MCP tool access, used as an executor backend for VectorStep
pipelines — to MCP clients such as Claude Code and Claude Desktop.

It lets an MCP client:

- create and edit agents (`agent.yaml` + `soul.md`), with the same validation
  the gateway itself uses — schema, plus reference checks (`model`/
  `model_fallbacks` must map to a configured LLM provider, `tools:` must map
  to configured MCP servers),
- inspect what's available — configured MCP tool servers and their tools,
  configured LLM providers, and
- read gateway health/metrics.

Pipelines/steps are **not** authored here — that's the job of the companion
VectorStep Service MCP, above. The two have clean, non-overlapping tool sets:
agents live here, pipelines/steps live there.

### Relationship to VectorStep Gateway

This is a **separate, standalone repository and process**. It is not a
package inside the VectorStep Gateway repo and has **no import-level dependency**
on it. The two are coupled *only* over HTTP: this server is a thin `httpx`
client against the gateway's JSON API.

```
Claude Code/Desktop  <--stdio (MCP)-->  vectorstep-gateway-mcp  <--HTTP-->  VectorStep Gateway
```

Because the coupling is HTTP-only, this repo can be developed, versioned, and
deployed independently of the gateway.

### Configuration

Set via environment variables:

| Variable | Default | Purpose |
|---|---|---|
| `GATEWAY_BASE_URL` | `http://127.0.0.1:18780` | Base URL of the VectorStep Gateway instance this server talks to. |
| `GATEWAY_OPERATOR_TOKEN` | *(unset)* | Bearer token sent on every gateway call — the gateway's **operator token**, the value written to `<identity>/device-auth.json` on first run (see [Gateway overview](/docs/gateway/overview/)). Required for any tool to work; the gateway's HTTP endpoints this server calls are not exempt from auth. |

**Never** set `GATEWAY_OPERATOR_TOKEN` (or any provider API key) to a value
you'd mind an LLM seeing echoed back — this server holds it only to
*authenticate outbound requests*; no tool ever returns it, a provider key, or
any other `config.yaml` secret in a response (enforced and tested — see
`tests/test_e2e.py::test_no_secret_leaks_across_every_read_tool`).

### Installing

This isn't published to PyPI — install it from the checked-out repo into its
own virtualenv:

```bash
cd VectorStep-Gateway-MCP
python3 -m venv .venv
.venv/bin/pip install -e .
```

That gives you a `python -m vectorstep_gateway_mcp` entry point at
`.venv/bin/python`. Note the **absolute path** to that interpreter — you'll
need it below, since MCP clients spawn the server directly (no shell/profile
sourced, so a bare `python` on your `$PATH` won't reliably resolve).

Also make sure a VectorStep Gateway instance is actually running for it to talk to
(`uvicorn gateway.main:app --port 18780` in the `VectorStep-Gateway` directory) —
this MCP is just a client; it has nothing to do without a gateway to call.

### Configuring your MCP client

**Claude Code**, from the repo root (or anywhere, using absolute paths):

```bash
claude mcp add vectorstep-gateway \
  --env GATEWAY_BASE_URL=http://127.0.0.1:18780 \
  --env GATEWAY_OPERATOR_TOKEN=<your-operator-token> \
  -- /absolute/path/to/VectorStep-Gateway-MCP/.venv/bin/python -m vectorstep_gateway_mcp
```

Or add it by hand to `.mcp.json` (project-scoped) or `~/.claude.json`
(user-scoped, under `mcpServers`):

```json
{
  "mcpServers": {
    "vectorstep-gateway": {
      "command": "/absolute/path/to/VectorStep-Gateway-MCP/.venv/bin/python",
      "args": ["-m", "vectorstep_gateway_mcp"],
      "env": {
        "GATEWAY_BASE_URL": "http://127.0.0.1:18780",
        "GATEWAY_OPERATOR_TOKEN": "<your-operator-token>"
      }
    }
  }
}
```

**Claude Desktop** — same `mcpServers` shape, in
`~/Library/Application Support/Claude/claude_desktop_config.json` (macOS).

:::note[stdio isn't a REPL]
Don't run `python -m vectorstep_gateway_mcp` directly in a terminal expecting a
REPL. stdio MCP servers aren't interactive — they read framed JSON-RPC
messages from stdin, written by an MCP *client* (Claude Code, Claude
Desktop, or a debug tool), not typed by a human. If you run it manually,
it'll just sit there; pressing Enter sends an empty line, which isn't valid
JSON-RPC and logs a `json_invalid` error (harmless — it doesn't crash the
server, it just means you sent it garbage).

To actually exercise it:
- **Through Claude Code**, once registered (above) — just ask it to use a
  `vectorstep-gateway` tool in a normal session.
- **Standalone, for debugging** — use the
  [MCP Inspector](https://github.com/modelcontextprotocol/inspector):
  ```bash
  npx @modelcontextprotocol/inspector /absolute/path/to/.venv/bin/python -m vectorstep_gateway_mcp
  ```
  which opens a web UI to call tools one at a time and see raw request/response.
:::

### Tool inventory

**Read tools:**

| Tool | Maps to | Returns |
|---|---|---|
| `list_agents()` | `GET /agents` | name, model, model_fallbacks, tools, `version` (content hash of the full config, incl. soul.md — VectorStep uses it to scope calibration buckets) for every loaded agent |
| `get_agent(name)` | `GET /agents/{name}` | parsed config + raw agent.yaml text + full soul.md + `version` |
| `list_mcp_servers()` | `GET /mcp/servers` | configured MCP servers — running, pid, restart_count |
| `list_mcp_tools()` | `GET /mcp/tools` | every tool available across all MCP servers, grouped by server |
| `list_providers()` | `GET /providers` | configured LLM providers, whether each has credentials, model-string prefix — never keys |
| `get_metrics()` | `GET /metrics` | gateway Prometheus metrics as raw exposition text under `"metrics"` |
| `validate_agent(agent_yaml, soul_md="")` | `POST /agents/validate` | `{valid, errors}` — dry-run, **no write** |

**Write / action tools:**

| Tool | Maps to | Notes |
|---|---|---|
| `create_agent(name, agent_yaml, soul_md, overwrite=False)` | `POST /agents` | `name` must match the YAML's own `name:` field; 'collision' error on an existing name unless `overwrite=True` |
| `update_agent(name, agent_yaml=None, soul_md=None)` | `PUT /agents/{name}` | 'not_found' if absent; pass only the field(s) you want to change — the other is left untouched. Changes this agent's `version`, resetting its calibration history in VectorStep (see the tool's own docstring) |
| `delete_agent(name, confirm=False)` | `DELETE /agents/{name}` | **destructive** — refuses to call the gateway at all without `confirm=True`; returns the deleted `agent_yaml`/`soul_md` for audit |
| `reload()` | `POST /reload` | usually implicit in create/update/delete — exposed for the rare case an agent dir was edited outside these tools |

Every `create_agent`/`update_agent`/`delete_agent` call validates schema
**and** reference integrity server-side (the gateway's `AgentConfig` +
`validate_agent_models()`) before writing anything — a bad `model` string or
a `tools:` entry naming an unconfigured MCP server is rejected with a
structured `validation` error, and the write never touches disk (see the
gateway's atomic validated-write path, `gateway/agent_writer.py`).

### Dependencies & transport

- **MCP SDK**: pinned to `mcp==1.28.1` (the latest release at the time this
  project was created — also the same pin `VectorStep-Service-MCP` uses). Bump
  deliberately and re-test the stdio transport when upgrading.
- `httpx` for the gateway HTTP client.
- `pyyaml` — not currently used for client-side validation (agent YAML is
  passed through as a raw string and validated server-side only, per design;
  see "Write-path design notes" below), kept for parity with the sibling MCP
  and in case a future client-side pre-check is added.

**stdio only**, for v1, same rationale as the Service MCP above.

### Write-path design notes

`create_agent`/`update_agent`/`delete_agent` are **thin adapters** over the
gateway's REST write endpoints — this server never writes `agent.yaml`/
`soul.md` itself, and never imports the gateway's Pydantic models
(`AgentConfig`) to pre-validate locally. Tool input schemas are plain
strings (`agent_yaml: str`, `soul_md: str`); the gateway is the single
source of truth for what's valid, so there's no vendored schema copy that
can drift out of sync with the real one. Use `validate_agent` for a fast,
authoritative, no-write check before calling `create_agent`/`update_agent`.

Other notes for authors of agents via this server:

- **Git awareness.** In the gateway repo, `agents/` (and `config.yaml`) are
  **gitignored** — personal to the deployment, unlike VectorStep's
  git-controlled `pipelines/`. Writing an agent through this server's tools
  is never a git-commit concern; every `create_agent`/`update_agent`/
  `delete_agent` result says so explicitly. This server never runs
  `git commit`.
- **Secrets.** `agent.yaml` can reference `${ENV_VAR}` placeholders (the
  gateway resolves these at its own startup, not here). This server
  preserves them verbatim in whatever you pass to `create_agent`/
  `update_agent` and never resolves or inlines an env value into a stored
  file. Separately — and more strictly than the sibling MCP — **no tool ever
  returns** the operator token, a provider API key, or any other
  `config.yaml` secret, regardless of what's asked for.
- **Reference integrity.** `model`/`model_fallbacks` must map to a
  configured provider (`list_providers` shows what's available and the
  prefix to use) and `tools:` must reference configured MCP servers
  (`list_mcp_servers` shows what's available) — `create_agent`/
  `update_agent` reject otherwise with a structured `validation` error
  describing exactly which field and value failed.
- **Destructive operations.** `delete_agent` requires an explicit
  `confirm=true` and returns the deleted `agent_yaml`/`soul_md` so the
  operation is auditable and recoverable. `overwrite=true` on `create_agent`
  is likewise explicit and non-default.
