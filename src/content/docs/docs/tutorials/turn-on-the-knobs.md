---
title: "Tutorial: turn on the trust knobs"
description: Take the pipeline from the previous tutorial and add a confidence floor, then a verifier — rungs 1 and 2 of the trust ladder, hands-on.
sidebar:
  order: 2
---

[Build your first agent](/docs/tutorials/build-your-first-agent/) got
`alert-triage` running your own `first-responder` agent with no gating at
all — rung 0 on [the trust ladder](/docs/guides/adding-trust/). This
tutorial climbs two rungs on that exact pipeline: a confidence floor, then a
second opinion.

## 1. Add a confidence floor

Edit the `triage` step in `pipelines/alert-triage.yaml`:

```yaml
steps:
  - name: triage
    executor: gateway
    executor_config:
      agent: first-responder
      session_key: "agent:first-responder:{{pipeline_run_id}}:triage"
    confidence_threshold: 0.70
    on_low_confidence: escalate
    prompt_template: |
      ...
```

Reload and re-trigger it exactly as before:

```bash
curl -X POST http://localhost:8000/reload
curl -X POST "http://localhost:8000/webhook?source=alertmanager" \
  -H "Content-Type: application/json" \
  -d @tests/fixtures/alertmanager_critical.json
```

Both tools should still succeed, so the agent reports high confidence and the
run completes exactly as before — `confidence_threshold` only changes
behaviour when the bar isn't cleared. See [how confidence and calibration
work](/docs/concepts/confidence/) for what the number means before you rely
on it.

### See it actually gate

Break one of the tools on purpose to see the other side of the threshold.
Rename the known-issues file so the read fails:

```bash
mv ~/vectorstep-tutorial/known-issues.md ~/vectorstep-tutorial/known-issues.md.bak
```

Re-trigger the same webhook. The agent should now report low confidence
honestly (per its own `soul.md`: *"a tool failed ... say so honestly and
score low"*), the step should come back below the 0.70 threshold, and the
run's status should show `escalated` instead of `completed` — a human
reviews it instead of the pipeline proceeding on a guess. Check the Trust
panel on the run to see the exact number and why it didn't clear the bar.

Restore the file when you're done:

```bash
mv ~/vectorstep-tutorial/known-issues.md.bak ~/vectorstep-tutorial/known-issues.md
```

## 2. Add a second opinion

A confidence floor only checks the agent's own number. A verifier adds a
second agent call that sanity-checks the primary response before that number
is trusted — and it can only lower confidence, never raise it. See
[Verifiers](/docs/pipelines/verifiers/) for the full mode/combination
reference; this tutorial uses the defaults.

Add a `verifier:` block to the same step:

```yaml
steps:
  - name: triage
    executor: gateway
    executor_config:
      agent: first-responder
      session_key: "agent:first-responder:{{pipeline_run_id}}:triage"
    confidence_threshold: 0.70
    on_low_confidence: escalate
    prompt_template: |
      ...
    verifier:
      executor: gateway
      executor_config:
        agent: first-responder
        session_key: "agent:first-responder:{{pipeline_run_id}}:triage-verify"
      combination_strategy: minimum
      trigger:
        always: true
```

This reuses the same `first-responder` agent for the verifier, just with a
different `session_key` — enough to see the mechanism work with nothing new
to write. In `critic` mode (the default), the verifier gets the primary's
full response plus a transcript of its tool calls, and critiques the
reasoning rather than re-running the task blind.

:::note[In production, verify with a different model]
A verifier reusing the exact same agent config will tend to agree with
itself for the same reasons it made the original call — its *disagreement*
is the informative signal, and that's more likely from a differently-tuned
reviewer. The one-line change is `executor_config.model` on the verifier
block: `model: anthropic/claude-opus-4-6`, for example, overrides just that
call without touching the agent's own default. For a step that authorises a
side effect rather than just informing, prefer `mode: independent` instead
of the `critic` default — see [Verifiers](/docs/pipelines/verifiers/) for
why.
:::

Reload and re-trigger again. The run's Trust panel now shows both numbers —
primary and verifier — and which one the `minimum` strategy picked. Audit
columns (`verifier_agent`, `verifier_model`) record which agent actually ran
the verification on that specific run, independent of whatever the config
says today.

## Where next

You've climbed rungs 1 and 2. Rung 3 (grounding) has its own hands-on
tutorial next; deterministic checks, calibration, and readiness follow the
same additive pattern and are documented, but not yet as click-by-click
tutorials:

- **[Adding trust, one signal at a time](/docs/guides/adding-trust/)**
  — the full ladder, and when climbing further is (and isn't) worth it.
- **[Calibration](/docs/pipelines/calibration/)** — once this step has real
  run history, check whether its "90% confident" has actually meant 90%.

Next in the series: **[Turn on grounding](/docs/tutorials/turning-on-grounding/)**,
then fan-out, artifacts, notifications, budget, metrics, and finally
[promoting it to production](/docs/tutorials/promoting-to-production/).
