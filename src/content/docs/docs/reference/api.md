---
title: REST API
description: Management, analytics, and write endpoints for the P-Ork service.
sidebar:
  order: 1
---

:::caution[Content migration in progress]
This page is being migrated from the P-Ork README (§15 "Management Endpoints"
and subsections). Until then, the README is the authoritative source.
:::

The service exposes a full JSON API: run triggering and inspection, live SSE
run tailing, pipeline/step CRUD with validation, per-pipeline and per-step
analytics, calibration bins, prompt/agent version history, readiness readouts,
accuracy feedback, Prometheus metrics, and health probes.
