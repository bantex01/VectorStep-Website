---
title: "Tutorial: gate a pipeline on budget"
description: Placeholder outline — price your steps and set budget.max_usd so a runaway pipeline aborts on cost, not just on confidence.
sidebar:
  order: 7
---

[PLACEHOLDER — outline only, not a full walkthrough yet.]

Everything gated so far has been about whether to trust an answer. This
tutorial gates on something completely different: whether the pipeline is
getting too expensive to keep running, using
[`budget.max_usd`](/docs/operations/cost-accounting/#budget-guardrail) —
independent of confidence, deliberately.

## What this builds on

`pipelines/alert-triage.yaml` from the series so far — adds a `budget:`
block at the pipeline level and a pricing table at the service level. No
change to the `triage` step itself.

## Outline

1. Add a minimal `pricing:` table to the service's `config.yaml` covering
   whatever model `first-responder` actually uses (`anthropic/claude-sonnet-4-6`
   from Tutorial 1) — `input_per_mtok`/`output_per_mtok`. Note the `NULL`
   vs `0` distinction up front: an unpriced step's cost is `NULL`, not
   free.
2. Trigger the pipeline once normally and look at the run detail page's
   per-step cost figure — confirm it's a real, priced number now, not
   blank.
3. Add `budget: { max_usd: <something deliberately tiny> }` to the
   pipeline and trigger again to force an abort — watch the run come back
   `status=aborted` naming which limit tripped, rather than completing.
4. Raise the budget to something realistic and confirm normal operation
   resumes — the point being budget is a ceiling, not a target.
5. Point at where the same number rolls up: Insights' cost columns, the
   Prometheus `vectorstep_pipeline_cost_total` counter, and (if a
   `pricing.team_budgets` entry exists) the advisory team-budget bar on
   `/ui/insights/teams` — advisory only, never enforcing, unlike
   `budget.max_usd`.
6. Briefly mention live/approximate OpenRouter pricing as an opt-in
   alternative to hand-maintaining the table, and why it's never the real
   persisted `cost`.

## Where next

- **[Cost accounting](/docs/operations/cost-accounting/)** — the full
  pricing/budget reference, including verifier and grounding-judge tokens
  being priced too.
- **[Team attribution](/docs/operations/teams/)** — where cost rolls up by
  team, and the `openclaw` executor's token-reporting gap mentioned in
  [Using OpenClaw](/docs/guides/using-openclaw/).

Next in the series: **[Metrics and traces in
Grafana](/docs/tutorials/metrics-and-tracing-in-grafana/)**, then the
capstone — [promoting your pipeline to
production](/docs/tutorials/promoting-to-production/).
