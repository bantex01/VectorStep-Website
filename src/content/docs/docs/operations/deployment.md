---
title: Deployment
description: Service configuration, database setup, Docker and Kubernetes deployment.
sidebar:
  order: 1
---

:::caution[Content migration in progress]
This page is being migrated from the P-Ork README ("Service Configuration",
"Database", "Kubernetes Deployment"). Until then, the README is the
authoritative source.
:::

Local development runs on SQLite with zero infrastructure. Production runs on
PostgreSQL (`asyncpg`), with Prometheus metrics at `/metrics`, optional
OpenTelemetry tracing, rotating file logs, and a liveness/readiness probe at
`/health`.
