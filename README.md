# P-Ork Website

Marketing site + documentation for [P-Ork](https://github.com/bantex01/P-Ork).
Astro + Starlight, fully static output — deployable as-is to Vercel, Netlify,
Cloudflare Pages, or GitHub Pages (point the host at `npm run build` → `dist/`).

- `/` — the landing page (`src/pages/index.astro`), dark zinc + indigo, matching
  the product UI. The hero carousel cycles real product screenshots from
  `public/screenshots/`.
- `/docs/…` — Starlight docs (`src/content/docs/docs/`), with built-in search.

## Commands

| Command           | Action                                    |
| :---------------- | :---------------------------------------- |
| `npm install`     | Install dependencies                      |
| `npm run dev`     | Dev server at `localhost:4321`            |
| `npm run build`   | Static build to `./dist/`                 |
| `npm run preview` | Preview the built site locally            |

## Status

- Landing page, theme, docs IA: **done**.
- Docs content: three exemplar pages are finished
  (`getting-started/quick-start`, `concepts/confidence`, `pipelines/verifiers`);
  the remaining pages are stubs pending migration from the product READMEs —
  see **`SPEC-content-migration.md`** for the full content map and rules.
- Placeholders to update before launch: `CONSOLE_URL` and `GITHUB_URL` in
  `src/pages/index.astro`, and the `social` GitHub link in `astro.config.mjs`.

## Regenerating the screenshots

The screenshots are captured from a real P-Ork instance running against a
seeded demo database (`pork_demo`) — fictional pipelines/data, so nothing
personal leaks and no LLM tokens are spent. To re-stage:

```bash
createdb pork_demo   # once

# 1. Start a demo service instance (isolated config, port 8300)
cd /Users/adalton/Development/github/P-Ork/service
CONFIG_PATH=/Users/adalton/Development/github/P-Ork-Website/demo/config.yaml \
  .venv/bin/uvicorn src.main:app --port 8300 --host 127.0.0.1

# 2. Seed the demo data (idempotent — wipes and re-inserts)
.venv/bin/python /Users/adalton/Development/github/P-Ork-Website/scripts/seed-demo-data.py \
  /Users/adalton/Development/github/P-Ork-Website/demo/pipelines

# 3. Capture at ~1530x803 viewport and drop into public/screenshots/
#    (trust-panel.jpg, calibration.jpg, readiness.jpg, runs.jpg)
```

The interesting URLs: `/ui/runs` (pick the newest escalated
`alert-triage-critical` run for the Trust panel), `/ui/insights/steps`
(sre-investigation drilldown for calibration flags),
`/ui/pipelines/checkout-refund-agent` (readiness card), `/ui/runs` (list).
