---
title: Using OpenClaw
description: You can point a step at executor:openclaw instead of the VectorStep Gateway — here's exactly what that trades away, so it's a deliberate choice, not a surprise.
sidebar:
  order: 4
---

`executor: openclaw` is a first-class, fully supported executor — if you
already run [OpenClaw](https://github.com/openclaw/openclaw) and don't want
to stand up a second gateway just to try VectorStep, you can point steps at
it directly, and mix `openclaw` and `gateway` steps freely in the same
pipeline. This guide is deliberately weighted toward what you give up by
doing that, because it's easy to reach for the executor you already have
running and not notice what silently stops working until you go looking for
data that was never recorded.

## Minimal setup

```yaml
steps:
  - name: triage
    executor: openclaw
    executor_config:
      agent: sre-triage        # an agent name OpenClaw already knows about
    confidence_threshold: 0.75
    on_low_confidence: escalate
    prompt_template: |
      ...
```

VectorStep authenticates to OpenClaw's Gateway using the Ed25519 device
identity files OpenClaw itself creates (`~/.openclaw/identity/`) — nothing
to author on VectorStep's side beyond the step config above. See
[Executors](/docs/integrations/executors/#openclaw--openclaw-gateway-websocket)
for the full `executor_config`/service-config reference, including the
remote-OpenClaw setup (copying identity files across machines).

## What still works exactly the same

Worth stating plainly, because the rest of this page is a list of gaps: the
core trust-gating mechanics **do not depend on which executor ran the
step**. Self-report confidence (S) and `confidence_threshold` gating,
[deterministic checks](/docs/pipelines/grounding/#deterministic-checks-d)
(evaluated by the runner directly, no LLM or executor involved),
[calibration](/docs/pipelines/calibration/)'s bin-and-measure mechanism,
`independent`-mode [verifiers](/docs/pipelines/verifiers/) (which redo the
task blind — they never needed the primary's trace), human-in-the-loop
approvals, notifications, and sub-pipeline composition all work identically
regardless of executor. The gap is specifically in the **evidence layer** —
everything that depends on VectorStep actually seeing what happened inside
the agent's own turn.

## What you don't get

### No trace, full stop

`pipeline_steps.agent_trace` — the ordered record of tool calls, tool
results, and thinking blocks — is `NULL` for every `openclaw` step. OpenClaw
does not expose intermediate events to VectorStep; only the final result
comes back. This one fact is the root cause of most of what follows.

### Grounding cannot run — and it fails silently, not loudly

[Grounding](/docs/pipelines/grounding/) only runs for `executor: gateway`
steps, because it cross-references claims against exactly the trace that
doesn't exist for OpenClaw. This isn't a degraded version of grounding on an
openclaw step — it's not attempted at all, and `grounding_score` stays
`NULL` forever.

**The footgun:** declaring `grounding: { enforce: true }` on an `executor:
openclaw` step is not a validation error. It just never does anything. The
gate formula only applies the grounding ceiling `if G is not None` — G is
always `None` here, so the enforce block sits in your YAML looking like a
real safety gate while contributing exactly nothing, indefinitely. If you
mix executors in one pipeline, double-check that `grounding.enforce` only
appears on the `gateway` steps.

### A `critic`-mode verifier loses its actual edge

A `critic`-mode [verifier](/docs/pipelines/verifiers/)'s value comes from
seeing "the primary's full response **and a formatted transcript of its own
tool calls**" — that's what lets it check specific claims against evidence
rather than just judge whether the prose sounds plausible. With no trace to
show it, a critic verifying an openclaw step's output degrades toward
judging the answer on its face — closer to a second read-through than a real
cross-check. `independent` mode is unaffected (it never looks at the
primary's trace either way), which is one more reason to prefer
`independent` for anything that authorises a side effect, openclaw or not.

### No cost or token accounting

The `openclaw` executor doesn't report token counts, so it's excluded
entirely from `vectorstep_pipeline_tokens_total` and every cost rollup — not
padded as zero, just absent. A team running mostly `openclaw` steps has
genuinely undercounted spend in [team
attribution](/docs/operations/teams/) and [cost
accounting](/docs/operations/cost-accounting/), not an approximate figure.

### No per-model or per-tool analytics

`/ui/insights/models` "has no data for OpenClaw-executed steps, since only
the gateway executor records a model per step" — you can't compare model
performance for anything routed through OpenClaw. `/ui/insights/mcp` is the
same story for tool usage: OpenClaw steps don't expose intermediate events,
so they contribute nothing to tool-level call/error breakdowns.

### No trace to watch or review, live or after the fact

The run-detail page's live tool-call tail and its after-the-fact trace
review — the exact thing [Build your first
agent](/docs/tutorials/build-your-first-agent/) has you watch to confirm
your agent actually called its tools — depends on `agent_trace`. For an
`openclaw` step it's `NULL`, so there's nothing to watch or replay. You get
the final JSON response and nothing about how the agent got there.

### No distributed tracing

OTel trace propagation into VectorStep's own trace is supported for the
`gateway` executor and not for `openclaw` — an openclaw step's LLM/tool
activity won't join the same trace as the rest of the pipeline run in
whatever tracing backend you're using.

### Calibration's version-reset safety net doesn't apply

`agent_version` — the content hash that makes editing a Gateway agent's
`soul.md` correctly start a fresh calibration bucket — is explicitly
**Gateway-owned**: VectorStep computes it from the Gateway's own agent
config. VectorStep has no equivalent visibility into an OpenClaw agent's
configuration, so it has no way to know when one changes. This is exactly
the bug that agent-version tracking was built to close for Gateway
agents — see [Editing a prompt or an agent resets the measurement — deliberately](/docs/concepts/confidence/#editing-a-prompt-or-an-agent-resets-the-measurement--deliberately)
— and it remains open for OpenClaw agents: edit one on the OpenClaw side,
and VectorStep will keep blending outcomes from the old and new
configuration into the same calibration bucket without telling you.

## Mixing is the point, not a compromise

None of this means avoid `executor: openclaw` — it means use it where the
gap doesn't matter and reach for `gateway` where it does. A step that only
needs S plus a `confidence_threshold`, or one gated entirely by a
deterministic check, loses nothing meaningful by running on OpenClaw. A step
whose whole job is producing an auditable trail for a side-effecting
action — the kind of step this product exists for — needs the trace, which
means it needs `executor: gateway`. Executors are a per-step choice for
exactly this reason.

## The discipline travels even if you stay on OpenClaw

Nothing above is really an argument against OpenClaw as a tool — it's an
argument about what VectorStep specifically can and can't see once a step
runs there. The underlying discipline — one job per agent, only the tools
it actually needs, an honest confidence signal instead of a plausible-sounding
one — isn't a production-only concern that stops mattering on a personal
setup. A raw OpenClaw agent scoped and prompted the way [Writing good
agents](/docs/guides/writing-good-agents/) describes will just work
better — more predictably, more legibly when it's wrong — than the same job
handed to one broad, every-tool-granted agent, whether or not VectorStep is
anywhere in the picture. See [How I think about agent
design](/blog/how-to-think-about-agents/) for more on why that's true even
when nothing you're running is customer-facing.

## Where next

- **[Gateway overview](/docs/gateway/overview/)** — why the VectorStep
  Gateway exists as an alternative, and what it adds beyond trace
  visibility (multiple LLM providers, configurable MCP servers).
- **[Executors](/docs/integrations/executors/)** — the full executor
  reference, including the OpenClaw/Gateway differences table.
- **[Grounding](/docs/pipelines/grounding/)** — the trace-dependent
  mechanism at the center of most of the gaps above.
