---
title: Write API
description: Endpoints for creating, updating, validating, and deleting pipelines and steps, plus the VectorStep Service MCP that's built on them.
sidebar:
  order: 3
---

All raw-YAML in (the YAML's own `name:` field is authoritative — never taken
from the URL for create), Pydantic-validated, and written with an **atomic
validated-rollback**: a candidate directory state (the real files plus the
one new/changed/removed entry) is fully reloaded in memory first; only if
that succeeds does the real file get written (temp file + `os.replace`).
This is what catches a step-library change that would silently break some
*other* pipeline's `use:` resolution — the live config and registry are left
completely untouched on any failure (`src/config_writer.py`).

## Pipeline endpoints

### POST /pipelines

Create a new pipeline. 409 (collision) if `service/pipelines/{name}.yaml`
already exists, unless `overwrite=true`. 400 on validation failure.

- body: `{"yaml": "name: ...\n...", "overwrite": false}`
- → `{"config": {...}, "committed": false, "note": "..."}`

:::note
`committed` is always false: the file is written and reloaded, but this is a
git-controlled directory — you still need to `git add`/`git commit` yourself.
:::

### PUT /pipelines/{name}

Update an existing pipeline. 404 if absent. The URL name and the YAML's own
`name:` must agree — 400 if they differ (a rename is a delete + create).

- body: `{"yaml": "name: ...\n..."}`

### DELETE /pipelines/{name}

Delete a pipeline's YAML. 404 if absent. Returns the deleted YAML so the
deletion is auditable/recoverable, then reloads.

→ `{"deleted": "...", "yaml": "...", "committed": false, "note": "..."}`

### POST /pipelines/validate

Validate a candidate pipeline YAML without writing anything — the safe
iterate loop before `POST`/`PUT` above.

- body: `{"yaml": "..."}`
- → `{"valid": true, "errors": []}` or `{"valid": false, "errors": [{"loc": [...], "msg": "..."}]}`

## Step library endpoints

The same four operations, for the step library (`service/steps/` —
gitignored, so `committed` is always false and nothing here is ever tracked
in git). Updating or deleting a step also re-validates every pipeline that
references it via `use:` — a step change/removal that would break one fails
with a `reload_failed` error and nothing is written/removed.

### POST /steps

Create a new library step.

- body: `{"yaml": "...", "overwrite": false}`

### PUT /steps/{name}

Update an existing library step.

- body: `{"yaml": "..."}`

### DELETE /steps/{name}

Delete a library step.

### POST /steps/validate

Validate a candidate step YAML without writing anything.

- body: `{"yaml": "..."}`

## Error shape

All of the above return FastAPI's standard `{"detail": ...}` on failure; for
write/delete failures `detail` is `{"type": "validation" | "not_found" |
"collision" | "reload_failed", "message": "...", ...}` — the explicit `type`
lets a caller (like the MCP) distinguish e.g. a plain validation error from a
write that would break another pipeline's resolution, both of which can
otherwise show up as the same status code.

## Secrets

`${ENV_VAR}` placeholders in a submitted YAML are preserved verbatim — these
endpoints never resolve or inline an environment value into a stored file.

## The VectorStep Service MCP

The endpoints on this page and [Analytics API](/docs/reference/analytics-api/)
exist to back **VectorStep Service MCP**, a separate, standalone repository
(sibling to this one) that exposes them as
[MCP](https://modelcontextprotocol.io) tools for Claude Code/Desktop:
pipeline and step-library authoring (with the same server-side validation
this service uses), run/step inspection, the operational and
judged-accuracy analytics above, and manual run/feedback actions.

It is a thin `httpx` client — the only coupling between the two repos is this
HTTP API; the MCP has no import-level dependency on the VectorStep codebase and
does not touch the database or YAML files directly. It holds one bearer
token (`VECTORSTEP_WEBHOOK_TOKEN`) sent on every call, required only where this
service already requires it.

For the full tool inventory, install instructions, and client configuration,
see [MCP servers](/docs/integrations/mcp/).
