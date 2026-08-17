---
title: Grounding keeps flagging real evidence as unsupported
description: Three independent truncation points can each produce the same false "unsupported" symptom — how to tell which one is cutting you off, and how to fix it.
sidebar:
  order: 1
---

**Symptom:** [grounding](/docs/pipelines/grounding/) marks a claim as
unsupported even though you're confident the agent actually did the work —
or a grounding call fails to parse at all. In both cases the cause is almost
always truncation, not a hallucinating agent or a broken judge. There are
**three independent places** something can get cut short, and they produce
two different-looking symptoms depending on which one it is.

## The three truncation points

```
primary agent's tool call
  → Gateway captures the tool_result           [1] limits.trace_tool_result_max_chars (default 3000)
  → VectorStep formats it into the judge's prompt   [2] grounding.max_trace_chars (default 1500)
  → grounding-judge agent generates its verdict [3] the judge agent's own max_tokens
```

**[1] and [2] truncate the judge's *input*** — the evidence it's shown.
**[3] truncates the judge's *output*** — its own response. Both produce
symptoms that look like "grounding is wrong," but they need different
fixes.

## Symptom A: a claim you know is true shows up "unsupported"

This is truncated input — [1] or [2], or both.

- **[2] `grounding.max_trace_chars`** (default 1500, set per-step in the
  `grounding:` block) controls how much of the trace VectorStep hands to the
  judge, *of what VectorStep already has*.
- **[1] `limits.trace_tool_result_max_chars`** (default 3000, in the
  **Gateway's** `config.yaml`, overridable per-step via the primary step's
  `executor_config.trace_max_chars`) caps each tool result *before VectorStep
  ever receives it*.

**Raising [2] alone is not enough if [1] already cut the evidence.** If the
Gateway truncated a tool result at 3000 characters, no amount of raising
`grounding.max_trace_chars` recovers the missing part — it was never sent.
Raise both together:

```yaml
steps:
  - name: investigate
    executor: gateway
    executor_config:
      agent: sre-investigation
      trace_max_chars: 8000        # [1] the Gateway-side cap, for this step
    grounding:
      agent: grounding-judge
      max_trace_chars: 8000        # [2] match it — same number, both layers
```

Reassuringly, **neither cutoff affects what the agent itself sees** — the
primary agent always gets the full, untruncated tool output when it's
actually doing the work. Only what gets *recorded and shown to the judge
afterwards* is capped, so this is purely a review-accuracy problem, never a
capability one.

`verifier.max_trace_chars` (default 1500, `critic` mode only) is the exact
same pattern for a verifier instead of the grounding judge — same fix, same
"raise the Gateway-side cap too" caveat.

## Symptom B: the grounding call fails to parse, not just scores low

This is truncated output — [3], and it looks different from Symptom A. The
judge is asked to return a per-claim list (`reasoning.claims`, one entry per
load-bearing claim) as part of its JSON response. A step with many claims
can produce a per-claim list long enough that the judge's own response gets
cut off mid-generation by its **`max_tokens`** — at which point the response
isn't valid JSON at all, and the grounding call fails to parse rather than
returning a low score.

**Fix:** raise `max_tokens` on the `grounding-judge` agent's `agent.yaml`
(on the Gateway) — this is a normal [agent config
field](/docs/gateway/agents/), nothing grounding-specific about it. If
you're not sure this is actually what's happening:

**How to tell [3] apart from [1]/[2]:** check
`trust_report.grounding.raw_output` on the run — it carries the judge's
exact, untruncated reply text, for both a clean parse and a parse failure.
If it cuts off mid-sentence or mid-JSON-object, that's [3]. If it's a
complete, valid response that simply says a claim is unsupported, that's
[1] or [2] — the judge answered honestly based on what it was shown, and
what it was shown was incomplete. The run-detail page surfaces this
directly: the grounding claims section's **Answer** disclosure shows this
same raw text without digging into the API response.

## If you're not sure where to start

Raise all three together for the step in question — `executor_config.trace_max_chars`,
`grounding.max_trace_chars`, and the `grounding-judge` agent's `max_tokens`
— re-run, and check `raw_output`. It's cheap to over-provision these for a
step whose tools return long content (a full document read, a large query
result); the defaults are tuned for short, cheap evidence, not for every
step in the pipeline.

## Where next

- **[Grounding](/docs/pipelines/grounding/)** — the full config reference,
  including the exact `grounding-judge` agent contract.
- **[How confidence and calibration work](/docs/concepts/confidence/)** —
  the trust-vector explanation this truncation behaviour is a footnote to.
- **[Writing good agents](/docs/guides/writing-good-agents/)** — general
  agent-design guidance, including tool scoping that affects how much a
  step's trace contains in the first place.
