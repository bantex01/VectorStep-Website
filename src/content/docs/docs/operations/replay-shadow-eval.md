---
title: Replay / shadow evaluation
description: Prove a candidate model, agent, or prompt change is safe to promote before running it in production traffic.
sidebar:
  order: 7
---

VectorStep already records everything needed to answer *"is this prompt/model/agent
change safe to promote?"* — per-step rendered prompts and outputs, `prompt_hash` +
`agent_version` bucketing (see [Confidence](/docs/concepts/confidence/)), human/
deterministic outcome labels with a defined precedence, and
[promotion-readiness criteria](/docs/concepts/readiness/). But editing a prompt
resets its calibration bucket by design, and the only way to earn evidence for the
*new* configuration was previously to run it forward in real traffic and wait for
marked outcomes to accumulate.

Replay closes that loop: take the most recent labelled step executions from an
existing bucket, execute a **candidate** configuration (a different model, agent,
and/or prompt) against the same recorded inputs, auto-grade what can be
auto-graded, queue the rest for human marking, and show a side-by-side report —
recorded config vs. candidate — an owner can use to decide on promotion.

## The safety gate: `replay.safe_agents`

Replay executes real agent calls against live tools. That's the point — a mocked
tool layer would grade the candidate on stale fiction — and the danger, since a
side-effecting agent (one that files tickets, pages people, mutates state) could
re-fire actions it already fired once when it was recorded.

```yaml
replay:
  safe_agents:
    - "gateway:sre-investigation"
    - "openclaw:incident-triage"
```

`safe_agents` is an explicit allowlist of `"executor:agent"` identities the
operator asserts are read-only. A replay request is rejected with `403` unless
**both** the recorded step's agent and the candidate's agent appear here — even
if only the model is changing, the recorded agent still has to be on the list.
No `replay:` block (or an empty `safe_agents`) means replay is off entirely;
every request 403s pointing back at this config key.

## Two modes

**`rendered`** — resend the recorded step's exact rendered prompt to the
candidate model/agent, verbatim. Valid when the candidate changes **model
and/or agent only**, not the prompt template. Requires the executor that
produced the recorded sample to have persisted the actual rendered prompt text
(the `gateway` and `openclaw` executors both do, via `raw_response["prompt"]`);
a sample recorded before that persistence existed, or by an executor that
doesn't stash it, is reported as `unreplayable` rather than guessed at.

**`rerender`** — render the **candidate's prompt template** against the
recorded step's reconstructed Jinja context (the same `{{steps.*}}`,
`{{labels.*}}`, `{{vars}}` a production run would have seen). Required whenever
the prompt template itself is changing. If context reconstruction fails for a
sample — the owning pipeline is no longer loaded, a prior step's persisted
output doesn't parse, an artifact has aged out of retention — that sample is
marked `unreplayable`, never silently dropped from the report.

## Sample selection

A batch samples the **most recent K labelled executions** of the source
bucket, `stage: production` only (default K=20, hard cap 100). "Labelled"
means the same label-precedence chain [Confidence](/docs/concepts/confidence/)
uses everywhere else: a human step mark, else a deterministic-check failure,
else a run-level fallback — never an unlabelled row. The bucket itself is
either an explicit selector (agent, model, provider, prompt_hash,
agent_version) or `"current"`, which resolves to whatever bucket the step's
single most recent production execution actually landed in.

The report's recorded-accuracy figure is exactly this sample set's existing
numbers — the same bucket [Calibration](/docs/pipelines/calibration/) would
report for it, not a separate recomputation.

## Grading the candidate

- **Deterministic checks** declared on the step run automatically against the
  candidate's output. Same asymmetry as production: a **failure** auto-labels
  the candidate `0.0` (a strong, computer-verified negative signal); a
  **pass** proves nothing on its own and leaves the sample unmarked.
- Everything else goes to the [marking queue](/docs/ui/marking-queue/), where
  replay-produced steps are flagged `REPLAY`, and a human marks them exactly
  like a production step.
- The report **recomputes live** on every request — there's no persisted
  report artifact, so a mark submitted a moment ago is already reflected.
