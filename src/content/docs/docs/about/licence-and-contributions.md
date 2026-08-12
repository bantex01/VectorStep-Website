---
title: Licence & contributions
description: VectorStep is Apache-2.0 open source and contributions are welcome — what that means in practice.
sidebar:
  order: 1
---

VectorStep is licensed under [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0).
You are genuinely welcome to use it, run it, modify it, and fork it. The
`NOTICE` file in each repo carries the copyright statement.

**These documentation pages are Apache-2.0 too.** The site repo
(`VectorStep-Website`) is otherwise all rights reserved — the landing page,
styling, brand assets, and screenshots are not openly licensed — but everything
under `src/content/docs/` carries the same licence as the code, via
`LICENSE-DOCS` at the repo root. That is what makes documentation pull requests
possible; it also means these pages are dense with pipeline configs and code
samples you are meant to copy, and a code licence handles those cleanly.

**Contributions are welcome.** Pull requests get read and merged. There's no
CLA to sign and no copyright assignment — contributions come in under
Apache-2.0 section 5, which applies by default, and your commits stay yours,
in your name, in the history.

## Before a large change, open an issue

Small changes — a bug fix, a doc correction, a missing test, a tidy-up — just
open a pull request. No preamble needed.

Larger changes — a new executor adapter, a new source parser, a schema change,
a refactor across modules — are worth an issue first, so you don't spend a
weekend on something that conflicts with work already in flight or with a
design decision that has a reason behind it. That's coordination, not
gatekeeping.

Each repo's `CONTRIBUTING.md` has the setup and test commands:

- [VectorStep](https://github.com/bantex01/VectorStep/blob/main/CONTRIBUTING.md) — the orchestration service
- [VectorStep-Gateway](https://github.com/bantex01/VectorStep-Gateway/blob/main/CONTRIBUTING.md) — the agent runtime
- [VectorStep-Service-MCP](https://github.com/bantex01/VectorStep-Service-MCP/blob/main/CONTRIBUTING.md)
- [VectorStep-Gateway-MCP](https://github.com/bantex01/VectorStep-Gateway-MCP/blob/main/CONTRIBUTING.md)

## What makes a pull request easy to merge

- **One concern per pull request.** Two unrelated fixes are two pull requests.
- **A test that fails before your change and passes after it** — for a bug fix,
  the single most useful thing you can include.
- **Existing style.** Match the surrounding code; the code is the style guide.
- **Say why, not just what.** The diff shows what changed; the description
  should say what problem it solves.
- **Docs updated if behaviour changed.** These docs live in a separate repo
  ([VectorStep-Website](https://github.com/bantex01/VectorStep-Website)) — either
  open a pull request there too, or just note in your code PR what needs
  changing.

## Also very welcome

- **Bug reports.** Steps to reproduce, what you expected, what happened, and
  the version you were running are usually enough.
- **Feature requests and use cases** — especially ones that explain what you
  were trying to do, not just what you want added. These shape the roadmap more
  than feature requests on their own.
- **Questions about how something works.** If the docs didn't answer it, that's
  a documentation bug and worth reporting.
- **Reports that the documentation is wrong or confusing.** Treated as bugs.

## A realistic word on response times

This is a single-maintainer project run alongside a full-time job. Issues and
pull requests get read, but not always quickly and not always the same week. If
a thread has gone quiet for a fortnight, a nudge is welcome.

## Forking

Forking is explicitly fine and the licence permits it. If you need behaviour the
project doesn't provide and an upstream change isn't the right fit, maintaining
your own fork is a legitimate answer. The one carve-out: you may not use the
VectorStep name or logo in a way that implies your fork is endorsed by or
affiliated with this project. See [Extending VectorStep](/docs/design/extending/)
for the three extension points designed for exactly this.

## Security issues

Please don't open a public issue for a suspected vulnerability — see the
`SECURITY.md` in the relevant repo for how to report one privately.

## Getting in touch

If you'd rather just talk to a person — about a use case, whether something is a
bug, or anything else — reach out at **alex@vectorstep.io**.
