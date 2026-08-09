---
title: Analytics API
description: Read-only pipeline, step, and agent inspection and analytics endpoints, added to back the VectorStep Service MCP.
sidebar:
  order: 2
---

These endpoints were added so the
[VectorStep Service MCP](/docs/reference/write-api/#the-vectorstep-service-mcp) can
author and inspect pipelines without importing the VectorStep codebase. The
analytics endpoints share their aggregation queries with the
`/ui/insights/*` pages (`src/analytics.py`), so the numbers they return can
never drift from what the UI shows for the same data.

## GET /pipelines/{name}

Full resolved pipeline config (`.model_dump()`) plus the raw YAML text from
disk.

→ `{"config": {...}, "yaml": "name: ...\n..."}` — 404 if unknown.

## GET /steps

Library step summaries: name, description, tags, executor, agent.

→ `{"steps": [{"name": "...", "description": "...", "tags": [...], "executor": "...", "agent": "..."}]}`

## GET /steps/{name}

Full step config plus raw YAML from the (gitignored) step library directory.

→ `{"config": {...}, "yaml": "..."}` — 404 if unknown.

## GET /agents

Agents merged across OpenClaw and VectorStep Gateway backends — read-only. A down
backend contributes an empty slice plus an `errors` entry, never a 500.

→ `{"agents": [{"name": "...", "executor": "openclaw"|"gateway", "model": "..."}], "errors": {}}`

## GET /pipelines/{name}/stats

Operational and judged-accuracy stats for one pipeline.

Query params: `time_range` (`24h`|`7d`|`30d`|`all`, default `7d`), `stage`
(`production`|`testing`|`all`, default `production`, matching every other
rollup in the app — see [Pipeline stages](/docs/concepts/stages/)).

```bash
GET /pipelines/{name}/stats?time_range=7d&stage=production
```

→ `{"pipeline_name", "runs_total", "status_counts": {...}, "success_rate", "tokens": {"input", "output", "total"}, "cost": {"total", "unpriced_steps", "currency"}, "duration_seconds": {"avg", "p95"}, "accuracy": {"correct", "partial", "incorrect", "total", "correct_pct"}, "teams": [...]}`

:::note
`success_rate` = completed ÷ terminal runs (excludes still-running); `accuracy`
is the separate *judged* rollup from `RunFeedback` — null/zeroed when nothing's
been graded, which is **not the same as "0% accurate"**. `cost.total` is a SUM
that skips NULL (unpriced) steps; `cost.unpriced_steps` is a separate count of
how many were skipped, so this can never be mistaken for a complete total —
see [Cost accounting](/docs/operations/cost-accounting/). 404 if the pipeline
name is unknown.
:::

## GET /stats/pipelines

The same per-pipeline payload as above, for every pipeline with a run in
range — the JSON behind the `/ui/insights/pipelines` table. Rank client-side
to answer "which pipeline fails most / costs most / is least accurate".

```bash
GET /stats/pipelines?time_range=7d&stage=production
```

→ `{"pipelines": [{...}, ...]}`

## GET /pipelines/{name}/promotion-readiness

Owner-defined promotion-readiness readout for one pipeline (see
[Promotion readiness](/docs/concepts/readiness/)) — advisory only, does not
gate or block `stage: testing -> production`. Evaluates every step against
its effective `readiness:` config (four independent tiers: operational,
confidence, accuracy, calibration) against evidence from the pipeline's own
current stage. Works for a pipeline of either stage; 404 if the pipeline name
is unknown.

:::note
`bin_width`/`n_min` are the INFORMATIONAL defaults used only for the
observed-calibration snapshot on steps with no calibration tier configured —
a configured step's own values always win, and neither is read from
`config.yaml`'s `calibration:` block (which only feeds the live runtime
gate).
:::

```bash
GET /pipelines/{name}/promotion-readiness?bin_width=0.1&n_min=20
```

→ `{"pipeline_name", "pipeline_stage", "evidence_stage", "criteria_source": "configured"|"none", "verdict": "ready"|"not_ready"|"building"|"no_data"|"not_configured", "gathered_at", "summary": {"ready","not_ready","building","no_data","not_configured","total"}, "steps": [{"step_name", "kind", "executor", "when", "verdict", "confidence_threshold", "criteria": {tier: {...knobs, "source"} | null, ...}, "current_config": {"prompt_hash", "agent_version", "agent_version_source", "prompt_hash_source", "prompt_hash_matches_history"}, "evidence": {"runs_total", "rows_total", "marked_total", "first_seen_at", "last_seen_at"}, "tiers": {"operational", "confidence", "accuracy", "calibration": {"verdict", ...}}, "observed_combos": [...], "narrative": ["...", ...], "notes": ["...", ...] }, ...]}`

## POST /pipelines/{name}/promotion-readiness/preview

