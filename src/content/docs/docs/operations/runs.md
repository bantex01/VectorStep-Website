---
title: Run storage
description: The database tables that persist every run, step, artifact, and piece of human feedback.
sidebar:
  order: 4
---

Every pipeline run, and every step within it, is persisted in the database in
full detail — enough to reconstruct exactly what happened, what was sent to
each agent, and how each confidence decision was reached, without needing the
original trace to still be available. This page documents those tables and
the artifact store that keeps large step outputs off the database entirely.

## Run storage

**pipeline_runs**

| Column | Type | Description |
|---|---|---|
| `id` | uuid, pk | Run identifier (returned in `/webhook` 202 response) |
| `pipeline_name` | str | |
| `source` | str | Webhook source or `"scheduler"` |
| `triggered_at` | datetime | |
| `status` | str | running / completed / stopped / aborted / escalated / failed |
| `normalised_context` | json | Full NormalisedContext at trigger time |
| `raw_payload` | json | Original unmodified webhook payload |
| `completed_at` | datetime, nullable | |
| `logs` | json, nullable | Structured run event log — array of `{ts, level, event, msg}` objects. Populated at run completion. Events cover step start/complete/fail/skip/escalate/abort, verifier results, parallel group outcomes, notifications sent, and (for `interrupted` runs) the startup interruption sweep. |
| `parent_run_id` | uuid, nullable, indexed | Set for sub-pipeline runs (`executor: pipeline`). Links back to the parent run. NULL for top-level runs. |
| `team` | str, nullable, indexed | Owning team, resolved from the Bearer token that authenticated the webhook (see [Team attribution](/docs/operations/teams/)). NULL for unattributed/legacy-token runs. |
| `stage` | str, indexed | `testing` or `production`, copied from `PipelineConfig.stage` (see [Pipeline stages](/docs/concepts/stages/)) at trigger time — persisted per-run so promoting a pipeline never reclassifies its prior runs. Defaults to `production` at the DB layer for rows that predate this column. |

**pipeline_steps**

