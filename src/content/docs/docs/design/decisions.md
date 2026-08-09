---
title: Key design decisions
description: The load-bearing decisions in VectorStep's design, and why they were made.
sidebar:
  order: 1
---

The short version: trust is a vector, not a scalar; every gating signal is
opt-in and additive; verifiers can never raise confidence; deterministic checks
fail closed; calibration is keyed by prompt and agent version so history never
silently pools across configurations.

The full list, verbatim from the project's own design notes:

| Decision | Rationale |
|---|---|
| Single `/webhook` endpoint | Source agnostic — parsers handle differences, pipelines don't care |
| Generic source requires explicit `pipeline` | Callers control the sending tool, so they can always name the pipeline |
| YAML pipeline configs | Git-controlled, human readable, no UI needed |
| Structured JSON output from LLM | Makes flow control deterministic — runner reads `confidence`/`proceed`, not prose |
| Extra fields allowed on LLMOutput | Domain fields (`jira_ticket`, `action`, etc.) pass between steps without schema changes |
| Isolated session key per step | Prevents context bleed between concurrent runs and between steps |
| SQLAlchemy async ORM, dialect swap via config only | SQLite for zero-infra local dev, Postgres for production — same code path |
| Alembic with auto-upgrade-on-boot | The hand-rolled add-column/add-index mechanism only ever adds nullable columns — it outgrew that at ~20 columns and couldn't rename, drop, backfill, or alter types. Auto-migrate-on-boot keeps the zero-ops experience; `database.auto_migrate: false` hands control to a DBA |
| DB-level partial unique index for in-flight dedup | The application-level pre-check narrows but cannot close a TOCTOU race on its own — the DB constraint is the actual correctness guarantee, the pre-check just avoids the round-trip in the common case |
| Adapter pattern for executors | Swap or mix backends with config changes only; steps in the same pipeline can use different executors |
| Runner owns flow decisions | LLM recommends, service decides — never blindly chain prompts |
| `executor:name` agent identity in DB | Disambiguates same agent name across different backends in run history and success rates |
| Artifact content on disk, not in DB | SQLite is not a blob store; large documents stay in the filesystem. DB row holds only the reference. |
| `{{artifacts.step.key}}` explicit namespace | Template authors know they are pulling a potentially large blob. Keeps `when:` conditions and `steps.*` references unambiguous. |
| `LocalArtifactStore` behind ABC | Swapping in S3 or another backend requires only a new class implementing four methods — no runner or config changes. |
| In-process APScheduler for cron | Zero extra infrastructure; same DB and runner code path as webhooks |
| `POST /reload` + SIGHUP | Config-driven system should never need a restart for a YAML edit |
| Step library with `use:` references | Eliminates step config duplication across pipelines; resolved at load time so runner is unaffected |
| `executor_config` deep-merge on library steps | Lets pipelines add `model` or `thinking_level` without repeating the full agent/session_key block |
| Structured run event log in DB | Per-run timeline queryable from the UI without grepping stdout; survives process restarts |
| `uvicorn.access` separated from service logs | HTTP request noise no longer pollutes run event output on stdout or in service.log |
| In-flight dedup always wins regardless of `window_seconds` | Prevents two overlapping triage/remediation runs for the same alert — the dangerous case — independent of how the recency window is tuned |
| Alert `status` (firing/resolved) folded into the Alertmanager fingerprint | A resolve notification must never be suppressed as a duplicate of the firing run it's closing out |
| `trigger.dedup` as a sibling of `trigger.match`, not inside it | Keeps `match` purely about resolver conditions (`_matches()` iterates every key as a field/label comparison) — dedup is an execution-policy concern, not a matching condition |
| `stage` defaults to `testing`, not `production` | New/WIP pipelines are safe by default — nothing pages a real human or counts toward metrics until someone deliberately promotes it |
| `pipeline_runs.stage` persisted per-run, not joined from the live config | Captures stage-at-run-time — promoting a pipeline to `production` never retroactively moves prior testing runs into production metrics |
| `stage` gates four outbound paths individually rather than one flag | `notifications:`, `executor: notify`, `on_failure.webhook`, and `executor: human` are genuinely independent side-effect sources — muting the pipeline as a whole would still need per-path logic, so it's implemented where each one fires |
| No UI toggle for `stage` | Consistent with `tags`/`version` — pipeline behaviour stays entirely git-controlled config, reviewable in a diff |
