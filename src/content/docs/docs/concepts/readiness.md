---
title: Promotion readiness
description: Owner-defined criteria a pipeline must earn before promotion from testing to production.
sidebar:
  order: 4
---

Pipelines start life as `stage: testing` and are promoted to `production` by
their owner. Readiness is the evidence-based readout that tells you whether a
pipeline has *earned* that promotion — evaluated per step across four
independent tiers (**operational**, **confidence**, **accuracy**,
**calibration**) against the pipeline's own accumulated run history. It is
advisory: it never blocks a promotion, it tells you exactly what the evidence
says.

A guided, preview-only **criteria builder** on the pipeline detail page lets
you turn knobs and see within ~300ms what they would say about the evidence,
then copy a ready-to-paste YAML snippet.

## Promotion readiness (owner-defined criteria)

The calibration loop described in [Confidence](/docs/concepts/confidence/) is
deliberately production-scoped — correct for the live gate
(`calibration: {enforce: true}`), but calibration is also the strictest,
slowest-to-earn signal there is, and it was previously the *only* readiness
criterion that existed, hardcoded (`n_min: 20`, `bin_width: 0.1`, a 15-point
divergence flag). A pipeline owner who just wants "twenty clean runs" had no
way to say so; one who wanted a stricter divergence threshold had no way to
say that either.

