---
title: Cron scheduler
description: Running pipelines on a cron schedule in addition to, or instead of, webhook triggers.
sidebar:
  order: 10
---

Pipelines don't have to wait for a webhook. A `schedule:` block runs a
pipeline on a cron schedule, using the exact same execution path as any other
trigger.

## Cron scheduler

Any pipeline can declare an optional `schedule:` block to run on a cron
schedule in addition to (or instead of) webhook triggers.

```yaml
schedule:
  cron: "0 9 * * 1-5"
  summary: "Daily morning service health sweep"
  severity: info
  team: platform           # owning team for token attribution
  labels:
    service: my-service
    environment: prod
```

Schedules register at startup and re-register atomically on every `/reload`
or `SIGHUP`. Scheduled runs synthesise a `NormalisedContext` with
`source="scheduler"` and fire through the standard runner — identical code
path to webhook triggers.

```bash
GET /schedules
# → {"schedules": [{"pipeline": "my-pipeline", "cron": "0 9 * * 1-5", "next_run": "..."}]}
```

## Where next

- **[Team attribution](/docs/operations/teams/)** — how the `team` field
  above resolves to token attribution and, downstream, human-approval
  routing.
- **[Pipeline schema](/docs/pipelines/schema/)** — the full YAML reference
  this `schedule:` block lives alongside.
