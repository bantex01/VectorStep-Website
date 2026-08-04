---
title: Webhook sources
description: Webhook intake, source detection, normalisation, and the generic source schema.
sidebar:
  order: 1
---

:::caution[Content migration in progress]
This page is being migrated from the P-Ork README (§1–§3 intake, normalisation,
resolution, dedup). Until then, the README is the authoritative source.
:::

A single `POST /webhook` endpoint accepts any source. Pluggable parsers
normalise each payload into a common `NormalisedContext`; the resolver matches
it to a pipeline; idempotent deduplication stops repeat deliveries triggering
repeat runs.
