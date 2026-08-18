---
title: "Tutorial: metrics and traces in Grafana"
description: "Placeholder outline — scrape Prometheus metrics, export OTel traces, and view both in Grafana (a free Grafana Cloud account works fine for this)."
sidebar:
  order: 8
---

[PLACEHOLDER — outline only, not a full walkthrough yet.]

Every tutorial so far has watched one run at a time in VectorStep's own UI.
This tutorial is about the other view — trends across every run
(Prometheus) and a full per-run drill-down (OpenTelemetry traces) — using
[Observability](/docs/operations/observability/)'s metrics and tracing, and
Grafana to look at both.

## What this builds on

The pipeline as it stands after however much of the series you've done —
this tutorial doesn't touch pipeline YAML at all, only service config and
where the data goes afterward. The grounding and budget tutorials are worth
doing first if you want `vectorstep_step_grounding_score` and
`vectorstep_pipeline_cost_total` to actually have data in them once you get
to Grafana.

## Outline

1. Point a browser at `http://localhost:8000/metrics` directly first — no
   config needed, it's always on — and confirm real numbers are already
   there from every trigger so far in the series.
2. Enable tracing, `exporter: console` first (`observability.otel: {
   enabled: true, exporter: console }`) — trigger the pipeline, watch spans
   print to stdout, and confirm the [span
   hierarchy](/docs/operations/observability/#opentelemetry-tracing) matches
   what actually ran (a `triage` step span, its `gen_ai.gateway` child, the
   verifier span if Tutorial 2 is in place).
3. Get a Grafana account — [Grafana Cloud's free
   tier](https://grafana.com/products/cloud/) includes hosted Prometheus and
   Tempo, which is the path of least resistance for this tutorial; running
   Prometheus/Tempo/Grafana locally via Docker Compose works too if you'd
   rather not use a hosted account, at the cost of more setup.
4. Wire metrics and traces to it — Grafana Cloud's onboarding generates a
   ready-to-use Grafana Alloy config; point its Prometheus scrape target at
   this service's `/metrics` and switch `observability.otel.exporter` to
   `otlp` with `endpoint` pointed at Alloy's local OTLP receiver (default
   `http://localhost:4318/v1/traces`).
5. Build two or three panels from metrics already introduced earlier in the
   series: an escalation-rate panel from `vectorstep_pipeline_runs_total`
   (`rate()`, split by `status`), the grounding-score histogram
   `vectorstep_step_grounding_score`, and (if the budget tutorial is done)
   `vectorstep_pipeline_cost_total`.
6. Find a real trace in Tempo (search by `vectorstep.pipeline.name` or the
   root span name `pipeline.run: <pipeline>`) and click through from the
   root span into a step span into its `gen_ai.*` LLM-call child — this is
   the same run you can already see in VectorStep's own UI, from the other
   direction.
7. Note explicitly: metrics are always-on and every series here is
   `stage=production`-scoped, so a `stage: testing` pipeline (which this
   whole series has been, unless [the promotion
   tutorial](/docs/tutorials/promoting-to-production/) is already done)
   contributes nothing to any panel built here — worth confirming panels
   are genuinely empty before promotion and populate after, rather than
   assuming something's broken.

## Where next

- **[Observability](/docs/operations/observability/)** — the full metrics
  table, span hierarchy, and logging reference.
- **[Cost accounting](/docs/operations/cost-accounting/)** — where the cost
  metrics used in this tutorial's panels come from.

Next in the series — the capstone: **[Promote your pipeline to
production](/docs/tutorials/promoting-to-production/)**.
