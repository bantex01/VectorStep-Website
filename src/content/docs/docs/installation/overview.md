---
title: Installation
description: Every way to run VectorStep and the Gateway, by platform — pick the one that matches how you actually want to run this.
sidebar:
  order: 1
  label: Overview
---

[Quick start](/docs/getting-started/quick-start/) gets a pair of services
running fast, with two one-liner paths (CLI install, or Docker). This
section is the full reference to sit alongside it — everything from a local
dev setup through to a production Kubernetes cluster, organized by how you
actually intend to run this rather than crammed into one page.

- **[Docker](/docs/installation/docker/)** — pull the published images,
  `docker run` or `docker compose` for local evaluation.
- **[Kubernetes](/docs/installation/kubernetes/)** — plain manifests for a
  real cluster, plus the two constraints (single replica, in-process
  migrations) worth knowing before you apply them.
- **[Linux](/docs/installation/linux/)** — from-source development setup,
  plus a systemd path for a plain VM with no container runtime.
- **[macOS](/docs/installation/macos/)** — the same from-source path as
  Linux today; called out separately since that may not stay true forever.
- **[Windows](/docs/installation/windows/)** — WSL2 today; native Windows
  support is on the roadmap, not yet available.

For the config file itself once something's running — every field, the
database decision, migrations — see [Deployment](/docs/operations/deployment/).
