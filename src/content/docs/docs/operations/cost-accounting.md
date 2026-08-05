---
title: Cost accounting
description: Converting tracked tokens into money — the pricing table, budget.max_usd, team budgets, and optional live/approximate OpenRouter pricing.
sidebar:
  order: 5
---

VectorStep tracks tokens end-to-end (see [Team attribution](/docs/operations/teams/)),
but tokens aren't money. This page covers converting them, using a pricing
table the operator maintains.

**VectorStep never bundles a price list or fetches prices from a provider by
default.** Provider pricing changes often, differs by contract (Azure PTUs,
OpenRouter markups, enterprise discounts), and a stale bundled table produces
confidently wrong dollar figures — worse than no number at all. The mechanism
ships; the operator owns the numbers. (An optional, clearly-labeled
*approximate* pricing source is available — see
[Live/approximate pricing](#liveapproximate-pricing-optional) below — but it's
opt-in and never the source of the real, persisted cost.)

## The pricing table

```yaml
pricing:
  currency: USD                  # display label only — no FX conversion anywhere
  models:
    # example — verify against your provider's current pricing before relying on this
    - match: {provider: anthropic, model: "claude-sonnet-4-6"}
      input_per_mtok: 3.00        # currency units per 1,000,000 input tokens
      output_per_mtok: 15.00
    - match: {provider: anthropic, model: "claude-haiku"}   # prefix match
      input_per_mtok: 1.00
      output_per_mtok: 5.00
    - match: {provider: openrouter}                          # provider-only fallback
      input_per_mtok: 2.00
      output_per_mtok: 8.00
  team_budgets:                  # optional — advisory only, see below
    payments: 500
    platform: 1000
```

**Resolution** is longest-prefix match, scoped by provider first: filter
entries whose `match.provider` equals the step's persisted `provider` (or has
no provider constraint), then the entry with the longest `match.model` that
prefixes the step's model string wins. A provider-only entry (no `model` key)
is the fallback for that provider if no model prefix matched.

:::note[NULL vs. zero]
No match at all → cost is `NULL` — **never `0`**. `0` means "priced, and this
genuinely costs nothing" (e.g. a local Ollama model an operator explicitly
rates at 0); `NULL` means "not priced" (unknown). Every surface that sums cost
keeps this distinction — a SUM skips NULLs, and reports how many steps it
skipped as a separate "unpriced steps: N" count rather than silently
understating spend as if the total were complete.
:::

## When cost is computed

Once, at step-save time, from whatever rate was in force at that moment —
never recomputed later from the current table. Pricing changes apply going
forward only; historical cost reflects what the tokens actually cost when
they were bought. `POST /reload`/SIGHUP re-reads the pricing table for future
steps; already-persisted costs never change.

## Verifier and grounding-judge tokens are priced too

A trust feature that hid its own cost would undermine the point of the
feature. Verifier tokens (`verifier_input_tokens`/`verifier_output_tokens`,
priced against `verifier_model`/`verifier_provider` — see
[Verifiers](/docs/pipelines/verifiers/)) and grounding-judge tokens
(`grounding_input_tokens`/`grounding_output_tokens`, priced against
`grounding_model`/`grounding_provider` — see
[Grounding](/docs/pipelines/grounding/)) are both folded into the step's
`cost` alongside the primary call. Grounding is shadow-mode/advisory (gated
only by `enforce: true`), but it still spends real tokens against a real
model, so it's priced the same way.

If a component that actually ran (primary, verifier, or grounding) has no
rate match for its model/provider, the step's `cost` is `NULL` rather than a
silently partial sum — a grounding-only pipeline with an unpriced judge model
doesn't get to look cheaper than it is. A `grounding:` block that never fired
(no trace to check, or the call errored) contributes nothing at all, same as
a step with no verifier configured.

## Budget guardrail

`budget.max_usd` works exactly like `budget.max_tokens` (see
[Pipeline schema](/docs/pipelines/schema/)): the runner accumulates persisted
`cost` per completed step and aborts the run with `status=aborted` if the
total exceeds the ceiling. Unpriced steps contribute `0` to this accumulator,
same as other-executor steps contribute `0` tokens. At least one of
`max_tokens`/`max_usd` is required if `budget:` is present at all; both may
be set together (whichever trips first aborts the run and names which limit
it was).

```yaml
budget:
  max_tokens: 50000
  max_usd: 5.00                  # abort run if accumulated cost across all steps exceeds this
```

## Team budgets

