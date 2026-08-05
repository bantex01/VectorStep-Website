---
title: Marking queue
description: The cross-pipeline queue of steps still waiting on a human accuracy mark.
sidebar:
  order: 4
---

`/ui/marking-queue` is a cross-pipeline review queue of steps with no **human** accuracy feedback yet, grouped by pipeline then step, oldest first, with pipeline/team/stage (default `testing`) additive filters and stat cards (pipelines/runs/steps affected, marked coverage %). It links out to `/ui/runs/{id}` to actually mark; nothing is markable from this page itself.

## Why this page exists

Every knob on the accuracy and calibration tiers ultimately needs marked evidence to resolve against, and `accuracy.min_human_marked` specifically needs a *human* to have graded the step directly — not an inherited run-level rating, and not a deterministic check's automatic label. Finding what still needs a human mark used to mean opening each pipeline's Accuracy feedback page one at a time; the Marking queue is a single cross-pipeline view of it instead.

## What it lists

It lists every step with no `StepFeedback` (i.e. `human_marked` would not count it), grouped by pipeline then by step (fan-out/parallel branches collapse to their group name, same as everywhere else in the readiness system), oldest first. A step that already has an *automatic* label — a failed deterministic check, or an inherited run-level rating — is still listed, but tagged with where that label came from, since neither one satisfies `min_human_marked`. Stat cards at the top give the shape of the backlog (pipelines affected, runs affected, steps unmarked, and marked-coverage %); filters for pipeline, team, and stage are additive.

**Stage defaults to `testing`** — the pre-promotion review case — but is a real, selectable filter, not a hard scope: a `stage: production` pipeline using calibration on its own merits (independently of any `stage: testing → production` gate) needs its backlog visible here too, so `production` and "all stages" are both one click away.

**Nothing can be marked from this page.** Every row links out to the run on `/ui/runs/{id}`, where the existing accuracy feedback widget (run-level and per-step) does the actual marking — the queue is a finder, not a second place feedback gets written.

## Relationship to the confidence system

The marking queue is one of several places confidence and calibration make themselves visible in the UI — for the readiness-criteria and calibration angle on this same underlying data (why marked evidence matters, how `min_human_marked` and the calibration bins use it), see [How confidence and calibration work — Where to actually see all of this](/docs/concepts/confidence/#where-to-actually-see-all-of-this).
