---
title: Calibration
description: Technical reference for calibration buckets, binning, labelling, and the enforce/on_uncalibrated knobs.
sidebar:
  order: 7
---

Calibration checks whether a step's reported confidence actually means what it
claims, empirically, using this exact system's own history. For the
plain-language explanation of why this exists, see
[How confidence and calibration work](/docs/concepts/confidence/). This page
is the technical/config reference: bucketing, labelling, binning, and the
`calibration:` block's knobs.

## Calibration (Phase 3)

Every step execution's `effective_confidence` has been persisted since Phase
0, and per-step/per-run human feedback (`step_feedback`/`run_feedback`) plus
deterministic-check failures (Phase 1) have been accumulating. Phase 3
finally checks whether the *number* means what it claims: does a step that
reports 0.75 confidence in a specific `(step × agent × model × provider)`
configuration actually turn out correct roughly 75% of the time?

**Bucketing.** Marked step-executions are grouped by `(step_name, agent,
model, provider, prompt_hash, agent_version)` — a `library step` (see
[Extending VectorStep](/docs/design/extending/)) used across five pipelines feeds
**one** bucket instead of five, and changing one step's model resets only
that step's bucket. Fan-out branches (`step_name` like `triage/0`,
`triage/1`) collapse into their parent step's bucket rather than one bucket
per branch index. `prompt_hash`/`agent_version` mean editing a step's prompt
template, or editing a Gateway agent's `agent.yaml`/`soul.md`, also starts a
fresh bucket — see
[How confidence and calibration work](/docs/concepts/confidence/) for the
full explanation and what you'll see in the UI when it happens.

**Label precedence, per step-execution:**

1. **Human** — a resolved `StepFeedback` row for that step execution
   (`correct → 1.0`, `partial → 0.5`, `incorrect → 0.0`) — authoritative when
   present.
2. **Deterministic (D)** — `pipeline_steps.deterministic_passed == False`
   labels the step `0.0`, for free, at scale. A *passing* check is **not**
   used as a positive label on its own — only failure is a strong-enough
   automated signal.
3. **Run-level fallback** — the enclosing run's `RunFeedback.outcome`, used
   only when neither of the above exists for that step execution.
4. Otherwise the step-execution is **excluded** entirely — not counted as a
   0, not counted toward `N`.

**Binning, not curve-fitting.** Rather than isotonic/Platt regression (which
would pull in `scipy`/`sklearn`, a dependency this service otherwise has zero
of), calibration uses simple fixed-width bins — default width 0.1 (10 bins
across `[0, 1]`) — and reports each bin's sample count and mean label. This is
directly interpretable and matches the exact language calibration
recommendations use: *"runs scoring ~70% in this configuration are only 50%
correct (40 runs)."* A bin needs `n_min` (default 20) marked outcomes before
it's considered **validated**; nothing computed from an unvalidated bin is
used to gate anything.

:::note[Advisory by default, no opt-in required]
`/ui/insights/steps` shows every bucket's calibration bins and, for any
validated bin whose predicted score and observed accuracy diverge by 15
points or more, a recommendation string — with no `calibration:` config on
any step. Nothing here changes a run's outcome; it's a report the human can
inspect and act on, exactly the same "tool informs, human governs" posture as
the accuracy pages already have.
:::

## Enforcing (opt-in per step, never silent)

A step can opt its *gate* into using the bucket's empirical accuracy instead
of the raw self-report/verifier number:

```yaml
- name: investigate
  executor: gateway
  executor_config: { agent: sre-investigation }
  confidence_threshold: 0.75
  calibration:
    enforce: true
    on_uncalibrated: proceed   # or "escalate" — see below
```

When enforced and the step's bucket/bin is validated, `combined_trust` is
**replaced** with the bin's `mean_label` before grounding's `min()` and
deterministic checks' force-zero apply on top — the *same*
`confidence_threshold` then decides `on_low_confidence`, no new threshold
config. The `TrustReport`'s `calibration` block always shows the arithmetic:
raw score, calibrated score, bin, `n`/`n_min`, so a calibrated escalation is
never a mysterious abort.

When the bucket/bin has **not** yet accumulated `n_min` marked outcomes,
`on_uncalibrated` decides the posture:

- **`proceed`** (default) — `combined_trust` is left as the raw
  `effective_confidence`, unchanged; the run behaves exactly as it would with
  no `calibration:` block. The `TrustReport` still records "not yet
  validated, N=x/N_min" for transparency.
- **`escalate`** — forces `combined_trust = 0.0`, driving the step's
  *existing* `on_low_confidence` action. An explicit "no track record → a
  human checks" policy for high-blast-radius steps; not imposed as a
  universal default.

A step with **no** `calibration:` block is unaffected by any of this — same
posture as Phase 1's core invariant (see
[Grounding](/docs/pipelines/grounding/)).

**No persisted calibration curve.** Calibration is still computed fresh from
`pipeline_steps`/`step_feedback`/`run_feedback` on every request, the same
way the Insights pages already recompute their rollups — there's no fitted
curve to migrate or invalidate. Prompt-versioning did add two columns to
`pipeline_steps` — `prompt_hash`, `agent_version` — plus two small
content-addressed registry tables that hold the recoverable text behind those
hashes.

See `samples/pipelines/trust-vector-remediation.yaml` for a complete worked
example combining `critic`/`independent` verifier modes, enforced grounding,
deterministic checks, and calibration into a single trust-vector gate on a
side-effecting step.

## Where next

- **[How confidence and calibration work](/docs/concepts/confidence/)** — the
  plain-language walkthrough, including the worked five-step example and the
  full knob quick-reference table.
- **[Promotion readiness](/docs/concepts/readiness/)** — owner-defined
  criteria, including calibration-based readiness tiers, for promoting a
  pipeline out of `stage: testing`.
- **[Grounding](/docs/pipelines/grounding/)** — the signal that caps
  `combined_trust` after calibration replaces the raw score.
