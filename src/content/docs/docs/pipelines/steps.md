---
title: Step library
description: Reusable step definitions shared across pipelines, and the deep-merge rules for use.
sidebar:
  order: 2
---

:::caution[Content migration in progress]
This page is being migrated from the P-Ork README (§4a "Step Library" and §5
"LLMOutput"). Until then, the README is the authoritative source.
:::

The step library (`service/steps/`) holds named, reusable step definitions.
A pipeline references one with `use: <step-name>` and can override any field —
overrides deep-merge over the library definition. Analytics aggregate per
library step across every pipeline that uses it.
