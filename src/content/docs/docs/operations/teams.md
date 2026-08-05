---
title: Team attribution
description: Attributing runs and token spend to owning teams via per-team webhook tokens.
sidebar:
  order: 3
---

To show LLM token spend broken down by owning team/department, every run is
tagged with a `team` — used for the `vectorstep_pipeline_tokens_total` metric (see
[Observability](/docs/operations/observability/)) and the `GET
/runs?team=` filter.

**Team comes from the Bearer token that authenticated the webhook, not from a
field in the payload.** A self-reported `team` in a JSON body is spoofable and
easy to get wrong; tying team to the auth credential makes attribution
authoritative, and "onboarding a team" becomes synonymous with "issuing them a
token" — a natural gate.

## Configuration

`auth.teams` replaces the single `auth.token`:

```yaml
auth:
  teams:
    - name: payments
      token: ${VECTORSTEP_WEBHOOK_TOKEN_PAYMENTS}
    - name: platform
      token: ${VECTORSTEP_WEBHOOK_TOKEN_PLATFORM}
  # token: ${VECTORSTEP_WEBHOOK_TOKEN}   # legacy single-token form, still supported
```

Generate each team's token with `openssl rand -hex 24` (or any other source of
cryptographically random bytes) — a 48-character hex string. There's no token
issuance endpoint; this is a plain shared secret, handled the same way as
`executors.gateway.token` and the Telegram `bot_token` elsewhere in
`config.yaml`: either resolved from an environment variable via `${ENV_VAR}`
as shown above, or written directly into `config.yaml` if you're not using
env vars for secrets — `config.yaml` is gitignored either way. Regenerate it
yourself locally rather than reusing a value that's appeared anywhere else (a
chat transcript, an issue tracker, etc.), since a real secret should only ever
exist in the one place it's actually used.

- If `auth.teams` is set, each entry's token is checked on `POST /webhook`; a
  recognized token resolves the run's `team`, an unrecognized or missing token
  still 401s exactly as before — no separate rejection path is needed for "no
  team supplied," since an unattributed/unauthenticated call already fails
  auth.
- If `auth.teams` is absent and the legacy `auth.token` is set, behaviour is
  unchanged — single shared token, every run's `team` is `None`
  (unattributed). If both are set, `auth.teams` wins silently.
- If neither is set, `POST /webhook` is unauthenticated, same as today.

## Non-webhook runs

Non-webhook runs don't have a caller/token to resolve team from:

- **Scheduled (cron) runs** declare `team:` directly on the pipeline's
  `schedule:` block — trusted because it's git-controlled config, not
  external input.
- **Sub-pipeline calls** (`executor: pipeline`) inherit the parent run's
  `team` automatically, the same way they inherit `labels`/`metadata`, and it
  can be overridden per-call via `context: {team: "..."}` like any other
  field.

## Team budgets

Converting tokens to a dollar figure, and setting an advisory monthly budget
per team, is covered in [Cost accounting](/docs/operations/cost-accounting/).
The `openclaw` executor's lack of token reporting still applies there too — a
team running mostly `openclaw` steps will undercount regardless, which is why
every cost aggregate carries an "unpriced steps" annotation rather than
silently showing a possibly-partial total as if it were complete.
