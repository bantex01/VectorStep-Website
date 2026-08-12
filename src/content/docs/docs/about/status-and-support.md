---
title: Status & support
description: What to expect from VectorStep as a best-effort, single-maintainer open source project.
sidebar:
  order: 2
---

VectorStep is maintained by a single author as a best-effort open source
project. There is no SLA and no bug bounty. Only the latest released version
receives fixes — there are no long-term support branches.

Issues are open and bug reports are wanted, and pull requests are welcome —
see [Licence & contributions](/docs/about/licence-and-contributions/) for what
that means in practice. There is no CLA and no copyright assignment. Because
this is a single-maintainer project run alongside a full-time job, issues and
pull requests get read, but not always quickly and not always the same week.

## Versions and releases

Tagging a release (`vX.Y.Z`) is what publishes a container image — see
[Deployment](/docs/operations/deployment/) for pulling published images and
running them, and each repo's `RELEASING.md` for the release process itself.
An `edge` tag tracks the default branch; `latest` and the semver tag track
the most recent release. An untagged local build reports `dev`.

**VectorStep and the Gateway deploy as a matched pair.** There's no protocol
version negotiation between them yet, so the only supported configuration is
running matching release tags together — don't mix, say, VectorStep `v0.7.0`
with Gateway `v0.5.0` and treat it as supported even if it happens to work.

`GET /health` on both services reports the running version, which is the
fastest way to confirm what's actually deployed in a given environment.

## Reporting a security issue

Do not open a public issue for a suspected vulnerability. Use GitHub's
private vulnerability reporting instead: the **Security** tab of the
relevant repo, **Report a vulnerability**. Include a description of the
issue, steps to reproduce or a proof of concept, the version or commit you
were running, and any relevant deployment details.

Reports will be acknowledged as promptly as realistically possible, you'll
be told whether the issue is accepted and what the fix timeline looks like,
and you'll be credited in the release notes when a fix ships, unless you'd
prefer not to be. Please allow a reasonable period for a fix before
disclosing publicly.

**Scope.** VectorStep executes AI pipelines that can call tools and take
actions. Some behaviour that looks alarming is intentional and configurable
rather than a vulnerability — for example, an agent taking an action its
`agent.yaml` grants it, or a pipeline step running without a verifier
because none was configured. Reports about *the trust and gating machinery
not behaving as documented* are firmly in scope; reports that amount to "a
permissive configuration is permissive" generally are not. If you're unsure,
report it anyway and say so.
