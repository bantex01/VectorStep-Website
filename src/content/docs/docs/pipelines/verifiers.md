---
title: Verifiers
description: Adding a second opinion to a step — critic vs independent mode, trigger bands, and how scores combine.
sidebar:
  order: 3
---

A verifier is a second agent call that sanity-checks a step's primary output
before its confidence score is trusted. It fires only if a step declares a
`verifier:` block. For the reasoning behind verifiers — and why a verifier can
never *raise* confidence — see
[How confidence and calibration work](/docs/concepts/confidence/).

## Modes

Two verifier **modes** are available:

| Mode | Behaviour |
|---|---|
| `critic` (default) | Verifier receives the primary agent's prompt, full response, **and a formatted transcript of the primary's own tool calls** (the same trace grounding uses) — it critiques the reasoning *and* can check specific claims ("a ticket was created", "a document was read") against actual evidence rather than just judging plausibility. Its *agreement* correlates with the primary's own errors and carries little signal; its *disagreement* is what's informative. |
| `independent` | Verifier receives only the original task prompt — it executes the same task blind, with no sight of the primary's answer or its trace. Its agreement is uncorrelated with the primary's errors, so it's the stronger corroboration signal — prefer it for steps that authorise a side effect. |

:::note[Renamed from `reviewer`/`challenger`]
Those names still work — parsed as permanent aliases for `critic`/`independent`
respectively — so no existing pipeline needs to change. New pipelines should
prefer the new names; they describe the *role* (correlated critique vs. blind
corroboration) rather than an adversarial framing.
:::

**`verifier.max_trace_chars`** (default 1500, `critic` mode only) caps the
transcript the same way `grounding.max_trace_chars` does — and the same
truncation caveat applies: a claim whose evidence lands past the cutoff is
invisible to the critic, and if the Gateway itself already truncated that tool
result before VectorStep received it (`executor_config.trace_max_chars`), no amount
of raising this setting recovers it. See
[the truncation gotcha](/docs/concepts/confidence/#the-truncation-gotcha-a-real-common-source-of-false-alarms).

## Examples

**Always verify:**

```yaml
verifier:
  executor: openclaw
  executor_config:
    agent: sre-verifier-opus
  mode: critic
  combination_strategy: minimum
  trigger:
    always: true
```

**Band-based — only verify in the uncertain middle ground:**

```yaml
verifier:
  executor: openclaw
  executor_config:
    agent: sre-verifier-opus
  combination_strategy: veto
  veto_floor: 0.60
  trigger:
    confidence_below: 0.95   # skip if primary is clearly confident
    confidence_above: 0.50   # skip if primary is clearly failing
```

The verifier fires only when:
`confidence_above < primary_confidence < confidence_below`.

See `samples/pipelines/trust-vector-remediation.yaml` in the VectorStep repo for
`critic` and `independent` used side by side — cheap corroboration on a step
that only informs, versus blind corroboration on a step that authorises a side
effect.

## Combination strategies

| Strategy | Behaviour |
|---|---|
| `minimum` | `effective = min(primary, verifier)` — both must be confident |
| `veto` | Primary passes through unless verifier < `veto_floor`, in which case the verifier score overrides |

Verifier failures (executor errors) are non-fatal — the runner logs a warning
and falls back to primary confidence only. **The verifier can only ever lower
or hold the primary's effective confidence — never raise it** (`minimum` takes
the lower of the two; `veto` only overrides when the verifier scores *below*
`veto_floor`). This is a permanent invariant, not an emergent property of the
current code — see `_combine_confidence` and its regression test in
`tests/unit/test_confidence.py`.

## Audit trail

**Which agent/model ran the verifier is persisted per-run** —
`pipeline_steps.verifier_agent` (`executor:agent`, mirroring the primary's
`agent` column), `verifier_model`, and `verifier_provider`. This is
deliberately a real column, not something read back out of the *current*
pipeline config at display time — a pipeline's `verifier.executor_config.agent`
can change between when a run executed and when someone looks at it later, and
the audit trail should reflect what actually ran, not what the config happens
to say today.
