# Implementation Spec: Docs Content Migration

**Audience:** implementing engineer (Sonnet). Self-contained. Follow it top to bottom.

**Status:** ready to implement. The site framework, landing page, theme, sidebar
config, and three exemplar pages are already built and building cleanly — do not
touch them except where this spec says so.

---

## 1. Context

This repo is the P-Ork marketing site + docs (Astro + Starlight, static output).
The docs content currently consists of:

- **Three finished exemplar pages** — study these before writing anything, they
  define the pattern you must follow:
  - `src/content/docs/docs/getting-started/quick-start.md`
  - `src/content/docs/docs/concepts/confidence.md`
  - `src/content/docs/docs/pipelines/verifiers.md`
- **Eleven stub pages** carrying a `:::caution[Content migration in progress]`
  banner. Your job is to replace every stub with real content, and add the new
  pages listed in §3, by **moving** content from the four product READMEs.

Source material (read-only — never edit these repos):

| Source | Path | Size |
|---|---|---|
| P-Ork README | `/Users/adalton/Development/github/P-Ork/README.md` | 2,887 lines |
| Confidence explainer | `/Users/adalton/Development/github/P-Ork/CONFIDENCE-EXPLAINED.md` | already migrated → `concepts/confidence.md` |
| Gateway README | `/Users/adalton/Development/github/P-Ork-Gateway/README.md` | 731 lines |
| Service MCP README | `/Users/adalton/Development/github/P-Ork-Service-MCP/README.md` | ~230 lines |
| Gateway MCP README | `/Users/adalton/Development/github/P-Ork-Gateway-MCP/README.md` | ~240 lines |

## 2. Rules (do not re-litigate)

1. **Move, don't rewrite.** Prose is preserved near-verbatim. You may: fix
   heading levels, convert README `§`/anchor cross-references into relative
   page links, split one README section across the pages mapped below, and add
   one- or two-sentence intros so a page stands alone. You may NOT: paraphrase
   for style, drop caveats/gotchas (these READMEs are unusually honest — the
   caveats are the value), or invent new claims about the product.
2. **Every page follows the exemplar pattern:** frontmatter (`title`,
   `description`, `sidebar.order`), a short orienting intro, thorough
   explanation, then straightforward copy-paste examples (YAML/`curl`/code
   blocks preserved from the README). Use Starlight `:::note`/`:::caution`
   asides for the README's blockquote warnings where it reads naturally.
3. **Remove the migration-caution banner** from a stub only when its content is
   fully migrated. When you finish, zero banners must remain.
4. **Sidebar ordering** is via `sidebar.order` frontmatter, matching the order
   pages appear in the tables below (top = 1). Directories are already wired in
   `astro.config.mjs` — only touch that file if a build error tells you to.
5. **Links:** internal doc links are root-relative with trailing slash, e.g.
   `/docs/pipelines/schema/`. References to repo files that stay in the repo
   (samples, fixtures, tests) are written as inline code paths, not links.
6. **Do not touch:** `src/pages/index.astro` (landing page),
   `src/styles/global.css`, `public/screenshots/`, the three exemplar pages.
7. **Skip entirely:** the P-Ork README's "Mac Setup (current machine)" and
   "OpenClaw Identity Files" sections (machine-specific, not product docs), and
   anything in `logs/`.
8. Work through §3 in order, committing after each sidebar group with message
   `docs: migrate <group>` so progress is reviewable.

## 3. The content map

Every `##`/`###` section of each README maps to exactly one page below.
Before writing, skim the README section list to confirm nothing is missed; if
you find a section not mapped here, put it on the page whose topic it clearly
belongs to and note it in the final report.

### 3.1 Getting Started (`docs/getting-started/`)

| Page | Source |
|---|---|
| `quick-start.md` | DONE (exemplar) |
| `installation.md` (new) | P-Ork README "Development Setup" + "Running Tests"; Gateway README "Quick Start" (full version — quick-start.md has the abbreviated one). Include the SQLite-vs-Postgres note from "Database". |

### 3.2 Concepts (`docs/concepts/`)

