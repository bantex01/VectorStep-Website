---
title: Pipeline schema
description: The full pipeline YAML reference — triggers, steps, executors, thresholds, flow control.
sidebar:
  order: 1
---

:::caution[Content migration in progress]
This page is being migrated from the P-Ork README (§4 "Pipeline Config Schema"
and related sections). Until then, the README is the authoritative source.
:::

Pipelines are YAML files in `service/pipelines/`. Each declares a `trigger`
(source + match rules), a list of `steps` (each with an executor, prompt
template, confidence threshold and flow-control policy), and optional
pipeline-level settings (stage, tags, notifications, readiness criteria).
Steps can be defined inline or pulled from the reusable
[step library](/docs/pipelines/steps/) with `use:`.
