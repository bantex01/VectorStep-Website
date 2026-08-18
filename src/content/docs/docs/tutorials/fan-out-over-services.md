---
title: "Tutorial: fan out over multiple services"
description: Placeholder outline — check every upstream dependency dynamically instead of just GitHub, using fan_out.
sidebar:
  order: 4
---

[PLACEHOLDER — outline only, not a full walkthrough yet.]

Tutorials 1–2 had `first-responder` check exactly one upstream dependency
(GitHub's status API), hardcoded in the prompt. Real services depend on
several upstreams at once. This tutorial turns that one hardcoded check into
a dynamic [`fan_out`](/docs/pipelines/parallel/#fan-out--dynamic-parallelism)
over however many the alert actually implicates — one branch per upstream,
run concurrently, joined back into a single effective confidence before the
existing threshold/verifier from Tutorial 2 apply.

## What this builds on

`pipelines/alert-triage.yaml`'s `triage` step, as left at the end of [Turn
on grounding](/docs/tutorials/turning-on-grounding/) — confidence
threshold, verifier, and (if that tutorial was done) grounding, already in
place.

:::caution[Grounding doesn't carry into the fan-out]
Grounding is not yet wired into `parallel`/`fan_out` branches — sequential
steps only. If the previous tutorial left `grounding:` on `triage`, turning
that same step into a `fan_out:` here means grounding simply won't run on
any branch — no error, just not there. Worth knowing before you go looking
for a Trust panel widget that isn't going to appear.
:::

## Outline

1. Add a small `identify-upstreams` step ahead of `triage` that returns a
   JSON list of upstream names to check (start with a hardcoded list to
   keep it simple — `["github", "npm"]` — rather than an agent inferring it,
   so the fan-out mechanics are the focus, not the list-generation).
2. Replace the single `triage` step with a `fan_out:` entry — `over:
   "{{ steps.identify_upstreams.upstreams }}"`, `as: upstream`, one branch
   per upstream, each hitting that upstream's own public status endpoint via
   the same `fetch` tool from Tutorial 1.
3. Pick a join strategy — `all_must_pass` reads naturally here ("don't
   proceed confidently if any upstream check failed"); show what
   `any_must_pass` would mean instead, and when you'd want it.
4. Add a `consolidate` step downstream that reads branch outputs via
   bracket notation (`{{ steps['triage-upstreams/0'].summary }}`) and
   produces the final triage summary.
5. Trigger it, and in the run detail page look at each fan-out branch as
   its own row — same Trust panel per branch as any sequential step gets.
6. Note the `max_items`/`on_empty` guardrails and why they exist (a
   misbehaving list-producing step shouldn't be able to spawn unbounded
   branches or silently do nothing).

## Where next

- **[Parallel groups & fan-out](/docs/pipelines/parallel/)** — full
  reference, including static `parallel:` groups for a fixed branch set
  (this tutorial only covers the dynamic case).

Next in the series: **[Store a full investigation as an
artifact](/docs/tutorials/storing-artifacts/)**.
