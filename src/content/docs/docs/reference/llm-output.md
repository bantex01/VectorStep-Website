---
title: "LLMOutput: the step contract"
description: The Pydantic contract every executor backend must return — mandatory and optional fields, extra-field propagation, and how downstream steps reference them.
sidebar:
  order: 4
---

Every executor backend must return an `LLMOutput`. This is the contract
between pipeline steps — the runner reads it for flow decisions, and
downstream steps reference its fields in prompt templates.

```python
class LLMOutput(BaseModel):
    model_config = ConfigDict(extra="allow")   # extra fields allowed and propagated

    # --- Mandatory ---
    confidence: float             # 0.0–1.0. Compared against confidence_threshold.
    summary: str                  # One-sentence human-readable outcome. Used in
                                  # notifications and downstream {{steps.name.summary}}.
    next_step_context: str        # Focused brief for the next step. Available as
                                  # {{steps.name.next_step_context}}. May be "" for
                                  # terminal steps.

    # --- Flow control ---
    proceed: bool = True          # false = pipeline stops cleanly here (status=stopped).
                                  # No further steps run. Use when the agent is confident
                                  # no further action is warranted.
    proceed_reason: str | None = None  # Required when proceed=false. Explain why.

    # --- Optional enrichment ---
    reasoning: dict | None = None  # Free-form audit dict. Conventional keys: supports,
                                   # contradicts, assumptions. Available downstream as
                                   # {{steps.name.reasoning.supports}} etc.

    # --- Artifacts (optional) ---
    artifacts: dict | None = None  # {name: content} — runner writes to disk, replaces
                                   # content with references. See Artifact storage.

    # --- Set by the executor (agents must NOT include these) ---
    model: str | None = None      # Populated from API metadata by the executor.
    provider: str | None = None   # Gateway provider key (gateway executor only).
    raw_response: dict = {}       # Full unparsed response for audit. Set by executor.
```

**Extra fields are allowed and fully propagated.** Any field returned by an
agent beyond the schema above (e.g. `jira_ticket`, `doc_found`, `action`,
`dashboard_uid`) is stored in the DB and available in all downstream prompt
templates as `{{steps.step_name.field_name}}`. This is the primary mechanism
for passing structured data between steps.

**Mandatory vs optional at a glance:**

| Field | Required? | Notes |
|---|---|---|
| `confidence` | **Yes** | Must be 0.0–1.0. No default — validation fails if missing. |
| `summary` | **Yes** | No default — validation fails if missing. |
| `next_step_context` | **Yes** | Empty string `""` is valid for terminal steps. |
| `proceed` | No | Defaults to `true`. Only set `false` when the pipeline should stop cleanly. |
| `proceed_reason` | No | Include whenever `proceed: false` to make the stop auditable. |
| `reasoning` | No | Recommended for triage/analysis steps; improves verifier quality. |
| `artifacts` | No | `{name: content}` dict. Runner writes each value to disk; content is not stored in the database. See [Artifact storage](/docs/operations/runs/). |
| `model` | No | Do not include — the executor sets this from API metadata. |
| `provider` | No | Do not include — the `gateway` executor sets this from `agentMeta.provider` (the VectorStep Gateway provider that served the call, e.g. `anthropic`/`openrouter`/`azure`). `None` for other executors. |
| `raw_response` | No | Do not include — set by the executor. |
| Any extra field | No | Freely add domain fields (`jira_ticket`, `action`, etc.). All are stored and accessible downstream. |

**Accessing prior step output in prompts:**

Hyphens in step names must be written as underscores in template references:

```yaml
# Step named "first-line-triage" is referenced as:
{{steps.first_line_triage.summary}}
{{steps.first_line_triage.next_step_context}}
{{steps.first_line_triage.jira_ticket}}   # extra field
{{steps.first_line_triage.reasoning.contradicts}}
```

**Minimal valid agent response:**
```json
{
  "confidence": 0.85,
  "summary": "CPU spike on api-gateway traced to upstream timeout storm — self-resolving.",
  "next_step_context": "Check upstream service latency before closing ticket."
}
```

**Full response with optional fields:**
```json
{
  "confidence": 0.90,
  "proceed": true,
  "summary": "OTEL Collector scrape duration elevated — CPU pressure from upstream.",
  "next_step_context": "Dashboard uid=abc123. Query scrape_duration_seconds p99 from 06:30–07:05.",
  "jira_ticket": "OC-87",
  "doc_found": true,
  "reasoning": {
    "supports": "SLO breach aligns with known fragility pattern in service doc.",
    "contradicts": "No downstream impact observed yet.",
    "assumptions": "Alert timing and Confluence doc are accurate."
  }
}
```
