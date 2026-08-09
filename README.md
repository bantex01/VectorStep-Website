# VectorStep Website

Marketing site + documentation for VectorStep. Astro + Starlight, fully static.

## Commands

| Command           | Action                                    |
| :---------------- | :---------------------------------------- |
| `npm install`     | Install dependencies                      |
| `npm run dev`     | Dev server at `localhost:4321`            |
| `npm run build`   | Static build to `./dist/`                 |
| `npm run preview` | Preview the built site locally            |

## Structure

- `src/pages/index.astro` — landing page
- `src/content/docs/docs/` — Starlight docs, grouped as Getting Started,
  Concepts, Pipelines, Sources & Executors, UI & Insights, Gateway, Operations,
  Reference, Design & Internals, About
- `src/styles/global.css` — theme
- `public/screenshots/` — landing-page carousel images

## Deployment

Point the host at `npm run build` → `dist/`. Deployable to Vercel, Netlify,
Cloudflare Pages or GitHub Pages.

Regenerating the demo screenshots is documented in the private dev-docs repo.

## Licence

All rights reserved. Unlike the engine repos, this repo carries no open-source
licence — it is marketing content, not engine code.