`pricing.team_budgets` sets a per-team currency-units-per-calendar-month
(UTC) figure, surfaced on `/ui/insights/teams` as a spend-vs-budget bar and
the `vectorstep_team_budget_ratio{team}` gauge (month-to-date spend /
budget).

:::caution[Advisory only, never enforcing]
Going over it never blocks a run — enforcement stays per-pipeline via
`budget.max_usd`. Blocking a critical-alert triage because a calendar month
rolled over would be the wrong failure mode for an ops tool.
:::

## Where cost shows up

- **Run detail** — per-step and run-total cost, with a 4-decimal sub-cent
  display when a step's cost rounds to $0.00 at the normal 2 decimals. See
  [Run detail](/docs/ui/run-detail/).
- **Insights** — pipelines/teams/models/providers pages all carry a cost
  column/card alongside tokens. See [Insights](/docs/ui/insights/).
- **`/stats/*` JSON endpoints** — same rollup functions as the UI, so they
  can't disagree. See [Analytics API](/docs/reference/analytics-api/).
- **Prometheus** — `vectorstep_pipeline_cost_total{pipeline, team, model,
  provider}`, a counter in `pricing.currency`'s units. See
  [Observability](/docs/operations/observability/).

Display formatting is `$12.34` for USD, `12.34 EUR` otherwise, always via one
template helper.

## Live/approximate pricing (optional)

Everything above is manual-only by design — but a step with no
`pricing.models` entry can optionally get a best-effort *approximation* from
OpenRouter's public model catalog (`GET
https://openrouter.ai/api/v1/models`, no auth required):

```yaml
pricing:
  live_pricing:
    enabled: true
    refresh_interval_seconds: 3600   # how often the catalog is re-fetched
```

This is a genuinely different kind of number from everything above, and is
never allowed to be confused with it:

- **Never persisted, never the real `cost` column.** `pipeline_steps.cost`
  stays exactly as described above — NULL when unpriced, computed once from
  the manual table. The approximation is computed fresh at display time (or,
  for the budget accumulator, once at run time) against whatever catalog
  snapshot happens to be cached — it drifts as OpenRouter's prices change,
  which is the opposite of the "historical cost never changes" guarantee
  real `cost` has.
- **Fuzzy-matched, best-effort, and says so.** OpenRouter's catalog uses its
  own `<vendor>/<slug>` ids (`anthropic/claude-3.5-sonnet`), which won't
  exactly match the raw `(provider, model)` strings recorded from a direct
  API call (`anthropic` / `claude-sonnet-4-6`). Matching is scoped to entries
  whose vendor plausibly matches `provider`, then picks the closest
  model-name overlap (ignoring version digits, so `claude-sonnet-4-6` can
  still find `claude-3.5-sonnet`) — and returns nothing rather than a weak
  guess if it isn't confident. There's no guarantee the matched model is
  even the same version, let alone under the same contract/pricing terms
  you actually have.
- **Colored, not blended.** Wherever a real cost exists, that's all that's
  shown (green). Where it doesn't, an approximation is shown in **amber**
  with a hover explaining it's a cross-provider guess — *unless* the step's
  `provider` genuinely is `openrouter`, in which case the live catalog price
  is the real rate for the exact API that was called (just not manually
  entered), shown in **green** too. A standalone **"Live reference
  pricing"** panel on the Insights Overview page lists every distinct model
  in use that could be matched, with the same disclaimer, refreshed on its
  own schedule.
- **Budget-accumulator opt-in only, off by default.**
  `budget.include_approx_cost: true` (in the pipeline's `budget:` block)
  lets an unpriced step's approximation fill the gap in the `max_usd`
  accumulator instead of contributing `0` — an individual step can override
  the pipeline's default via its own `include_approx_cost: true|false`. An
  estimate can't abort a run (or count toward a team's month-to-date
  spend/budget-ratio) unless explicitly opted into; the teams page
  separately notes month-to-date approximate spend for unpriced steps,
  clearly marked as not counted toward the real spend/budget figures next
  to it.
- **Its own Prometheus metric.** `vectorstep_pipeline_approx_cost_total` is a
  *separate* counter from `vectorstep_pipeline_cost_total` — never a label
  on the real one, so a dashboard reading the real metric alone can never
  accidentally include an estimate.

## Out of scope

FX conversion; price history tables (persisted cost *is* the history);
run-blocking team quotas; Gateway-side pricing (VectorStep is the system of
record for spend); live pricing from any source other than OpenRouter's
public catalog.