Preview a candidate `readiness:` block against the same evidence, without
writing anything — the same response shape as the GET above, plus
`applied_to`, `scope` (`"pipeline"`|`"step"`), `yaml_snippet`/
`yaml_snippet_indented` (server-generated, validated through the real
`ReadinessConfig` — this endpoint cannot be used to produce YAML the loader
would reject), `yaml_target_hint`, `evidence_gathered_at`,
`evidence_cache_hit` (a 30s in-process cache, used only by this endpoint —
the GET above always re-gathers fresh).

- body: `{"readiness": {"operational": {"min_runs": 20}, ...}, "apply_to": ["step-name"] | null}`
- 422 with Pydantic's own detail on an invalid `readiness:` body; 400 if
  `apply_to` names a step that doesn't exist.

## GET /steps/{name}/stats

Same stats shape as `/pipelines/{name}/stats`, aggregated per library step
across every pipeline that uses it (`avg_input_tokens`/`avg_output_tokens`
instead of `teams`). 404 if the step name is unknown to the library.

```bash
GET /steps/{name}/stats?time_range=7d&stage=production
```

## GET /steps/{name}/models

Per (agent, model, provider) breakdown for one step — un-blends the single
aggregate above so "which model performs best for this step" can actually be
answered (success rate, avg tokens, avg duration, judged accuracy per model,
instead of averaged across every model the step has ever run under). Same
rows as the existing `/ui/insights/steps` drilldown's per-agent/model table.
404 if the step name is unknown to the library.

```bash
GET /steps/{name}/models?time_range=7d&stage=production
```

→ `{"step_name": "...", "breakdown": [{"agent", "provider", "model", "runs_total", "status_counts", "success_rate", "avg_input_tokens", "avg_output_tokens", "avg_duration_seconds", "accuracy": {...}}, ...]}` — sorted by `runs_total` desc.

## GET /steps/{name}/calibration

Calibration bins for one step, per (agent, model, provider, prompt_hash,
agent_version) — the same data behind the `/ui/insights/steps` calibration
bins (`pipeline/calibration.py`), exposed as its own stat.

:::note
NOT `time_range`/`stage` scoped — always the step's full production history,
since calibration is a track-record measurement (windowing it would defeat
the point). 404 if the step name is unknown.
:::

`prompt_hash`/`agent_version` are part of the bucket key so editing a prompt
or a Gateway agent's config starts a fresh bucket instead of silently pooling
with the old one's history. See `SPEC-prompt-versioning.md` in the VectorStep
repo.

```bash
GET /steps/{name}/calibration?bin_width=0.1&n_min=20
```

→ `{"step_name": "...", "buckets": [{"agent", "provider", "model", "prompt_hash", "agent_version", "total_n", "bins": [{"lo", "hi", "n", "mean_label", "validated"}, ...] (always 1/bin_width bins), "recommendation": "runs scoring ~90% here are only 75% correct..." or null }, ...]}` — sorted by `total_n` desc.

## GET /steps/{name}/versions

Every prompt template version VectorStep has recorded for this step, newest
first — "did that prompt edit actually help?" made answerable with data.
Each version carries its diff against the version before it (null for the
oldest) and its own calibration data scoped to just that version. NOT
`time_range`/`stage` scoped, same reasoning as `/calibration` above. 404 if
the step name is unknown.

```bash
GET /steps/{name}/versions
```

→ `{"step_name": "...", "versions": [{"prompt_hash", "template", "first_seen_at", "last_seen_at", "runs_total", "labelled_n", "diff_from_previous", "calibration": [...] }, ...]}` — sorted by `first_seen_at` desc.

:::caution
May include one synthetic entry with `"prompt_hash": null` — pre-versioning
or un-backfilled runs (`PipelineStep.prompt_hash IS NULL`), which have no
hash to register under. Its `"template"` is also null (no text was ever
captured), but `"runs_total"`/`"labelled_n"` are real — don't mistake this
for the step having no history. `"diff_from_previous"` is null both for this
entry and for whichever real version comes right after it (nothing to diff
against).
:::

## GET /agents/{name}/versions

Every Gateway `agent_version` VectorStep has a snapshot for, newest first — the
only place recoverable text for an `agent_version` survives once the Gateway
agent moves on to a newer config. `name` is the bare agent name (no
`gateway:` prefix). 404 if VectorStep has no snapshot rows for this agent at all.

```bash
GET /agents/{name}/versions
```

→ `{"agent": "gateway:...", "versions": [{"agent_version", "soul_md", "agent_yaml", "note", "first_seen_at", "last_seen_at", "diff_from_previous", "used_by_steps": [...] }, ...]}` — sorted by `first_seen_at` desc.

:::note
`note` (instead of `soul_md`/`agent_yaml` text) means VectorStep couldn't confirm
that snapshot, not that the agent had no config. Same synthetic-entry
behaviour as `/steps/{name}/versions` above, for rows where
`PipelineStep.agent_version IS NULL` — `"agent_version": null`,
`"soul_md"`/`"agent_yaml"`: null, `"note"` explains why in plain language,
`"used_by_steps"` is still real.
:::
