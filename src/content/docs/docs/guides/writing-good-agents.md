---
title: Writing good agents
description: Practical principles for scoping, tooling, prompting and versioning an agent well — narrow jobs, minimal tools, honest uncertainty.
sidebar:
  order: 2
---

Nothing in this guide is enforced by the schema — an agent can be as broad,
over-toolstuffed, and self-assured as you write it to be. That's exactly why
it's worth writing down: these are the differences between an agent whose
confidence score is worth gating on and one that's just guessing
confidently. For the mechanical reference — every `agent.yaml` field,
hot reload, startup validation — see [Creating agents](/docs/gateway/agents/).
For the philosophy behind why this matters more than it might seem, see
[How I think about agent design](/blog/how-to-think-about-agents/) on the blog.

## Give it one job

An agent that triages, investigates, *and* remediates is three agents
wearing a trenchcoat — its soul.md has to cover three sets of judgement
calls, its confidence number has to mean three different things depending
on which part of the job it was doing, and calibration ends up averaging
across tasks that don't belong in the same bucket. Split it. The bundled
samples do this deliberately: `first-line-triage` looks up docs and raises a
ticket, `sre-investigation` queries metrics and updates that ticket, and a
separate `principal-sre` agent only ever verifies — each with a soul.md that
describes one job, not three.

## Grant only the tools the job needs

`tools:` in `agent.yaml` is the agent's entire capability surface — nothing
it wasn't listed can reach. Two independent reasons to keep that list
short:

- **Smaller blast radius.** An agent that can only read Confluence and
  raise a Jira ticket cannot accidentally (or under a prompt injection from
  a tool result) do anything more damaging than that, whatever its
  reasoning goes sideways into.
- **Smaller, sharper context.** Every tool's schema is prompt real estate.
  An agent choosing between 4 well-understood tools makes better tool
  choices than one holding 40 "just in case." Scope down to specific tool
  names — `atlassian: [jira_search, jira_get_issue]` rather than the whole
  server — when a server exposes more than the job needs; see [Scoping
  tools](/docs/gateway/agents/#scoping-tools-to-specific-tools).

## Be explicit about the output contract

`confidence`, `summary` and `next_step_context` are mandatory on every
response — see the [LLMOutput contract](/docs/reference/llm-output/). Say so
plainly in the prompt (*"Return ONLY this JSON, no other text"*) and show
the exact shape, including the `reasoning: {supports, contradicts,
assumptions}` convention used throughout the samples — a verifier in
`critic` mode reads that reasoning directly, and a human reading the Trust
panel later relies on it just as much.

## Confidence measures completion, not stakes

The single most common miscalibration: an agent treats a scary alert as
grounds for a low confidence score, or an easy one as grounds for a high
one, regardless of how completely it actually did the job. Say explicitly
in the soul.md what confidence *is* for this agent — usually "how completely
did you gather the evidence / complete the steps I asked for," never "how
severe does this look." An agent that conflates the two poisons its own
[calibration](/docs/pipelines/calibration/) history from the first run.

## Say "I don't know" instead of guessing

A tool call that fails, times out, or returns nothing useful is information
— tell the agent explicitly that this is a low-confidence result to report
honestly, not a gap to paper over with a plausible-sounding guess. This is
the difference [grounding](/docs/pipelines/grounding/) is built to catch:
prose that sounds right versus a claim actually backed by a tool call in
the agent's own trace. An agent whose soul.md rewards honesty about gaps
gives grounding something true to check.

## Match the model to the job, not the biggest one everywhere

A first-line triage step run 200 times a day doesn't need the same model as
a verifier whose entire job is catching the primary's mistakes. Set a
cheaper default in `agent.yaml` and override per-step with
`executor_config.model` where it's worth the spend — and see [cost
accounting](/docs/operations/cost-accounting/) once you want real numbers
behind that choice, not just intuition. The inverse matters too: a
`critic`-mode [verifier](/docs/pipelines/verifiers/) reusing the exact same
model as the primary tends to agree with itself for the same reasons the
primary was wrong — its value goes up with a genuinely different reviewer.

## Treat every edit as a reset

Editing `agent.yaml` or `soul.md` changes the agent's version, which resets
its calibration history in VectorStep — a fact, not a warning to route
around. It means casual, frequent tweaking of a production agent has a real
cost: every edit throws away the track record that made its confidence
number trustworthy in the first place. Batch changes, and prove a reworked
agent on a pipeline still in `stage: testing` before promoting it — see
[Pipeline stages](/docs/concepts/stages/).

## Where next

- **[Writing good prompts](/docs/guides/writing-good-prompts/)** — the same
  treatment for `prompt_template`, the other half of what an agent actually
  sees each run.
- **[Choosing confidence thresholds](/docs/guides/choosing-confidence-thresholds/)**
  — once an agent reports confidence honestly, what number to actually gate
  on.
- **[Using OpenClaw](/docs/guides/using-openclaw/)** — if a step runs on
  `executor: openclaw` instead of `gateway`, several of the mechanisms this
  guide assumes (grounding, trace review) aren't available at all.
- **[Creating agents](/docs/gateway/agents/)** — the full `agent.yaml`
  reference.
- **[Build your first agent](/docs/tutorials/build-your-first-agent/)** —
  put these principles into practice from scratch.
- **[How confidence and calibration work](/docs/concepts/confidence/)** —
  what the number actually means once an agent reports it honestly.
