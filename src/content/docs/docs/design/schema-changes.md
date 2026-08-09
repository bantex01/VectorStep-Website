---
title: Adding a schema change
description: How to generate and review an Alembic migration when changing the ORM models.
sidebar:
  order: 5
---

Edit the model in `service/src/db/models.py`, then generate a revision from
the diff and review it before committing — autogenerate is a starting point,
not the final migration:

```bash
cd service
alembic revision --autogenerate -m "add foo column to pipeline_runs"
```

Check the generated file in `migrations/versions/` for: correct
`batch_alter_table` usage on anything SQLite can't `ALTER` directly, a sane
`downgrade()`, and that a backfill (if the change needs one) is written
explicitly — autogenerate only emits schema-shape DDL, never data migrations.
`test_database_migrations.py`'s drift-guard test fails CI if a model change
ships without a matching revision.

For how migrations run at deploy time (auto-migrate on boot vs. a DBA-run
step), see [Deployment](/docs/operations/deployment/#database).