- **No LLM auto-judge.** Judging "is the candidate's answer as good as the
  recorded-correct answer" with a model needs its own grounding/trust
  treatment and is deliberately out of scope for now — shipping human-marked
  replay first keeps the evidence honest.
- **Verifier and grounding never fire during replay.** The candidate runs
  bare — primary call only — so the comparison isolates the one variable
  under test, and it's cheaper.

## Where the results live

A replay batch is stored as an ordinary pipeline run: one synthetic run per
batch, `stage: testing`, with a `replay_of` descriptor recording the source
bucket, the candidate, the mode, and which recorded samples map to which
candidate step executions. Its steps carry the **candidate's**
`prompt_hash`/`agent_version` — so if the candidate is later promoted, these
replay-produced marks stay `stage: testing` and are excluded from the new
production bucket. That's intentional: replay evidence informs the promotion
*decision*, it doesn't pre-seed the production track record. Production trust
is still only earned in production — see
[Testing vs production stages](/docs/concepts/stages/) for why that boundary
exists and what else it protects.

Because it's an ordinary `stage: testing` run, every metric/aggregate surface
that already excludes testing traffic excludes a replay batch automatically —
no new exclusion logic anywhere. It shows up in browse surfaces (the runs
list, the marking queue) with the usual `TESTING` badge, and Prometheus
exposes it specifically as `vectorstep_replay_batches_total` and
`vectorstep_replay_steps_total{grade}` (grade: `completed`,
`deterministic_failed`, `execution_failed`, `unreplayable`) — see
[Observability](/docs/operations/observability/).

## API

```bash
# Launch a batch — blocks until every sample has been attempted
POST /steps/{step_name}/replay
# body: {
#   "bucket": "current",                          # or {agent, model, provider, prompt_hash, agent_version}
#   "candidate": {"model": "...", "agent": "...", "prompt_template": "..."},  # any subset
#   "mode": "rendered" | "rerender",
#   "k": 20                                        # optional, default 20, max 100
# }
# → {"status": "completed", "run_id": "<synthetic-run-id>"}

# Recomputed live on every call — reflects marks as they arrive
GET /replays/{run_id}/report
# → {
#     step_name, mode, source_bucket, candidate, k,
#     recorded_distribution: {correct, partial, incorrect},
#     recorded_accuracy, candidate_accuracy_so_far,
#     candidate_graded_n, candidate_total_n, unreplayable_count,
#     confidence_distribution: [...],
#     rows: [{sample_step_id, recorded_label, recorded_label_source,
#             status, candidate_step_id, candidate_confidence,
#             candidate_summary, deterministic_passed, mark_outcome,
#             candidate_label?, candidate_label_source?}, ...]
#   }
```

## Concurrency

Fixed at 3 concurrent candidate executions per batch — sequential is too slow
at K=20, unbounded risks hammering a provider. Not configurable.

## UI

Minimal by design: a "Replay against candidate…" link on the
[step insights page](/docs/ui/insights/) opens a plain form
(`/ui/replays/new?step=...`) for the candidate model/agent/prompt/mode/K; on
submit it blocks until the batch finishes and lands on the report page
(`/ui/replays/{run_id}`). Marking a replay-produced step happens on the
ordinary run detail page, same widget as any other step.

## What replay is not

- It doesn't replay whole pipelines — one step at a time, by design (isolates
  the variable under test).
- It doesn't run on a schedule — every batch is operator-triggered.
- It doesn't preview cost before launching.
- It doesn't grade with an LLM judge.

These are deliberate Phase 1 boundaries, not oversights — each would need its
own design (particularly the LLM judge, which needs the same grounding/trust
treatment everything else in [Confidence](/docs/concepts/confidence/) gets)
before it's worth building.

## Related

- [Confidence](/docs/concepts/confidence/) — "Proving a change before
  promotion" ties replay directly to the S/V/G/D formula and calibration
  bucketing this feature reuses.
- [Promotion readiness](/docs/concepts/readiness/) — the criteria a replay
  batch's evidence ultimately feeds a decision about.
- [Marking queue](/docs/ui/marking-queue/) — where replay-produced steps
  needing a human mark show up, flagged `REPLAY`.
- [Testing vs production stages](/docs/concepts/stages/) — why a replay
  batch stays `stage: testing` even after the candidate it tested gets
  promoted.
