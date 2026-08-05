---
title: Grounding
description: Checking whether an agent's claims are actually backed by evidence in its own trace, plus deterministic checks and enforced grounding.
sidebar:
  order: 6
---

Grounding fact-checks a step's output against its own execution trace: for every
load-bearing claim the agent made, is there a tool call or tool result in its
trace that actually backs it up? For the plain-language explanation of how
grounding (G) fits into the overall trust vector alongside self-report (S) and
the verifier (V), see
[How confidence and calibration work](/docs/concepts/confidence/). This page is
the technical/config reference for grounding itself, plus the deterministic
checks and enforced-grounding mechanics that build on top of it.

## Grounding (shadow mode)

**What it is.** After a step runs, an optional second call — a "grounding
judge" — checks how many of the step's *load-bearing claims* (a stated root
cause, a metric value, a causal link, a referenced ticket/dashboard id) are
actually supported by evidence in that step's own execution trace, rather than
just asserted. The result is a **grounding score G ∈ [0,1]** (the fraction of
claims that are supported) plus a per-claim breakdown, both persisted as
`pipeline_steps.grounding_score` and `pipeline_steps.trust_report`.

:::note[Phase 0 — shadow only]
This is pure observation: G is recorded, never enforced. It never touches
`effective_confidence`, the `confidence_threshold` gate, `on_low_confidence`,
or any abort/escalate/stop path. The point is to accumulate, on real traffic, a
record of how far an agent's self-reported confidence (S) and its actual
grounding (G) diverge — near-identical self-reported confidence can hide a
well-evidenced conclusion or a confidently-asserted guess, and shadow mode is
how you find out which. A later phase may let grounding gate side-effecting
steps; that isn't wired up yet.
:::

**Opt-in per step, gateway-only.** Grounding only runs for steps that declare
a `grounding:` block, and only for `executor: gateway` steps — only the
gateway executor emits the ordered tool-call trace (`agent_trace`) grounding
cross-references against. Steps on other executors, or a gateway step whose
trace has no tool activity, record `grounding_score = NULL` ("no evidence
trail to check"), never `0` ("claims are unsupported"). Grounding is not yet
wired into parallel/fan-out branches — sequential steps only.

```yaml
steps:
  - name: investigate
    executor: gateway
    executor_config: { agent: sre-investigation }
    grounding:
      agent: grounding-judge      # gateway agent; must be configured on the gateway
      max_trace_chars: 4000       # optional — see below
```

`grounding.agent` (default `grounding-judge`), `grounding.executor` (default
`gateway`), `grounding.executor_config`, `grounding.timeout_seconds` (default
120), and `grounding.max_trace_chars` (default 1500) are the only knobs —
there's no threshold or cap here; that's Phase 1, below.

:::caution[`max_trace_chars` — truncation, not a hallucination]
The transcript handed to the judge truncates each `tool_result`/agent-text
event at `max_trace_chars`, with a trailing `…`. A claim whose supporting
evidence lands past that cutoff is genuinely invisible to the judge — that
shows up looking exactly like "the primary agent is making things up," when
actually the trace transcript just didn't include the relevant part. Steps
whose tools return long content (a full document read, a large query result)
should raise this; the default (1500) is tuned for cheap, short evidence, not
long reads.

**There are two independent truncation points, and raising this one alone may
not be enough.** `grounding.max_trace_chars` only controls how much of the
trace VectorStep *already has* it hands to the judge. The Gateway itself caps each
`tool_result` event's content **before VectorStep ever receives it**
(`limits.trace_tool_result_max_chars`, default 3000, in the Gateway's own
config) — if a tool result was truncated there, no `grounding.max_trace_chars`
setting on the VectorStep side can recover the missing part, because it was never
sent. Use the primary step's `executor_config.trace_max_chars` (the `gateway`
executor) to raise the Gateway-side cap for that step, *then* raise
`grounding.max_trace_chars` here to match — otherwise you've just moved the
same cutoff from the judge's transcript-formatting step to the Gateway's own
capture step. Either cutoff being too low produces the identical symptom (a
claim that looks unsupported but genuinely wasn't), so if grounding keeps
flagging claims you believe are backed by real evidence, check both.
:::

**Soft failure.** Like the verifier, a grounding call that errors or times out
logs a warning and records `grounding_score = NULL` with the error captured in
the report — it never breaks or delays the step. When the failure is
specifically the judge's own output not parsing as JSON — most commonly
because a step with many load-bearing claims produced a per-claim evidence
list long enough to hit the judge agent's output-length ceiling
mid-generation — the report's `raw_output` field carries the judge's full,
untruncated text (not just the 500-character snippet in the log/exception
message), so a reviewer can tell "genuinely truncated" apart from "malformed
from the start." When the failure is a timeout instead —
`grounding.timeout_seconds` (default 120, per-step override) elapsing before
the judge responds at all — there's no response to show `raw_output` for, but
the error message itself now says so explicitly (`"grounding call timed out
after 120s"`) rather than the blank string `asyncio.TimeoutError` carries by
default; a step whose trace/claim count needs longer should raise
`grounding.timeout_seconds` directly rather than relying on the (deliberately
conservative) default.

**The `grounding-judge` agent contract.** Grounding calls a gateway agent
(configured on the **VectorStep Gateway**, not in this repo) whose only job is a
constrained cross-reference — it cannot browse or add outside knowledge. It
receives:

1. the original task given to the primary agent (its rendered
   `prompt_template` — the same thing a `critic`-mode verifier sees, see
   [Verifiers](/docs/pipelines/verifiers/)),
2. the primary agent's structured output (`summary`, `next_step_context`,
   `reasoning`), and
