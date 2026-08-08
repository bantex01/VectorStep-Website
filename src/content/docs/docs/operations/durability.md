---
title: Durability & resume
description: Resuming in-flight pipeline runs after a restart instead of losing them, opt-in per pipeline.
sidebar:
  order: 6
---

Pipeline runs execute as fire-and-forget in-process tasks. Before this feature, if
the service process died or restarted mid-run — a deploy, a crash, an OOM kill —
every in-flight run was lost: the startup sweep stamped every `status="running"`
row as `interrupted`, even if four of five steps had already completed, and even
if the run was an escalated triage a human was waiting to approve.

For an ops-automation service, that's a real production-credibility gap: a
routine deploy shouldn't kill every investigation in flight. Durability closes
it — opt-in, per pipeline.

## Opt-in

```yaml
durable: true   # shorthand for {on_interrupted: rerun}
```

or the block form, to pick the conservative policy explained below:

```yaml
durable:
  on_interrupted: escalate
  max_resume_age_seconds: 1800   # optional — overrides the service-wide default
```

A pipeline with no `durable:` field behaves exactly as before: a restart marks
it `interrupted`, full stop. This is deliberate — resume changes side-effect
semantics (see the warning below), so the pipeline author has to opt in.

## What actually resumes

**Resume happens at step boundaries only.** A step whose output is already
persisted is never re-executed — its saved output is loaded and the prompt
context for later steps is rebuilt from it exactly as if the run had never
stopped, including any extra fields a step returned (`{{steps.*}}` references
resolve identically). The step that was **in flight** at crash time is
indeterminate — its agent call may or may not have fired a side effect before
the process died — and that step is where `durable.on_interrupted` applies:

- **`rerun`** (default) — re-execute the in-flight step from scratch. This is
  the right default because agent calls are the overwhelmingly common step
  type, and re-running a triage or investigation is safe.
- **`escalate`** — do not re-execute; mark the step `escalated` and drive its
  existing `on_low_confidence`/notification path so a human decides. Use this
  for a step that fires a real side effect (a ticket, a remediation action,
  anything not idempotent) — re-running it blind could double-fire it.

**A parallel group or fan-out with only some branches persisted resumes just
the missing branches**, then re-joins using the full set (persisted +
freshly executed) — a branch that already completed is never re-run. For
`on_interrupted: escalate`, this generalizes the same way: only the *missing*
branches are treated as escalate-worthy; a group that turns out to have been
fully complete before the crash just proceeds normally, since nothing about it
was actually interrupted.

**A step using `executor: human` resumes as *waiting*, not re-executed** — a
pending approval already delivered to Telegram/Slack/Teams before the crash
survives it. The approval buttons already in the human's chat still work after
restart; resume re-registers the same token's wait rather than sending a new
request. This applies to a top-level `human` step; a `human` step living
inside a parallel branch or fan-out isn't re-armed today and is re-executed
fresh (sending a new approval request) if it was in flight — a known scope
limitation.

**Loop steps (`loop_until`) resume like any other step.** A refinement loop's
iteration state never crosses a step boundary — only the final iteration's
output is ever persisted or referenced by later steps — so `on_interrupted:
rerun` simply restarts the loop cleanly at iteration 1, and `escalate` skips
it entirely. There's no unresumable "stuck mid-loop" state to detect.

**The token/cost budget accumulator counts pre-restart usage.** A run that had
already spent most of `budget.max_usd` or `budget.max_tokens` before the crash
carries that spend into the resumed run rather than getting a fresh budget on
top of it.

## The config-fingerprint guard

Every run — durable or not — is stamped at trigger time with a fingerprint of
the pipeline's step sequence (name, executor, agent per step). At resume time,
that fingerprint is compared against the pipeline's *current* config. A
mismatch means the pipeline changed while the run was down — a step added,
removed, reordered, or pointed at a different agent — and the run is marked
`interrupted` instead of resumed, with a `resume_skipped_config_changed`
run-log event. Replaying half a run under different semantics would poison
calibration/accuracy data, which depends on every step in a run having
executed under one consistent config.

Resumed steps carry the same `prompt_hash`/`agent_version` bucketing as any
other step, so calibration itself is unaffected by a resume — the
config-fingerprint guard is what makes that true, by refusing to resume across
a config change in the first place.

## The age window

```yaml
durability:
  max_resume_age_seconds: 3600   # service-wide default; a pipeline's own
                                  # durable.max_resume_age_seconds overrides it
```

A run down longer than this is marked `interrupted`, not resumed — resuming a
six-hour-old triage of a long-resolved alert is worse than dropping it.
Defaults to one hour, configurable service-wide in `config.yaml` or per
pipeline.

## Scope: single replica

This makes a *single* VectorStep process durable across its own restarts. It
is not multi-replica work distribution or a shared job queue — the startup
sweep is inherently single-replica ("any `running` row belongs to me"). A
future queue-based design would supersede it for multi-replica deployments;
that's out of scope here.

## Observability

Every resume is loudly audited — an operator should never have to wonder
whether a run's steps executed in one process or two:

- A `run_resumed` run-log event, with the number of steps/branches skipped and
  the `on_interrupted` policy applied.
- A `WARNING`-level log line per resumed run.
- The `vectorstep_runs_resumed_total` Prometheus counter, labeled by pipeline
  (see [Observability](/docs/operations/observability/)).

## A warning worth repeating

`on_interrupted: rerun` on a side-effecting step can double-fire that side
effect — the step may have already fired before the crash, and resume can't
know that. Use `escalate` for any step whose action isn't safe to repeat
(ticket creation, a remediation script, anything with an external effect). A
worked example — triage (durable, `rerun`) feeding a remediation step
(durable, `escalate`) — is in
`samples/pipelines/durable-remediation-example.yaml` in the engine repo.

## Related

- [Flow control](/docs/pipelines/flow-control/) for `when:`, retries, and the
  other step-level control-flow fields `durable` sits alongside.
- [Run storage](/docs/operations/runs/) for what actually gets persisted per
  step, which is what resume reconstructs from.
