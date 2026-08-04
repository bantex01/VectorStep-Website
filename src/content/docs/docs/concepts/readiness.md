---
title: Promotion readiness
description: Owner-defined criteria a pipeline must earn before promotion from testing to production.
sidebar:
  order: 3
---

:::caution[Content migration in progress]
This page is being migrated from the P-Ork README ("Promotion readiness
(owner-defined criteria)" and "Criteria builder (guided UI)" sections). Until
then, the README is the authoritative source.
:::

Pipelines start life as `stage: testing` and are promoted to `production` by
their owner. Readiness is the evidence-based readout that tells you whether a
pipeline has *earned* that promotion — evaluated per step across four
independent tiers (**operational**, **confidence**, **accuracy**,
**calibration**) against the pipeline's own accumulated run history. It is
advisory: it never blocks a promotion, it tells you exactly what the evidence
says.

A guided, preview-only **criteria builder** on the pipeline detail page lets
you turn knobs and see within ~300ms what they would say about the evidence,
then copy a ready-to-paste YAML snippet.