3. a formatted transcript of the primary agent's tool calls and results.

The judge's prompt is explicit that (1) is *given, trusted input* — a claim
that merely restates a fact already present in the original task (alert
severity, service name, environment, summary, ...) needs no trace evidence,
because the agent was told it, not asked to discover it. Only claims that go
beyond the given input (a root cause, a specific metric value, a causal link, a
ticket/dashboard id it created or looked up) need a supporting tool result.
Without (1), the judge has no way to tell "restates the input" apart from
"claims something it needed to discover," and will mark plain input facts as
unsupported — a false "unsupported" verdict, not a real evidence gap.

...and must return an `LLMOutput`-shaped JSON object where:

- **`confidence`** carries **G** itself — the fraction of load-bearing claims
  supported by trace evidence, in `[0,1]`. (This reuses the existing
  `confidence` field as the transport so the ordinary `GatewayExecutor` parse
  path works unchanged; it is not the judge's confidence in itself.)
- **`summary`** — one sentence, e.g. *"3 of 4 load-bearing claims are
  supported by tool results; the root-cause claim is not."*
- **`reasoning.claims`** — a list of `{ "claim": str, "supported": bool,
  "evidence": str }`, one per load-bearing claim identified.
- **`next_step_context`** — unused, `""`.

The persisted `trust_report.grounding` also records **which** agent/model
actually judged this run — `agent` (from `grounding.agent` config), plus
`model`/`provider` read straight from the judge's own response metadata (both
`null` when grounding didn't compute, e.g. an error or no trace) — and
`prompt`: the judge's own fully-rendered prompt (the
`_GROUNDING_PROMPT_TEMPLATE` with the original task, primary's response, and
trace all substituted in), so a reviewer can see exactly what the judge was
shown, not just what it concluded. `raw_output` carries the exact text the
judge replied with — not just the `summary`/`claims` fields VectorStep extracted
from it — for both a successful parse and a parse failure (the executor
stashes it onto `LLMOutput.raw_response["response_text"]` the same way it
stashes `prompt`; on failure, `LLMParseError.raw_text` carries the full,
untruncated text rather than the 500-char snippet in the log/exception
message). `prompt` and `raw_output` are populated for `gateway`/`openclaw`
executor grounding calls; `null` for others.

**Where it surfaces.** Each grounded step's expanded detail panel shows a
**"Trust (shadow)"** widget: self-report (S) vs. verifier (V, if any, with its
own agent/model shown alongside) vs. grounding (G, with its judging
agent/model shown alongside), a divergence flag when `|G − S| ≥ 0.2`, and the
per-claim ✓/✗ breakdown with evidence. A **Prompt** disclosure (collapsed by
default) shows what the judge was asked; a matching **Answer** disclosure
right below it shows the judge's raw reply text
(`trust_report.grounding.raw_output`) — present for a successful grounding
pass and, just as importantly, for one that failed to parse, so a reviewer
isn't limited to the `computed: false` / error-message summary and can see
exactly what the judge actually returned. `vectorstep_step_grounding_score` exposes
the score distribution for Grafana.

**The Trust panel isn't just for grounded steps.** Any step with a verifier —
even with no grounding, deterministic checks, or calibration configured —
gets a "Trust (shadow)" panel too, so how S and V combined is never invisible.
A **"How was this calculated?"** button reveals a plain-language,
numbers-first walkthrough of that specific run: self-report → verifier
combine → calibration (if enforced) → grounding (if configured) →
deterministic checks (if declared) → the final figure and what it decided. No
config keys, just what actually happened on this run — built from the same
`trust_report` data, not a re-derivation from the pipeline's current config.

