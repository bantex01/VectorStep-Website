---
title: Kubernetes
description: Plain manifests for a real cluster, the single-replica constraint, and how migrations run on boot.
sidebar:
  order: 3
---

Target: ARM64 home lab cluster (Ubuntu snap k8s), pulling the published GHCR
images — see [Docker](/docs/installation/docker/) for image tags and the
config-mounting convention shared with this page.

Both repos ship plain, heavily-commented manifests under `deploy/k8s/`
(`deployment.yaml`, `service.yaml`, `configmap.example.yaml`, `pvc.yaml`) —
copy-and-adapt templates, not a generic chart. A Helm chart is deliberately
out of scope for now: the manifests are the ground truth a chart would
template, and templating them before there's a second real user to justify
it is premature. See `deploy/k8s/README.md` in each repo for the exact
`kubectl apply` order and secret setup.

Two things worth knowing before you apply them:

- **VectorStep runs `replicas: 1` with `strategy: Recreate`, and that's
  required regardless of database backend** — the scheduler is in-process
  and the dedup/event state is in-memory, so a second replica would
  double-fire scheduled pipelines. PostgreSQL doesn't change this; it only
  changes whether SQLite's single-writer limitation is also in play.
- **Migrations run in-process at boot** (`create_tables()`, see
  [Deployment → Database](/docs/operations/deployment/#database)) when
  `database.auto_migrate` is `true` (the default). With `replicas: 1` +
  `strategy: Recreate` that's safe and needs no init container — the old
  pod is fully gone before the new one starts. For a DBA-controlled
  cluster, set `auto_migrate: false` and run
  `kubectl exec ... alembic upgrade head` (or a one-shot `Job`) before
  rolling the new image instead.

Secrets (Gateway tokens, webhook tokens, LLM provider keys) are delivered as
a Kubernetes `Secret` referenced via `envFrom`, feeding the same `${VAR}`
placeholders the config uses everywhere else — never baked into the
ConfigMap or the image.

## Where next

- **[Docker](/docs/installation/docker/)** — image tags and the
  `/data` volume convention these manifests build on.
- **[Deployment](/docs/operations/deployment/)** — the full `config.yaml`
  reference and database/migration mechanics.
