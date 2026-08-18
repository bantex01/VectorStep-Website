---
title: Choosing readiness criteria
description: "Placeholder outline — what tiers and numbers to actually put in a readiness: block, not just what each knob does."
sidebar:
  order: 6
---

[PLACEHOLDER — outline only, not full prose yet.]

[Promotion readiness](/docs/concepts/readiness/) documents what every tier
and knob *does*, exhaustively. This guide is meant to be its
[Choosing confidence thresholds](/docs/guides/choosing-confidence-thresholds/)
companion — the opinionated "what do I actually set" complement, aimed at
someone standing in front of [the promotion
tutorial](/docs/tutorials/promoting-to-production/)'s criteria builder with
sixteen knobs and no instinct yet for which four matter for this pipeline.

## Planned sections

1. **Start with `operational` alone, always.** It's the only tier a
   non-LLM step (`webhook`/`notify`/`human`/`pipeline` executor) can ever
   satisfy, and it can never report `fail` — it's the cheapest possible bar
   and a reasonable one on its own for a low-stakes step.
2. **Add `accuracy` before `calibration`, not instead of it.** Calibration
   is the strongest signal but the slowest to earn (needs `n_min` per
   *band*, not total) — accuracy with a real `min_human_marked` floor is a
   faster, still-meaningful bar while calibration history accumulates.
3. **`confidence` alone is close to worthless as a gate** — tie this
   directly back to [why self-report is the least trustworthy
   signal](/docs/concepts/confidence/#s--the-self-report); a bar that only
   checks "did it claim confidence" doesn't check whether it should have.
4. **The two misreadings that make a "stricter-looking" config weaker**
   deserve their own worked example, not just a warning: `n_min` per band
   vs total with real numbers, and an `acceptable_statuses` list that grew
   to look thorough but actually loosened the bar.
5. **Match the tier set to the step's actual risk**, echoing [Choosing
   confidence thresholds](/docs/guides/choosing-confidence-thresholds/)'s
   core argument — a step that only informs doesn't need the same bar as
   one that authorises a side effect, and `readiness: null` is a legitimate
   choice for a step where no bar makes sense (a `notify` step, say).
6. **Use `require_own_evidence`/`require_current_config` deliberately**,
   not at their defaults by habit — when a shared step's track record from
   elsewhere should or shouldn't count, and when a prompt tweak should
   force tiers back to `insufficient_data` rather than quietly carry old
   evidence forward.

## Where next

- **[Promotion readiness](/docs/concepts/readiness/)** — the full
  mechanical reference this guide will assume throughout.
- **[Promote your pipeline to production](/docs/tutorials/promoting-to-production/)**
  — the hands-on companion this guide is meant to prepare you for.
