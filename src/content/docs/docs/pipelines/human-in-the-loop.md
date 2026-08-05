---
title: Human-in-the-loop
description: "executor: human — approval requests over Telegram, Slack, and Microsoft Teams, per-team routing, and the approvals UI."
sidebar:
  order: 11
---

`executor: human` pauses a pipeline until a person approves or rejects it, over
whichever chat channel the run's owning team is configured to use. This page
covers the executor itself, all three approval channels, per-team routing, and
where approvals surface in the UI.

## `executor: human` — Human-in-the-Loop (Telegram, Slack, Microsoft Teams)

**`executor: human`** sends an approval request and pauses the pipeline until
the operator approves or rejects, or `timeout_seconds` elapses.

| Outcome | confidence | proceed |
|---|---|---|
| Approved | 1.0 | true |
| Rejected | 0.0 | true — triggers `on_low_confidence` action |
| Timeout | — | step marked `failed` |

The `prompt_template` renders to the approval message text. Default timeout is
300s.

**Which channel a run uses is resolved per-team, not per-pipeline.** The same
`executor: human` step works unchanged for every team — VectorStep looks up the
run's `team` (resolved from the webhook auth token, see
[Team attribution](/docs/operations/teams/)) against `human_approval.teams` in
`config.yaml`, falling back to `human_approval.default`, falling back to the
legacy Telegram-only config if `human_approval` is omitted entirely. This
keeps team onboarding a config-only change (like issuing a token) rather than
requiring a new executor or a pipeline fork per team.

```yaml
- name: approve-remediation
  executor: human
  timeout_seconds: 600
  confidence_threshold: 0.5
  on_low_confidence: abort
  on_abort: notify
  prompt_template: |
    <b>Approve remediation for {{labels.service}}?</b>

    Proposed action: {{steps.investigation.next_step_context}}
```

### Config (`config.yaml`)

```yaml
human_approval:
  ui_base_url: https://vectorstep.internal.example.com   # required for the msteams channel — see below
  default:
    channel: telegram
  teams:
    team-a:
      channel: slack
      slack:
        bot_token: ${SLACK_BOT_TOKEN_TEAMA}
        app_token: ${SLACK_APP_TOKEN_TEAMA}
        channel_id: C0123456
    team-b:
      channel: msteams
      msteams:
        webhook_url: ${TEAMS_WEBHOOK_URL_TEAMB}
```

### Channels

| Channel | How the human responds | Requires |
|---|---|---|
| `telegram` | Inline-keyboard Approve/Reject buttons, resolved by the existing Telegram long-poll (`notifications/telegram_poller.py`). Requires a **separate** Telegram bot from OpenClaw (Telegram only allows one simultaneous `getUpdates` poller per bot token). | `human_approval.*.telegram.{bot_token,chat_id}`, or falls back to `notifications.telegram` |
| `slack` | Interactive Approve/Reject buttons via a Slack app's Socket Mode connection (`notifications/slack_poller.py`) — no public HTTPS endpoint needed, free on any Slack plan. | `human_approval.*.slack.{bot_token,app_token,channel_id}` |
| `msteams` | One-way notification (via a Power Automate webhook flow) linking to a VectorStep web page (`GET /ui/approvals/{token}`) where the human clicks Approve/Reject. Real interactive Adaptive Card buttons in Teams need a registered Azure Bot with a public callback endpoint — this deployment doesn't expose one, so Teams gets a notify-and-click-through flow instead. | `human_approval.*.msteams.webhook_url`, `human_approval.ui_base_url` |

If `human_approval` is omitted entirely, every `human` step behaves exactly as
before this feature existed — the single global `notifications.telegram`
bot/chat, no team awareness required.

:::caution[The `notifications.telegram` fallback only applies to the `telegram` channel]
It's a special case: a `human_approval.*` entry with `channel: telegram` and
no nested `telegram:` block reads `notifications.telegram` instead. `slack`
and `msteams` have no equivalent fallback — a `default:` or `teams.<name>:`
entry using either of those channels must include its own nested
`slack:`/`msteams:` credentials, exactly like any other channel entry.
Omitting it raises `RuntimeError: Slack/Teams approval channel missing ...`
the first time a run resolves to that entry.
:::

## Testing vs production behaviour

Approval behaviour differs depending on the pipeline's stage. See
[Pipeline stages](/docs/concepts/stages/) for the full testing-vs-production
model; the short version for `executor: human` and for `human`-type
deterministic checks (see [Grounding](/docs/pipelines/grounding/)) is that in
`stage: testing`, the external channel (Telegram/Slack/Teams) is **not**
sent — the decision is made entirely via VectorStep's own `/ui/approvals` — and a
timeout **auto-approves** rather than failing the step. In production, the
configured channel is used normally and a timeout marks the step `failed` as
described above.

## The approvals UI

| Page | Route | Description |
|---|---|---|
| Approvals | `/ui/approvals` | Every pending `executor: human` approval, regardless of channel — a universal fallback so a team isn't stuck if their primary chat channel (Slack/Telegram) is unreachable. No standalone sidebar entry; reached via a pending-count badge next to **Runs** (only shown when the count is non-zero) |
| Approval decision | `/ui/approvals/{token}` | Standalone page (no sidebar) reached via a direct token link — used by the Teams approval channel, which posts this link instead of an in-chat button since Teams interactive cards need a public Bot Framework callback endpoint this deployment doesn't expose (see `executors/human.py`'s `TeamsApprovalChannel`). Approve/Reject decision buttons post back to this same route |

## Where next

- **[Team attribution](/docs/operations/teams/)** — how a run's `team` is
  resolved from its webhook auth token, which in turn drives the channel
  lookup above.
- **[Pipeline stages](/docs/concepts/stages/)** — the full testing-vs-production
  behaviour matrix, including timeout and auto-approve differences.
- **[Grounding](/docs/pipelines/grounding/)** — `human`-type deterministic
  checks reuse this exact same approval subsystem.
