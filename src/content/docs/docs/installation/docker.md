---
title: Docker
description: Pulling the published VectorStep and Gateway images, config-mounting conventions, and the docker-compose evaluation path.
sidebar:
  order: 2
---

VectorStep and the Gateway each ship their own `Dockerfile`
(`service/Dockerfile` in the VectorStep repo, `Dockerfile` at the root of
VectorStep-Gateway) and publish multi-arch (`linux/amd64` + `linux/arm64`)
images to GHCR on every tagged release, plus an `edge` tag tracking the
default branch. See [Versions and releases](/docs/about/status-and-support/#versions-and-releases)
for what each tag means and the VectorStep/Gateway compatibility rule:

```bash
docker pull ghcr.io/bantex01/vectorstep:latest
docker pull ghcr.io/bantex01/vectorstep-gateway:latest
```

## Config and secrets

Images contain code and committed samples only — **config is never baked in**.
Mount a config file and point `CONFIG_PATH` (VectorStep) /
`VECTORSTEP_GATEWAY_CONFIG` (Gateway) at it; secrets arrive as environment
variables consumed by the config's `${VAR}` substitution. Everything writable
lives under a single `/data` volume, so the container variant of
`config.yaml` looks like this:

```yaml
database: {url: "sqlite+aiosqlite:////data/db/runs.db"}   # four slashes = absolute path
pipeline_config_dir: /data/pipelines     # or a ConfigMap mount — see Kubernetes
step_library_dir: /data/steps
artifacts: {dir: /data/artifacts}
logging: {dir: /data/logs}
```

## Running it

```bash
docker run -d \
  -p 8000:8000 \
  -v ./config.yaml:/etc/vectorstep/config.yaml:ro \
  -v vectorstep-data:/data \
  ghcr.io/bantex01/vectorstep:latest
```

The Gateway's container config additionally needs `identity.path` and
`agents_dir` pointed at `/data` — its default identity path
(`~/.vectorstep-gateway/identity`) is ephemeral per-container, which would
regenerate the operator token on every recreation. See
`samples/config.yaml.example` in each repo for the full annotated
container-paths block.

## Evaluating the pair locally (docker compose)

VectorStep ships a `docker-compose.yaml` (`deploy/docker-compose.yaml`) that
brings up both services from sibling checkouts with `docker compose up` —
see `deploy/README.md` for the one-time operator-token bootstrap step. It's
an evaluation/dev path, not a production one — for a real deployment, see
[Kubernetes](/docs/installation/kubernetes/).

## Where next

- **[Kubernetes](/docs/installation/kubernetes/)** — the production path
  once evaluation is done.
- **[Deployment](/docs/operations/deployment/)** — the full `config.yaml`
  reference and database/migration mechanics, regardless of how you're
  running the images.
