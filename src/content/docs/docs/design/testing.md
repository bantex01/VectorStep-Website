---
title: Testing
description: How the test suite is organised, how to run it against SQLite or Postgres, and what CI runs on every push.
sidebar:
  order: 4
---

Unit tests cover the pure-function logic: pipeline resolver matching, verifier
confidence-combination and parallel join strategies, step-library `use:`
deep-merge, and webhook dedup fingerprinting/settings.

```bash
# from repo root — installs requirements.txt plus pytest/pytest-asyncio
pip install -r requirements-dev.txt

cd service
pytest
```

By default the suite runs against SQLite — a fresh per-test temp-file DB, no
setup required. To run the same tests against Postgres instead (exercising
the Postgres-only migration branch in `create_tables()`), point
`VECTORSTEP_TEST_DATABASE_URL` at a throwaway database:

```bash
createdb vectorstep_test
VECTORSTEP_TEST_DATABASE_URL=postgresql+asyncpg://localhost:5432/vectorstep_test pytest
```

Isolation on Postgres is via a `DROP SCHEMA public CASCADE; CREATE SCHEMA
public;` reset around each test (see `tests/conftest.py`'s `db` fixture)
rather than a fresh file, since there's no per-test temp file on a shared
server. CI (`.github/workflows/tests.yml`) runs both backends on every push.