Two things worth knowing about how honest this walkthrough can be:
- **`V_veto_floor`** is persisted in `trust_report.signals` (alongside
  `V_mode`) specifically so the narrative can say *why* a verifier's lower
  score didn't change anything ("this step only lowers confidence below X%")
  instead of just asserting it did nothing. Rows from before this field
  existed fall back to vaguer wording rather than inventing a number.
- **`grounding.enforce`** is persisted per-run for the same reason —
  grounding computes and reports a score even in pure shadow mode, so its
  presence alone can't tell you whether it actually gated a given historical
  run. Rows predating this field say so explicitly ("isn't recorded for this
  older run") rather than guessing either way.

A **Prompt** disclosure (collapsed by default) also sits above each gateway
step's parsed output, showing the actual rendered prompt the agent
received — necessary for marking step accuracy honestly, since a grounding
claim like "the agent didn't check X" might mean the prompt never asked it to.
The verifier pane and the grounding claims section each get their own
matching disclosure (`verifier_prompt`, `trust_report.grounding.prompt`) —
all three (primary, verifier, grounding judge) are computed from the same
executor-level stash (`GatewayExecutor.execute` writes it onto
`raw_response["prompt"]` for every call it makes), so seeing one doesn't mean
the others are guaranteed present — each is independently `null` if that
particular call used a non-gateway executor or predates this fix.

A **Step configuration** disclosure sits alongside "How was this calculated?"
in the Trust panel — a plain-language summary of what this step is *set up*
to do: confidence threshold and `on_low_confidence`; verifier mode and
combination strategy, naming a `veto` floor by its actual number rather than
leaving "why didn't this change anything" unexplained; grounding's enforce
state; declared deterministic checks by name; calibration's
`n_min`/`on_uncalibrated`. Built from the same `trust_report` data as the
narrative, not a live read of the pipeline's current config.

## Deterministic checks & enforced grounding (Phase 1)

Phase 0 (above) only ever records G — it never gates. Phase 1 adds two
**opt-in per step** mechanisms that can actually change a step's outcome:
deterministic checks (D) and grounding-as-a-gate (`grounding.enforce: true`).
A step that declares neither behaves byte-for-byte as it did before this
feature existed — the legacy `effective_confidence < confidence_threshold`
comparison is a permanent, first-class gate policy, not a deprecated code
path.

**The gate formula:**

```
combined_trust = effective_confidence                    # today's S after the verifier's veto, unchanged
if grounding.enforce and G is not None:
    combined_trust = min(combined_trust, G)               # G can only ever pull trust down
if deterministic_checks declared and not all_passed:
    combined_trust = 0.0                                  # a failed check is dispositive

# the SAME comparison, SAME threshold, SAME on_low_confidence action as today:
if combined_trust < step.confidence_threshold:
    <on_low_confidence action>
```

There is deliberately no second, separately-tuned threshold for grounding (no
`require_grounding: 0.7` or similar) — `grounding.enforce` reuses the step's
*existing* `confidence_threshold`. A null G (grounding wasn't computed this
run — no trace, or the grounding call itself soft-failed) never triggers the
cap; `combined_trust` is simply left as whatever it already was, consistent
with Phase 0's "no evidence trail to check" ≠ "unsupported" rule.

### Deterministic checks (D)

A step can declare a list of `deterministic_checks:`, each a pass/fail
assertion the *runner* evaluates directly — no LLM involved. Three check
types:

**`shell`** — run a command; evaluate its output.

```yaml
deterministic_checks:
  - type: shell
    name: still_breaching
    run: "curl -s 'http://prometheus/api/v1/query?query=rate(http_5xx{service=\"{{ labels.service }}\"}[5m])' | jq '.data.result[0].value[1]'"
    expect: "result | float > 0.02"     # bare Jinja2 bool expr — same convention as `when:`,
                                        # NOT wrapped in {{ }}. Sees `result` (stdout, stripped)
                                        # and `exit_code`, plus the normal step context.
    timeout_seconds: 30                # default
```

**`webhook`** — call a URL; evaluate the response. Same shape as the existing
`on_failure.webhook` config (`url`/`method`/`headers`/`payload`) —
deliberately does **not** call `raise_for_status`, since a check might
legitimately expect a non-2xx status (e.g. 404 = "does not exist").

```yaml
deterministic_checks:
  - type: webhook
    name: dashboard_resolves
    url: "https://grafana.example.com/api/dashboards/uid/{{ steps.investigate.dashboard_uid }}"
    method: GET
    headers:
      Authorization: "Bearer {{ steps.investigate.grafana_token }}"
    expect: "response.status_code == 200"   # sees `response` = {status_code, body}
```

**`human`** — ask a person to approve/reject, reusing the *existing*
human-approval subsystem (same channels, same per-team routing, same
testing-stage behaviour as `executor: human` — see
[Human-in-the-loop](/docs/pipelines/human-in-the-loop/)).

```yaml
deterministic_checks:
  - type: human
    name: sre_signoff
    message: "Auto-remediate {{ steps.investigate.summary }}? Approve to proceed."
    timeout_seconds: 300               # default
```

**Any prior step's output is available to every check type**, via the same
`{{ steps.step_name.field }}` context `prompt_template` uses (see
[Prompt construction](/docs/pipelines/prompts/)) — `shell.run`,
`webhook.url`/`webhook.headers`/`webhook.payload`, and `human.message` are all
Jinja2-rendered against it before use; `expect` (`shell`/`webhook`) already
sees the full step context too since it's evaluated the same way `when:` is.

:::caution[`shell.run` quotes every interpolated value]
A step's output is agent-generated, not operator-controlled, and `shell`
checks run unsandboxed (see below) — so a value containing shell
metacharacters (`;`, `|`, `` $(...) ``, quotes) must not be able to break out
of the command the pipeline author actually wrote. Every `{{ }}` substitution
in `run` is passed through `shlex.quote` before insertion, so
`{{ steps.investigate.summary }}` is always treated as one literal argument,
never as additional shell syntax, regardless of what the agent put in
`summary`. This only affects *interpolated values* — the command template
itself (the literal text you wrote in `run:`) is untouched.
:::

**Fail-closed, universally.** A check that cannot be evaluated — a shell
command errors or times out, a webhook is unreachable, a human approval times
out — is recorded as **failed**, never silently skipped. D is meant to be the
strongest, most trustworthy signal in the trust vector, so an unanswerable
check must not quietly vanish from the computation. (This is a deliberate
divergence from grounding's soft-fail philosophy above — grounding failing
soft just means "less signal"; a deterministic check failing soft would mean
"we lost the ability to catch a real problem.")

**Stage behaviour differs by check type.** `shell` and `webhook` checks are
semantically *queries*, not outbound notifications, so — unlike
`on_failure.webhook` — they are **not** muted by `stage: testing`; muting them
would make it impossible to test check logic in a testing pipeline.
`human`-type checks **do** inherit `executor: human`'s existing testing-stage
behaviour (external channel not sent; the decision is made via VectorStep's own
`/ui/approvals`; a timeout auto-approves). See
[Pipeline stages](/docs/concepts/stages/) for the full testing-vs-production
behaviour matrix.

:::caution[Unsandboxed by design]
A `shell` check runs with the full environment and permissions of the VectorStep
process — there is no sandboxing or resource-limiting. This is a deliberate
choice for a single-operator, self-hosted deployment where the operator
already fully controls pipeline YAML and already has executors capable of far
more (MCP tools, OpenClaw). Revisit this if the deployment model ever becomes
multi-tenant.
:::

### Grounding as a gate

Add `enforce: true` to an existing `grounding:` block:

```yaml
steps:
  - name: investigate
    executor: gateway
    executor_config: { agent: sre-investigation }
    confidence_threshold: 0.75
    grounding:
      agent: grounding-judge
      enforce: true                      # G now participates as a ceiling on combined_trust
    deterministic_checks:
      - type: shell
        name: still_breaching
        run: "curl -s '...' | jq '.data.result[0].value[1]'"
        expect: "result | float > 0.02"
```

**Where it surfaces.** The run-detail Trust panel header now reads **"Trust
(enforced)"** instead of "(shadow)" for any step where grounding or a
deterministic check actually participated in the gate, with a `Combined
trust` figure alongside S/V/G, a `Checks (D)` PASS/FAIL chip, and a per-check
✓/✗ list (name, type, detail). `vectorstep_step_deterministic_check_total` exposes
check outcomes for Grafana.

See `samples/pipelines/trust-vector-remediation.yaml` for a complete worked
example of enforced grounding and a deterministic check gating a
side-effecting step, or
`samples/pipelines/deterministic-checks-step-context.yaml` for a smaller,
focused example of all three check types (`shell`/`webhook`/`human`) reading a
prior step's structured output as template variables.

## Where next

- **[Calibration](/docs/pipelines/calibration/)** — replacing the raw
  self-report with a measured, per-agent accuracy figure once enough marked
  history exists.
- **[Verifiers](/docs/pipelines/verifiers/)** — the second-opinion signal (V)
  that runs before grounding in the gate formula.
- **[How confidence and calibration work](/docs/concepts/confidence/)** — the
  plain-language explanation of the whole trust vector.
