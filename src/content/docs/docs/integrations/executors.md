---
title: Executors
description: The executor adapter pattern — Gateway, OpenClaw, human-in-the-loop, webhook, sub-pipeline.
sidebar:
  order: 2
---

:::caution[Content migration in progress]
This page is being migrated from the P-Ork README (§9 "Executor Adapter
Pattern" and related sections). Until then, the README is the authoritative
source.
:::

AI backends are adapters behind a common interface; steps in the same pipeline
can mix executors freely: `gateway` (P-Ork Gateway agents), `openclaw`,
`human` (Telegram/Slack/Teams approvals), `webhook` (HTTP POST out),
`pipeline` (sub-pipelines), and `notify`.
