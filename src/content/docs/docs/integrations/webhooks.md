---
title: Webhook sources
description: Webhook intake, source detection, normalisation, and the generic source schema.
sidebar:
  order: 1
---

A single `POST /webhook` endpoint accepts any source. Pluggable parsers
normalise each payload into a common `NormalisedContext`; the resolver matches
it to a pipeline; idempotent deduplication stops repeat deliveries triggering
repeat runs.

## Webhook intake & source detection

Single endpoint: `POST /webhook`

Source is identified via query parameter: `/webhook?source=alertmanager`

Header fallback also supported: `X-Pipeline-Source: alertmanager`

The source value maps to a registered parser class. Registered sources: `alertmanager`, `generic`.

## Normalisation layer

Each source parser implements `BaseParser` and produces a `NormalisedContext` object. This is the universal data model that all downstream pipeline logic operates on.

```python
class NormalisedContext(BaseModel):
    source: str                    # e.g. "alertmanager" — for audit only
    pipeline: str                  # pipeline config name to resolve
    severity: str | None           # critical / warning / info
    labels: dict[str, str]         # service, environment, etc.
    summary: str | None            # human readable description of the event
    fingerprint: str | None        # dedup key — see Idempotency & Deduplication below
    raw: dict                      # original unmodified payload
    metadata: dict                 # source-specific extras
    received_at: datetime
```

### Generic source

Any tool that can send HTTP can target `POST /webhook?source=generic` using a standardised schema — no bespoke parser needed. The generic source always requires an explicit `pipeline` name, which bypasses the resolver's trigger matching entirely.

**Generic payload schema:**
```json
{
  "pipeline": "my-pipeline",      // required — names the pipeline explicitly
  "event": "order.placed",        // optional — stored in labels["event"] for audit
  "source": "shopify",            // optional — defaults to "generic"
  "summary": "Human readable...", // optional
  "idempotency_key": "order-12345", // optional — dedup key, see Idempotency & Deduplication below. Omit to disable dedup.
  "data": { ... }                 // optional — free-form dict, lands in metadata
}
```

**Mapping to NormalisedContext:**
- `pipeline` → `pipeline` (resolver uses this directly, skips trigger matching)
- `event` → `labels["event"]`
- `source` → `source`
- `summary` → `summary`
- `idempotency_key` → `fingerprint`
- `data` → `metadata` (accessible in prompts as `{{metadata.field_name}}` or just `{{field_name}}` via leaf flattening)

## Pipeline resolution

The `resolver` loads all YAML configs from `PIPELINE_CONFIG_DIR` and matches the incoming `NormalisedContext` against each config's `trigger.match` block. First match wins. Configs should be ordered by specificity (more specific matches first).

Pipeline name can also be explicitly set by the source parser if the webhook payload contains a pipeline attribute (e.g. an Alertmanager label `pipeline: alert-triage-critical`).

**Match operators:** a `trigger.match` value can be a plain scalar (exact equality, the original behaviour) or a single-key operator dict for richer matching:

```yaml
trigger:
  match:
    severity: critical                    # exact match (unchanged)
    environment:
      in: [prod, staging]                 # membership
    service:
      not_in: [test-runner]                # exclusion
    summary:
      regex: "(?i)timeout"                 # regex search (re.search, not full match)
    error_rate:
      gt: "5"                              # numeric comparison — gt | gte | lt | lte
    severity:
      ne: info                             # not-equal
```

| Operator | Behaviour |
|---|---|
| `eq` | Same as a plain scalar — exact equality |
| `ne` | Not equal |
| `in` | Value is a member of the given list |
| `not_in` | Value is not a member of the given list |
| `regex` | `re.search(pattern, str(actual))` — `None` actual never matches |
| `gt` / `gte` / `lt` / `lte` | Numeric comparison — both sides are cast with `float()`; a non-numeric actual or expected value never matches |

A match value dict must have exactly one key; an unknown operator or a multi-key dict logs a warning and never matches (fails closed).

## Idempotency & deduplication

Alertmanager (and similar sources) re-send the same alert repeatedly — every evaluation
interval while it's firing, and again on resolve. Without dedup, each resend spawns a
fresh pipeline run: redundant LLM spend, and worse, **overlapping remediation runs for
the same alert**.

### Fingerprint

Each parser populates `NormalisedContext.fingerprint` — the dedup key:

| Source | Fingerprint source |
|---|---|
| `alertmanager` | The matched alert's `fingerprint` field (Alertmanager's own label-hash), or the group's `groupKey` for the `common_labels` strategy. Falls back to a hash of the relevant labels if neither is present. The alert `status` (`firing`/`resolved`) is appended, so a resolve notification is never suppressed as a duplicate of the firing run. |
| `generic` | The optional `idempotency_key` field (see Generic source above). If omitted, `fingerprint` is `None` and dedup is skipped for that webhook — generic triggers (orders, etc.) are opt-in. |

### Dedup check

On `POST /webhook`, after the pipeline is resolved and before a run is started, VectorStep
looks for an existing `pipeline_runs` row with the same `pipeline_name` + `fingerprint`:

- **In-flight** (`status="running"`) — **always** suppressed, regardless of config. This
  is the race-prevention case: two overlapping triage/remediation runs for the same alert
  never run concurrently.
- **Recent** (`triggered_at` within `window_seconds` of now) — suppressed even if the
  prior run has completed. This absorbs Alertmanager's repeat-fire on a flapping alert.

If either matches, no new run is created. The webhook still gets a `202`, but with
`status: "deduplicated"` and the matching run's `run_id`:

```json
{
  "status": "deduplicated",
  "run_id": "<existing-run-id>",
  "source": "alertmanager",
  "pipeline": "alert-triage-critical",
  "severity": "critical",
  "summary": "...",
  "reason": "Duplicate of run <existing-run-id> (status=running)"
}
```

### Configuration

Service-wide defaults in `config.yaml`:

```yaml
dedup:
  enabled: true
  window_seconds: 300
```

Per-pipeline override via `trigger.dedup` (both fields optional — `None` falls back to
the service default):

```yaml
trigger:
  match:
    severity: critical
  dedup:
    window_seconds: 600   # this pipeline's triage takes a while — widen the window
    # enabled: false       # or opt this pipeline out of dedup entirely
```

:::caution[Race safety]
The application-level check above narrows the window but two webhooks
with the same fingerprint arriving within milliseconds of each other can both pass it
before either's run row is inserted. The actual guarantee comes from a partial unique
index — `UNIQUE (pipeline_name, fingerprint) WHERE status = 'running'` (migration in
`service/src/db/database.py`). If both requests' inserts race, the database accepts
exactly one; the loser's insert raises `IntegrityError`, which `PipelineRunner` catches
in `_db_create_run()` and turns into an early `status="deduplicated"` result — no second
pipeline ever executes. NULL fingerprints are never equal in a unique index, so
fingerprint-less sources (sub-pipelines, re-runs) are unaffected. The one rough edge: the
loser's HTTP response was already sent as `"status": "accepted"` with its own `run_id`
before the conflict was discovered (responses are returned before the background task
runs), so that particular `run_id` 404s on `GET /runs/{run_id}` — the work itself is
never duplicated, only that one run_id is left unrealized.
:::

## Adding a new source parser

1. Create `src/normaliser/<source>.py`
2. Implement `BaseParser` — produce a `NormalisedContext`
3. Register in `src/normaliser/__init__.py` source map

See [Extending VectorStep](/docs/design/extending/) for the full checklist shared
across parsers, executors, and library steps.