`readiness:` lets the owner define the bar instead, on a ladder from *nothing*
(today's default: promote freely, no criteria, no gate) through progressively
stronger evidence up to full calibration. It is settable at the pipeline level
(a house default for every step) and per step (add to or override the house
default) — a step pulled from the shared step library is *owned by the
pipeline that uses it*, so its bar is settable at the point of use.

**Four independent, additive tiers.** Every *configured* tier must pass for a
step to be "ready"; an unconfigured tier is not a failure, it is simply not
asked — an owner can require `operational` + `accuracy` without touching
`calibration`, because they answer genuinely different questions:

| Tier | Answers | Cheapest signal? |
|---|---|---|
| `operational` | Did it run cleanly? | Yes — pure `PipelineStep.status` counting. The only tier a non-LLM step (`webhook`/`notify`/`human`/`pipeline` executor) can ever satisfy, since those never write `effective_confidence`. Can only ever report `pass` or `insufficient_data` — never `fail`. |
| `confidence` | Does it claim confidence? | Mean self-reported `effective_confidence`. Weak alone — the model can be confidently wrong. |
| `accuracy` | Are its outputs actually good? | Judged accuracy (correct=1.0, partial=0.5, incorrect=0.0) over human/deterministic/run-level labels. |
| `calibration` | Is its confidence number trustworthy? | The strongest bar — reuses the calibration bucket machinery from [Confidence](/docs/concepts/confidence/), with every previously-hardcoded constant now owner-settable. |

**Strictly advisory — no automated gate, ever.** Promoting a pipeline stays
exactly the [testing-vs-production workflow](/docs/concepts/stages/#promotion-workflow):
a one-line `stage:` edit in YAML, `POST /reload`, reviewed in git like any
other config change. This readout doesn't intercept that edit, add a UI
toggle, or block `/reload`/SIGHUP. A team that wants an automated CI block can
script one against the JSON endpoint below; building that automation isn't
part of this feature.

**Evidence follows the pipeline's own stage.** A `stage: testing` pipeline is
measured against its testing runs; a `stage: production` pipeline against its
production runs (`evidence_stage` in the response) — this makes the readout
an ongoing "are my criteria currently met" health check in either stage, not
only a promotion-moment check.

**Merge: tiers merge, tier contents replace.** The pipeline sets a house
standard; a step *adds* tiers to it or *replaces* an individual tier wholesale
(never field-by-field — a step's `accuracy:` block is always exactly what's
written for that step). Explicit `null` on a tier removes an inherited one
(`readiness: {calibration: null}`); `readiness: null` on the whole block opts
a step out entirely. **Documented wart:** a step pulled via `use:` from the
step library is, after loading, indistinguishable from a step whose
`readiness:` was written directly in the pipeline YAML — so when the library
step and the pipeline-level block configure the *same* tier, the library
step's value wins the conflict. The worst case under tier-level merging is
still a union of tiers (strictly stricter), never a silent replacement of the
whole block.

**`require_current_config`** (default `true` on `accuracy`/`calibration`,
`false` on `operational`/`confidence`) filters evidence to runs matching the
pipeline's *current* `prompt_template` and the step's most recently observed
`agent_version`. Editing a step's prompt therefore drops its
accuracy/calibration tiers to `insufficient_data` immediately — with an
explicit note naming how many earlier marked results were excluded, never a
silent zero — while `operational`'s default (`false`) means a typo fix
doesn't wipe out 30 clean runs. `calibration.require_current_config` cannot be
set `false`: a calibration bucket is keyed by `(prompt_hash, agent_version)`
by definition.

**`calibration.require_own_evidence`** (default `false`) lets a shared
library step's *production* track record from a different pipeline count,
when agent/model/prompt/agent version all match exactly — the response names
which pipeline(s) contributed (`production_pipelines`) so an owner's green
tick is never mysteriously "someone else's traffic." `true` restricts a step
to only its own pipeline's evidence. Overriding `prompt_template` locally on a
`use:` step changes the prompt hash and silently forfeits inherited evidence
either way — a real trap worth knowing about.

**The single most misread knob: `calibration.n_min` is per confidence band,
not a total.** A step with 100 marked results spread evenly across 10 bands
has only 10 in each, and will not validate at `n_min: 20`. Look at the
fullest band's own count, never `total_n`.

**`acceptable_statuses` is laxer, not stricter, the more you add.**
`[completed, escalated]` accepts runs where a human had to step in — a
*weaker* claim than `[completed]` alone, even though the longer list reads
like a higher bar.

A pipeline with **no** `readiness:` block anywhere behaves exactly as before —
`criteria_source: "none"`, no verdict asserted — but the readout still shows
each step's observed calibration evidence (at the endpoint's
`bin_width`/`n_min` defaults), so a real signal never disappears behind a
config chore.

No new DB column or migration, no new Prometheus metric — everything is
recomputed fresh from `pipeline_steps`/`step_feedback`/`run_feedback`/`pipeline_runs`
on every request.

### YAML examples

Minimal — operational only, pipeline-wide:

```yaml
readiness:
  operational:
    min_runs: 20                      # 20 runs of this step...
    acceptable_statuses: [completed]  # ...that all ended `completed`
```

House default plus a stricter step, an opt-out, and a parallel group:

```yaml
readiness:                            # house standard for every step
  operational:
    min_runs: 20
    acceptable_statuses: [completed, escalated]
    max_age_days: 30
  confidence:
    min_confidence: 0.80
    min_runs: 10

steps:
  - name: investigate                 # inherits the house standard verbatim
    executor: gateway
    ...

  - name: apply-fix                   # house standard PLUS accuracy PLUS calibration
    executor: gateway
    readiness:
      accuracy:
        min_accuracy: 0.90
        min_marked: 30
        min_human_marked: 15          # at least 15 by a real human, not automation
      calibration:
        n_min: 30                     # PER BAND, not total
        max_divergence: 0.10          # stricter than the 0.15 default
        require_own_evidence: true

  - name: notify-oncall                # no bar makes sense for a notify step
    executor: notify
    readiness: null

  - parallel:                          # readiness lives INSIDE `parallel:`
      name: cross-checks
      readiness:
        operational: {min_runs: 50}
        confidence: null              # drop the inherited confidence tier
      steps: [...]
```

See `samples/pipelines/promotion-readiness-criteria.yaml` for a complete
worked example hitting all sixteen knobs across all four tiers, including
both traps above.

The pipeline detail page (`/ui/pipelines/{name}`) shows a "Promotion
readiness" card for `stage: testing` pipelines, with per-step tier chips, a
"How is this judged?" disclosure carrying a plain-language narrative and
label provenance, and an "Observed (service defaults)" fallback for steps
with no criteria configured. `GET /pipelines/{name}/promotion-readiness` (see
[API reference](/docs/reference/api/)) exposes the same data as JSON for
either stage; `POST .../preview` evaluates a *candidate* config against the
same evidence without writing anything.

## Criteria builder (guided UI)

Authoring `readiness:` by hand from a README is a lot of surface for knobs
this counter-intuitive — `n_min` being per band, `acceptable_statuses` being
laxer the more you add, and the rest. The "Build criteria" button on the
Promotion readiness card (or clicking any `—` tier chip on a step) opens a
builder card below it: turn a knob, see within ~300ms what that bar would say
about the evidence already accumulated for this pipeline, read the same
plain-language help text as above, and copy a ready-to-paste YAML snippet.

**It is preview-only and writes nothing.** There is no save button and no
write endpoint call — the builder is a thin client over `POST .../preview`
(the same read-only endpoint described above), which validates the candidate
config through the real `ReadinessConfig` and hands back generated YAML. You
paste the snippet into the pipeline's YAML file yourself and ship it through
the normal `POST /reload` + git review workflow (see
[Testing vs production stages](/docs/concepts/stages/)) — the builder never
touches the file on disk, and VectorStep's git-controlled-config posture is
unchanged.

For finding steps that still need a human accuracy mark before their
`accuracy`/`calibration` tiers can resolve, see the
[Marking queue](/docs/ui/marking-queue/).

## Quick-reference: readiness knobs

| Knob | Where | Default | Effect |
|---|---|---|---|
| `readiness.operational.min_runs` | pipeline or step `readiness:` | required | Distinct runs (never rows) that must end in an acceptable status. Can only ever be `pass`/`insufficient_data` — never `fail`. |
| `readiness.operational.acceptable_statuses` | pipeline or step `readiness:` | `[completed]` | End-states that count. Adding a status makes the bar LAXER, not stricter — `[completed, escalated]` is weaker than `[completed]` alone. |
| `readiness.operational.max_age_days` | pipeline or step `readiness:` | `null` (lifetime) | Restricts `operational` to runs from the last N days. The only readiness tier with a time window. |
| `readiness.operational.require_current_config` | pipeline or step `readiness:` | `false` | `true` filters to runs matching the current prompt/agent version. |
| `readiness.confidence.min_confidence` | pipeline or step `readiness:` | required | Minimum mean self-reported `effective_confidence` over qualifying runs. |
| `readiness.confidence.min_runs` | pipeline or step `readiness:` | `null` | Minimum sample size before `min_confidence` is trusted — strongly recommended. |
| `readiness.accuracy.min_accuracy` | pipeline or step `readiness:` | required | Minimum weighted judged accuracy (correct=1.0, partial=0.5, incorrect=0.0). |
| `readiness.accuracy.min_marked` | pipeline or step `readiness:` | required | Minimum labelled results before `min_accuracy` is evaluated. |
| `readiness.accuracy.min_human_marked` | pipeline or step `readiness:` | `null` | Minimum labels from a HUMAN specifically — guards against a labelled population that's 100% failed deterministic checks reading as 0% accurate. |
| `readiness.calibration.n_min` | pipeline or step `readiness:` | `20` | Marked outcomes needed AT THE SAME CONFIDENCE BAND — per band, not a total. The single most misread readiness knob. |
| `readiness.calibration.bin_width` | pipeline or step `readiness:` | `0.1` | Must evenly divide 1.0 — rejected at config load, not at request time, if it doesn't. |
| `readiness.calibration.max_divergence` | pipeline or step `readiness:` | `0.15` | Owner-settable version of the hardcoded 15-point divergence flag. |
| `readiness.calibration.require_own_evidence` | pipeline or step `readiness:` | `false` | `true` restricts calibration to this pipeline's own runs, excluding a shared library step's production track record from elsewhere. |
| `readiness.calibration.require_current_config` | pipeline or step `readiness:` | `true`, cannot be `false` | A calibration bucket is keyed by `(prompt_hash, agent_version)` by definition — "ignore the version" would mean merging buckets. |

**Safety property:** adding a `readiness:` block never resets a calibration
bucket — `prompt_hash` is computed from `prompt_template` **text only**, so
`readiness:` (which lives alongside, not inside, the prompt) can't touch it.
