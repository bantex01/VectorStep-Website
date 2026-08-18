---
title: "Tutorial: promote your pipeline to production"
description: "Placeholder outline — the capstone tutorial. Take the pipeline built across this whole series from stage: testing to stage: production, on real evidence."
sidebar:
  order: 9
---

[PLACEHOLDER — outline only, not a full walkthrough yet.]

Every tutorial in this series has run `pipelines/alert-triage.yaml` in
`stage: testing` — the default — without saying so explicitly. This
capstone tutorial makes that visible, then walks through actually earning
and executing the promotion to `stage: production`, using
[readiness](/docs/concepts/readiness/) evidence rather than a gut call.

## What this builds on

The full `pipelines/alert-triage.yaml` as left at the end of whichever
prior tutorials you've done — the more of the series behind it (confidence
threshold, verifier, fan-out, notifications), the more interesting its
accumulated run history is for this one.

## Outline

1. Make the testing-stage behaviour concrete first: re-trigger the
   pipeline and point out exactly what's being suppressed right now — the
   `notification_suppressed_testing` log line if [the notifications
   tutorial](/docs/tutorials/routing-notifications/) was done, the
   `TESTING` badge on the run in the UI — versus what's genuinely
   unaffected (the trust-gating mechanics from Tutorial 2 behave
   identically in either stage).
2. Generate enough run history to have something to evaluate — several
   more triggers, marking a few outcomes via the run detail page's
   accuracy feedback so `accuracy`/`calibration` tiers have real labels to
   work with, not just `insufficient_data`.
3. Open the pipeline detail page's **Promotion readiness** card and read
   the "Observed (service defaults)" fallback — this pipeline has no
   `readiness:` block yet, so this is what evidence looks like before you
   set a bar.
4. Use the **criteria builder** to turn a couple of knobs (start with
   `operational.min_runs` and `confidence.min_confidence`) and watch the
   ~300ms preview update against the real accumulated evidence, then copy
   the generated YAML into the pipeline file.
5. Call out the two classic misreadings explicitly while they're on
   screen: `calibration.n_min` is per confidence band, not a total; adding
   a status to `acceptable_statuses` makes the bar *laxer*, not stricter.
6. Flip `stage: production`, `POST /reload`, and re-trigger — confirm the
   `TESTING` badge is gone and (if wired) a real notification actually
   fires this time.
7. Close the loop back to readiness being advisory: promotion was still a
   one-line YAML edit reviewed like any other config change — the tooling
   informed the decision, it never gated the edit itself.

## Where next

- **[Promotion readiness](/docs/concepts/readiness/)** — the full tier
  reference (operational/confidence/accuracy/calibration) and every
  readiness knob.
- **[Testing vs production stages](/docs/concepts/stages/)** — exactly
  what stage gates and what it doesn't.
- **[Marking queue](/docs/ui/marking-queue/)** — finding every step still
  missing a human accuracy mark before its tiers can resolve.