| Page | Source |
|---|---|
| `confidence.md` | DONE (exemplar) |
| `architecture.md` (new) | P-Ork README "Project Overview", "Tech Stack", "Project Structure" (the tree can be trimmed to the top two levels), plus a prose walk-through of the flow: webhook → normalise → resolve → run steps → executors → Gateway → providers/MCP. Include a Mermaid diagram of that flow (Starlight renders ```mermaid fences via its default config — if the build disagrees, use a fenced text diagram instead and say so in your report). |
| `stages.md` | README §3c "Pipeline Stages (testing vs production)" |
| `readiness.md` | README "Promotion readiness (owner-defined criteria)" + "Criteria builder (guided UI)" + the `readiness.*` knob rows from CONFIDENCE-EXPLAINED §9 quick-reference table (copy those rows here; `concepts/confidence.md` links here for them). |

### 3.3 Pipelines (`docs/pipelines/`)

| Page | Source |
|---|---|
| `schema.md` | README §4 "Pipeline Config Schema (YAML)" |
| `steps.md` | README §4a "Step Library" |
| `verifiers.md` | DONE (exemplar) |
| `parallel.md` (new) | README §7 "Parallel Groups" + §7a "Fan-Out — Dynamic Parallelism" |
| `flow-control.md` (new) | README §10 "Flow Control" + "Step and Run Status Reference" + §10a "Conditional Steps (`when:`)" + §10b "Per-Step Failure Policy (`on_failure`)" + §13 "Retry Logic" |
| `grounding.md` (new) | README "Grounding (shadow mode)" + "Deterministic checks & enforced grounding (Phase 1)" |
| `calibration.md` (new) | README "Calibration (Phase 3)" — this is the technical reference; `concepts/confidence.md` is the plain-language version; cross-link both ways. |
| `prompts.md` (new) | README §11 "Prompt Construction" + §12 "Session Keys" |
| `notifications.md` (new) | README §9a "Pipeline Notification Channels" + §10c "Outbound Notification Steps (`executor: notify`)" |
| `scheduling.md` (new) | README §8 "Cron Scheduler" |
| `human-in-the-loop.md` (new) | README's human executor material (in §9's executor list + the Approvals rows of the UI table) — everything about `executor: human`, approval channels (Telegram/Slack/Teams), per-team routing, `/ui/approvals`. |

### 3.4 Sources & Executors (`docs/integrations/`)

| Page | Source |
|---|---|
| `webhooks.md` | README §1 "Webhook Intake & Source Detection" + §2 "Normalisation Layer" + §2a "Generic Source" + §3 "Pipeline Resolution" + §3a "Idempotency & Deduplication" + "Adding a New Source Parser" |
| `executors.md` | README §9 "Executor Adapter Pattern" + "Adding a New Executor" + Gateway README "Differences from the OpenClaw executor" |
| `mcp.md` (new) | Both MCP READMEs, condensed but complete: what each server is, `explain` tool semantics (Service MCP), tool inventories, install + client config for each, write-path design notes. Title: "MCP servers". |

### 3.5 UI & Insights (`docs/ui/`)

| Page | Source |
|---|---|
| `overview.md` | README "UI" intro + the full page/route table + "Running a pipeline manually" |
| `run-detail.md` (new) | README "Run log" + "Live tail" + "Agent trace" + "Accuracy feedback" (run-level and per-step) |
| `insights.md` (new) | The eight Insights rows of the UI table, expanded into prose per page, + "Agent Library" section |
| `marking-queue.md` (new) | README "Marking queue" material (UI table row + the marking-queue parts of CONFIDENCE-EXPLAINED §10 already summarised in confidence.md — link there rather than duplicating) |

### 3.6 Gateway (`docs/gateway/`)

| Page | Source (all Gateway README) |
|---|---|
| `overview.md` | "Overview" + "Quick Start" + "Directory Structure" (trim tree to two levels) |
| `configuration.md` (new) | "Configuration (`config.yaml`)" — all subsections: server, identity, limits, mcp_servers, providers, logging, observability |
| `providers.md` (new) | "Model Routing" + "Azure OpenAI" + provider-specific notes |
| `agents.md` (new) | "Creating Agents" — agent.yaml, soul.md, startup validation, hot reload |
| `protocol.md` (new) | "WebSocket Protocol" — auth, agent request, trace event types, session keys, concurrency & cancellation |
| `api.md` (new) | "REST Endpoints" + "/health response" + "Agent management endpoints" |
| `operations.md` (new) | "Prometheus Metrics" (+ scrape config, PromQL examples) + "Environment Variables" + "Performance Notes" + "MCP Transport Notes" |
| `pork-integration.md` (new) | "P-Ork Integration" + "Gateway MCP (agent authoring)" pointer |

### 3.7 Operations (`docs/operations/`)

| Page | Source |
|---|---|
| `deployment.md` | README "Service Configuration" + "Database" + "Kubernetes Deployment" + Dockerfile mention from project structure |
| `observability.md` (new) | README §15a "Prometheus Metrics" + §15b "OpenTelemetry Tracing" + the logging material (`logs/` rotating files, access log split) |
| `teams.md` (new) | README §3b "Team Attribution" |
| `runs.md` (new) | README §14 "Run Storage" + §5a "Artifact Storage" |

### 3.8 Reference (`docs/reference/`)

| Page | Source |
|---|---|
| `api.md` | README §15 "Management Endpoints" (the annotated endpoint list, formatted as endpoint-per-heading with the README's inline comments as prose) |
| `analytics-api.md` (new) | README §15c "Pipeline/Step/Agent Read + Analytics Endpoints" |
| `write-api.md` (new) | README §15d "Pipeline/Step Write, Validate, and Delete Endpoints" + §15e "The P-Ork Service MCP" (short section linking to `/docs/integrations/mcp/`) |
| `llm-output.md` (new) | README §5 "LLMOutput — The Step Contract" |
| `config.md` (new) | The full annotated `samples/config.yaml.example` walk-through from "Service Configuration" (if that page and deployment.md would duplicate, deployment.md keeps the operational guidance and this page keeps the field-by-field reference; cross-link). |

### 3.9 Design (`docs/design/`)

| Page | Source |
|---|---|
| `decisions.md` | README "Key Design Decisions" table, verbatim |
| `extending.md` (new) | README "Adding a New Source Parser" / "Adding a New Executor" / "Adding a Library Step" (these also appear condensed on webhooks/executors/steps pages — here they live in full; keep the copies short there and link here). |

## 4. Verification (all must pass before you're done)

1. `npm run build` — clean, zero warnings about missing pages.
2. `grep -rn "Content migration in progress" src/content` → no hits.
3. Every README `##`/`###` section from §3's sources is present on its mapped
   page (spot-check by grepping distinctive phrases).
4. Every internal `/docs/...` link in the content resolves to a built page
   (`grep -rho '/docs/[a-z-]*/[a-z-]*/' src/content | sort -u` and check each
   against `dist/`).
5. Report: list any README section you found unmapped and where you put it,
   and any place you had to deviate from a rule.

## 5. Out of scope (do not do)

- Shrinking the product repos' READMEs (phase 2, needs the owner's go-ahead).
- Editing anything outside this repo.
- The landing page, theme, screenshots, hosting/deploy config.
