---
title: "Tutorial: build your first agent"
description: Wire up two MCP servers, write an agent from scratch, and give it a prompt — building on the quick start pipeline, no trust knobs yet.
sidebar:
  order: 1
---

The [quick start](/docs/getting-started/quick-start/) got a pipeline running
end to end, but it borrowed a ready-made agent to do it. This tutorial builds
one from nothing: two real MCP servers, an `agent.yaml` and a `soul.md` you
write yourself, and a prompt that puts both tools to work.

It deliberately turns none of the trust knobs on. That's [the next
tutorial](/docs/tutorials/turn-on-the-knobs/) — this one is just about
getting an agent to do something real and watching it happen.

## What you'll build

A **first-responder** agent that triages the same critical alert from the
quick start, but actually gathers evidence before handing off:

1. Checks [GitHub's public status API](https://www.githubstatus.com/api/v2/summary.json)
   — if the alerting service depends on GitHub (CI, package registry, container
   registry), an upstream incident changes the whole story.
2. Checks a local `known-issues.md` file — has this exact alert already been
   triaged and understood?

Two tools, two MCP servers, zero accounts to sign up for.

## Prerequisites

- The [quick start](/docs/getting-started/quick-start/) completed — Gateway
  and VectorStep both running.
- `npx` (ships with Node.js) and `uvx` (ships with [uv](https://docs.astral.sh/uv/))
  on your `$PATH` — the Gateway spawns MCP servers as subprocesses using
  these.

## 1. Give the filesystem server something to read

MCP's `filesystem` server needs a real directory to scope itself to. Create
one and drop a known-issues log in it:

```bash
mkdir -p ~/vectorstep-tutorial
cat > ~/vectorstep-tutorial/known-issues.md <<'EOF'
# Known issues

- payments-api: intermittent 5xx during the nightly batch export job
  (02:00-02:15 UTC). Not a page — self-resolves within minutes.
EOF

echo ~/vectorstep-tutorial   # note this absolute path — you need it below
```

## 2. Add both MCP servers to the Gateway

In the Gateway's `config.yaml`, add — using the absolute path from above in
place of `/absolute/path/to/vectorstep-tutorial`:

```yaml
mcp_servers:
  fetch:
    command: uvx
    args: ["mcp-server-fetch"]
  filesystem:
    command: npx
    args: ["-y", "@modelcontextprotocol/server-filesystem", "/absolute/path/to/vectorstep-tutorial"]
```

The filesystem server's argument must be an absolute path — it scopes every
file operation to that directory and everything under it, and won't expand
`~` itself.

## 3. Write the agent

Agents live under the Gateway's `agents_dir` (default `./agents/`) — from
the Gateway repo root. The agent below is written narrow on purpose — one
job, two tools, an explicit output contract — following the principles in
[Writing good agents](/docs/guides/writing-good-agents/), worth a read once
this tutorial is done.

```bash
mkdir -p agents/first-responder
```

`agents/first-responder/agent.yaml`:

```yaml
name: first-responder
model: anthropic/claude-sonnet-4-6
max_tokens: 4096
tools:
  - fetch
  - filesystem
```

`agents/first-responder/soul.md`:

```markdown
# First Responder

You are a first-response triage agent for infrastructure alerts. Your job is
narrow: gather two pieces of evidence and hand off a clear brief. You do not
remediate anything, and you do not guess at a root cause you haven't checked
for.

## What you do

1. Use the `fetch` tool to check whether GitHub itself is having an
   incident — relevant if the alerting service depends on it (CI, package
   registry, container registry).
2. Use the `filesystem` tool to read `known-issues.md` and check whether
   this exact alert has already been triaged before.
3. Summarise what you found and hand off.

## Confidence

Confidence measures how completely you gathered the two pieces of evidence
above — not how serious the alert is. Both tool calls succeeded and gave you
a clear answer → confidence should be high. A tool failed, timed out, or gave
you nothing useful → say so honestly and score low, rather than filling the
gap with a plausible-sounding guess.

## Output format

Respond with ONLY the JSON object your prompt asks for. No preamble, no
markdown fences, no commentary outside the JSON.
```

**Restart the Gateway** so it picks up the new `mcp_servers` entries and the
new agent — [hot reload](/docs/gateway/agents/#hot-reload) covers agent
config changes, not new MCP server subprocesses, so a restart is the safe
move here.

## 4. Check the tools actually loaded

```bash
curl http://localhost:18780/mcp/tools
```

You should see tool entries under both `fetch` and `filesystem`. If a server
is missing, check the Gateway's startup logs — a bad `command`/`args` fails
loudly there.

## 5. Wire the pipeline to your new agent

The quick start's `pipelines/alert-triage.yaml` already triggers on
`severity: critical` and pulls its step from the step library (`use:
first-line-triage`). Rather than add a second pipeline that would collide
with the same trigger match — pipeline resolution is first-match-wins, so
the two would race — **replace that file's contents** to point at your new
agent with an inline step instead of the library one:

```yaml
name: alert-triage
description: First-responder agent gathers evidence before anyone escalates
trigger:
  source: alertmanager
  match: { severity: critical }

steps:
  - name: triage
    executor: gateway
    executor_config:
      agent: first-responder
      session_key: "agent:first-responder:{{pipeline_run_id}}:triage"
    prompt_template: |
      A {{severity}} alert fired for {{labels.service}} in {{labels.environment}}.
      Summary: {{summary}}

      1. Use the fetch tool to check https://www.githubstatus.com/api/v2/summary.json
         for any active GitHub incident.
      2. Use the filesystem tool to read known-issues.md and check whether an
         entry already matches this alert.

      Return ONLY this JSON, no other text:
      {
        "confidence": 0.0,
        "summary": "One sentence: what's happening and what you found",
        "next_step_context": "",
        "upstream_incident": true,
        "known_issue": true,
        "reasoning": {
          "supports": "Evidence that makes this alert credible",
          "contradicts": "Evidence that suggests noise or a known cause",
          "assumptions": "What you're assuming in the absence of data"
        }
      }
```

`confidence`, `summary` and `next_step_context` are the three mandatory
fields every agent response must include — see [the LLMOutput
contract](/docs/reference/llm-output/) — `next_step_context` can be an empty
string for a terminal step like this one, but it has to be present or the
response fails validation. Everything else in the JSON above
(`upstream_incident`, `known_issue`) is a free-form extra field, stored and
available to any later step as `{{steps.triage.upstream_incident}}`.

Notice what's *not* here: no `confidence_threshold`, no `on_low_confidence`,
no verifier. This is rung 0 on [the trust ladder](/docs/tutorials/adding-trust/)
— a fully working pipeline with no gating at all, which is a legitimate place
to stop for a step that only informs rather than acts.

Reload the service:

```bash
curl -X POST http://localhost:8000/reload
```

## 6. Trigger it

Reuse the same fixture from the quick start — the point of this tutorial is
the agent, not a new trigger:

```bash
curl -X POST "http://localhost:8000/webhook?source=alertmanager" \
  -H "Content-Type: application/json" \
  -d @tests/fixtures/alertmanager_critical.json
```

## 7. Watch it run

Open the run in **http://localhost:8000/ui/** and look at the step's trace.
You should see two real tool calls — `fetch` hitting GitHub's status API and
`filesystem` reading `known-issues.md` — plus the agent's JSON response
built from what they returned, not from what the model assumed.

That trace is exactly what [grounding](/docs/pipelines/grounding/) checks
later: not whether the output *sounds* right, but whether it's backed by a
real tool call in the agent's own trace.

## Where next

- **[Writing good agents](/docs/guides/writing-good-agents/)** — the
  principles behind the agent you just wrote: narrow scope, minimal tools,
  honest uncertainty, and why each of those matters more than it looks like
  it should.
- **[Writing good prompts](/docs/guides/writing-good-prompts/)** — the same
  treatment for the `prompt_template` you just wrote, including the
  soul.md-vs-prompt split and the `{{steps.x.y}}` hyphen gotcha.
- **[Turn on the trust knobs](/docs/tutorials/turn-on-the-knobs/)** —
  take this exact pipeline and add a confidence floor and a verifier.
- **[Adding trust, one signal at a time](/docs/tutorials/adding-trust/)**
  — the full ladder this tutorial and the next one are climbing.
- **[Creating agents](/docs/gateway/agents/)** — the full `agent.yaml`
  reference, including scoping `tools:` to specific tool names and model
  fallbacks.
