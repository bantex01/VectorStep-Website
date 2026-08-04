---
title: Testing vs production stages
description: Pipeline stages, what stage gates, and how runs are attributed to the stage they ran under.
sidebar:
  order: 2
---

:::caution[Content migration in progress]
This page is being migrated from the P-Ork README (§3c "Pipeline Stages"). Until
then, the README is the authoritative source.
:::

Every pipeline declares `stage: testing` or `stage: production`. Stage controls
which webhook sources may trigger it, keeps testing runs out of production
rollups, and is persisted per-run — a run permanently records the stage its
pipeline had when it was triggered.