| Column | Type | Description |
|---|---|---|
| `id` | uuid, pk | |
| `run_id` | fk | → pipeline_runs.id |
| `step_name` | str | `"step-name"` for sequential; `"group-name/branch-name"` for parallel branches |
| `step_index` | int | Sort order within run |
| `executor` | str | `openclaw` / `gateway` / `human` / `webhook` |
| `agent` | str | `executor:agent-name` (e.g. `openclaw:sre-triage`) |
| `model` | str | Actual model used, from executor metadata |
| `prompt` | text | Rendered prompt sent to the agent — the actual, fully-substituted text, not the `{{ }}` template. Populated for `executor: gateway` steps only; other executors don't yet stash their rendered prompt back out, so their rows fall back to a JSON dump of `executor_config` (recognisable by starting with `{`) — the UI's Prompt disclosure hides that fallback rather than showing it as if it were a real prompt. |
| `raw_output` | json | Full unparsed executor response |
| `parsed_output` | json | Validated LLMOutput (excluding raw_response) |
| `status` | str | completed / stopped / escalated / aborted / failed |
| `primary_confidence` | float | Raw confidence from the primary agent |
| `verifier_confidence` | float, nullable | Verifier agent confidence (if verifier ran) |
| `effective_confidence` | float | Confidence used for threshold gate (post-combination) |
| `grounding_score` | float, nullable | Shadow-mode grounding score **G** ∈ [0,1] — the fraction of the step's load-bearing claims a blind grounding judge found supported by evidence in the step's own execution trace. NULL when grounding wasn't configured for the step, or when it had no trace to check against. Never gates on its own — see [How confidence and calibration work](/docs/concepts/confidence/). |
| `trust_report` | json, nullable | Per-step TrustReport: the trust vector `{S, S_after_V, V, V_mode, V_combination_strategy, V_veto_floor, G, C, D}`, `combined_trust`, `gate` (`{policy, confidence_threshold, on_low_confidence}` — `policy` is `legacy_confidence` / `trust_vector`), and — for grounding — the per-claim support breakdown, and — for deterministic checks — the full per-check detail. Populated for steps with a **verifier**, a `grounding:` block, `deterministic_checks:`, and/or `calibration: {enforce: true}` — i.e. any mechanism beyond the plain single-confidence gate, not just the trust-vector ones; `mode` is `"shadow"` when recorded-only or `"enforced"` when grounding/deterministic/calibration actually participated in the gate (a verifier-only step is always `"shadow"`, since the verifier's downward-only combine has always been part of the legacy gate). A `calibration` sub-key (bucket/bin/n/n_min/validated/raw/calibrated/on_uncalibrated) is present only for a step with `calibration: {enforce: true}`. See [How confidence and calibration work](/docs/concepts/confidence/). |
| `deterministic_passed` | bool, nullable | Whole-step pass/fail across all declared deterministic checks — `True` only if every check passed. NULL when no `deterministic_checks:` were declared. Full per-check detail lives in `trust_report.deterministic_checks`. |
| `duration_ms` | int | |
| `executed_at` | datetime | |
| `artifacts` | json, nullable | `{key: reference}` map — references are opaque strings pointing to artifact files on disk. Content is not stored in the DB. See [Artifact storage](#artifact-storage) below. |
| `agent_trace` | json, nullable | Ordered execution trace from the VectorStep Gateway executor — array of `{type, ...}` objects. `type` is one of: `llm_call` (iteration marker), `thinking` (extended thinking block), `text` (response text), `tool_call` (MCP tool invoked with arguments), `tool_result` (MCP tool response). **Not truncated** — the full content the Gateway returns on its final `ok` frame is stored and rendered as-is; only the ephemeral *live* SSE tail truncates content (at 200 chars) for a fast in-progress preview, never the persisted record. If a `tool_result`'s content looks cut off on a *completed* run, that truncation happened upstream (the Gateway server or the MCP tool itself), not in this column. NULL for all other executors (`openclaw`, `human`, `webhook`). |
| `verifier_agent` | str, nullable | `executor:agent-name` for the verifier call (mirrors `agent` above), e.g. `gateway:principal-sre`. NULL if no verifier ran, or for rows persisted before this column existed. |
| `verifier_model` | str, nullable | Actual model used by the verifier call, from executor metadata. NULL if no verifier ran. |
| `verifier_provider` | str, nullable | Gateway provider key for the verifier call (gateway executor only). NULL if no verifier ran or the verifier used a non-gateway executor. |
| `verifier_prompt` | text, nullable | Rendered prompt actually sent to the verifier — for `critic` mode this is the meta-prompt with the primary's own prompt+response embedded; for `independent` mode it's a verbatim copy of the primary's prompt. Gateway executor only; NULL if no verifier ran, the verifier used a non-gateway executor, or the row predates this column. |
| `input_tokens` | int, nullable | Input tokens consumed by this step's primary executor call. Populated for `gateway` steps; NULL for others. For parallel/fan-out branches, each branch row has its own token count. |
| `output_tokens` | int, nullable | Output tokens produced by this step's primary executor call. |

**run_feedback**

| Column | Type | Description |
|---|---|---|
| `id` | uuid, pk | |
| `run_id` | str, unique, indexed | The run this feedback is for. One row per run — submitting again upserts. |
| `pipeline_name` | str, indexed | Denormalised from the run for efficient pipeline-level queries. |
| `outcome` | str | `correct` / `partial` / `incorrect` — human judgement of the run's result. |
| `notes` | text, nullable | Optional free-text context. |
| `submitted_at` | datetime | Created or last updated. |

**step_feedback**

| Column | Type | Description |
|---|---|---|
| `id` | uuid, pk | |
| `step_id` | str, unique, indexed | The specific step execution (`pipeline_steps.id`) this feedback is for. One row per step, upserted. |
| `run_id` | str, indexed | Denormalised for lookup. |
| `pipeline_name` | str, indexed | Denormalised. |
| `step_name` | str | Denormalised — may contain `/` for fan-out branches (e.g. `triage/0`). |
| `outcome` | str | `correct` / `partial` / `incorrect` — human judgement of that step's result. |
| `notes` | text, nullable | Optional free-text context. |
| `submitted_at` | datetime | Created or last updated. |

## Artifact storage

Steps can produce large artifacts (research reports, scraped data, compiled
documents) that would be unwieldy to pass inline through
`next_step_context`. The artifact store writes these to disk, keeps them out
of the database, and makes them available in downstream prompt templates by
content — not by reference.

### Producing an artifact

An agent returns an `artifacts` dict alongside its normal `LLMOutput` fields.
Each key is a name chosen by the agent; each value is the full text content:

```json
{
  "confidence": 0.9,
  "summary": "Research complete — 3 sources compiled",
  "next_step_context": "Coverage spans Q1–Q4 2025",
  "artifacts": {
    "research_report": "# Research Report\n\n## Source 1\n..."
  }
}
```

The runner intercepts the `artifacts` field before anything is stored in the
database. The content is written to
`{artifacts_dir}/{run_id}/{step_name}/{key}` and replaced with an opaque
reference string (`local://...`). SQLite only stores the reference; the blob
lives on disk.

### Consuming an artifact

Downstream steps reference artifact content in their prompt templates using
`{{artifacts.step_name.key}}`. The runner loads the content from disk at
render time — only for the steps that actually reference it.

```yaml
steps:
  - name: research
    executor: openclaw
    executor_config:
      agent: web-researcher
    prompt_template: |
      Research the topic and compile a full report.
      Return JSON with the usual fields plus an "artifacts" key:
      {"confidence": ..., "summary": ..., "next_step_context": ...,
       "artifacts": {"research_report": "..."}}

  - name: proofread
    executor: openclaw
    executor_config:
      agent: editor
    prompt_template: |
      Proofread and improve the following document:

      {{artifacts.research.research_report}}

      Return the corrected document as an artifact named "final_report".
```

Hyphens in step names follow the same rule as `steps.*` references — use
underscores in template expressions:

```
# Step named "web-research" is referenced as:
{{artifacts.web_research.report}}
```

### Lifecycle and cleanup

Artifact directories are scoped to a run (`{artifacts_dir}/{run_id}/`). A
daily APScheduler job (02:00) removes directories for runs older than
`retention_days`. Failed runs retain their artifacts for the same period,
which is useful for debugging.

To disable artifact storage entirely, omit the `artifacts:` block from
`config.yaml`. Steps that return an `artifacts` field will have it passed
through as a regular extra field rather than being written to disk.
