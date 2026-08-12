# Contributing to VectorStep-Website

This repository holds the VectorStep marketing site and documentation, published
at [vectorstep.io](https://vectorstep.io).

## Licensing — read this first, it decides what you can PR

This repo is **split**:

| Path | Licence | Contributions |
|---|---|---|
| `src/content/docs/**` | Apache-2.0 (see [`LICENSE-DOCS`](LICENSE-DOCS)) | **Welcome** |
| everything else | All rights reserved | Please open an issue instead |

"Everything else" is the landing page (`src/pages/`), styling, components, brand
assets, and screenshots. Those are the project's visual identity rather than its
documentation, and they stay closed.

Documentation contributions come in under Apache-2.0 section 5, the same as the
engine repos. There is no CLA and no copyright assignment — your commits stay
yours, in your name, in the history.

## Documentation contributions are welcome

If the docs are wrong, outdated, confusing, or contradict what the software
actually does, a pull request against `src/content/docs/` is welcome. So are
plain issues — a clear report is genuinely more useful than a rushed patch, and
never a waste of anyone's time.

The most useful reports say which page, what you expected to find, and what you
found instead.

### Running the site locally

```bash
npm install
npm run dev      # dev server at localhost:4321
npm run build    # static build to ./dist/ — run this before opening a PR
```

`npm run build` is the check that matters: Starlight validates frontmatter and
internal links at build time, so a green build catches most mistakes.

### What makes a documentation PR easy to merge

- **One page or one topic per pull request.**
- **Match the surrounding voice.** The docs are written in plain prose, British
  spelling, no marketing language, and no emoji. Read the neighbouring page
  before writing.
- **Keep frontmatter intact** — `title` and `description` are required, and
  `sidebar.order` controls placement.
- **Say why, not just what.** If a page was misleading, say what it led you to
  believe.
- **Don't restructure the navigation** in a docs fix. If the information
  architecture seems wrong, open an issue and let's talk about it first.

## Landing page, design, and branding

Please open an issue rather than a pull request for these. Not because feedback
isn't welcome — a broken layout, a dead link, or a confusing bit of copy is
worth reporting — but because those files aren't openly licensed, so I can't
merge a patch to them.

## The software itself

Code changes live in the engine repos, where pull requests are welcome:

- [VectorStep](https://github.com/bantex01/VectorStep) — the orchestration service
- [VectorStep-Gateway](https://github.com/bantex01/VectorStep-Gateway) — the agent runtime
- [VectorStep-Service-MCP](https://github.com/bantex01/VectorStep-Service-MCP)
- [VectorStep-Gateway-MCP](https://github.com/bantex01/VectorStep-Gateway-MCP)

## A realistic word on response times

Single-maintainer project run alongside a full-time job. Issues and pull
requests get read, but not always quickly and not always the same week. A nudge
after a fortnight is welcome.

## Getting in touch

If you'd rather talk to a person, I'm at **alex@vectorstep.io**.
