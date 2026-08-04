---
title: Key design decisions
description: The load-bearing decisions in P-Ork's design, and why they were made.
sidebar:
  order: 1
---

:::caution[Content migration in progress]
This page is being migrated from the P-Ork README ("Key Design Decisions").
Until then, the README is the authoritative source.
:::

The short version: trust is a vector, not a scalar; every gating signal is
opt-in and additive; verifiers can never raise confidence; deterministic checks
fail closed; calibration is keyed by prompt and agent version so history never
silently pools across configurations.
