---
title: Windows
description: WSL2 is the supported path today — native Windows support is on the roadmap, not yet available.
sidebar:
  order: 6
---

**Native Windows support is on the roadmap, not available today.** Nothing
here — the `venv`/`pip` toolchain, systemd — has been built or tested
against native Windows, and there's currently no native install path.

## WSL2

The supported way to run this on Windows today is [WSL2](https://learn.microsoft.com/en-us/windows/wsl/install)
— a real Linux environment running under Windows, not a compatibility
shim. Once WSL2 is installed and you have a Linux distribution running
inside it (Ubuntu is the default and the one this is most tested against),
follow [Linux](/docs/installation/linux/) unmodified from inside your WSL2
shell — every command on that page, `venv`/`pip`/`systemd` included, applies
exactly as written.

If you'd rather avoid WSL2 entirely, [Docker Desktop for
Windows](https://www.docker.com/products/docker-desktop/) (which itself
runs on WSL2 under the hood) gets you to [Docker](/docs/installation/docker/)'s
path without manually setting up a Linux shell yourself.

## Where next

- **[Linux](/docs/installation/linux/)** — the instructions this page
  points you to run inside WSL2.
- **[Docker](/docs/installation/docker/)** — the container path, via
  Docker Desktop.
