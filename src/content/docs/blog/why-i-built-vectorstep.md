---
title: Why I built VectorStep
description: OpenClaw showed me what agentic tooling could do. It also showed me why I'd never point it at production — so I built the gateway that would let me.
date: 2026-08-24
tags: [origin-story, agentic-ai, gateway]
excerpt: OpenClaw is a brilliant personal AI assistant. Using it for real work made it obvious why "brilliant personal assistant" and "safe to run against production" are two different design problems — and that the second one didn't have an open-source answer yet.
---

Earlier this year I got deep into [OpenClaw](https://github.com/openclaw/openclaw)
— Peter Steinberger's self-hosted personal AI assistant. If you haven't seen
it: it's a gateway that gives an agent real access to your machine — files,
scripts, a browser — and lets it act on your behalf from Telegram or
WhatsApp. It can write its own new skills as it goes. It's genuinely
impressive engineering, and it didn't pick up 60k+ GitHub stars by accident.

I used it for real tasks, not just a demo. And the more I used it, the
clearer it became: OpenClaw isn't built for a production environment, and it
isn't trying to be. There's no confidence scoring on what the agent decides,
no calibration against whether it was actually right, no gate between "the
agent proposed this" and "this is now allowed to run unattended." For a
personal assistant acting on your own accounts, that's a reasonable trade —
you're the blast radius, and you're right there to notice if something's
off. For anything touching production infrastructure, it isn't a reasonable
trade at all. An agent that can rewrite its own capabilities and act broadly
on your behalf, with no record of *why* it decided what it decided, is not
something I'd want anywhere near a system other people depend on.

I didn't want less autonomy. I wanted the same autonomy, with a trust layer
underneath it.

## From "a service that talks to OpenClaw" to its own gateway

VectorStep didn't start as its own thing. The first version was just a
service that connected to OpenClaw's gateway — I was trying to bolt the
confidence and audit layer I wanted onto the outside of it. That worked
right up until it didn't: a trust model has to live at the gateway level,
not be layered on top after the fact. You can't retrofit an audit trail
onto a system that wasn't built to produce one.

So I built VectorStep Gateway — the same webhook-in, agent-acts-out shape
that made OpenClaw compelling, but with calibration and promotion-readiness
built into the core loop instead of bolted on: every decision carries a
confidence score, gets calibrated against outcomes over time, and has to
earn its way from "the agent thinks this is right" to "this is allowed to
run unattended" before it does.

## Why this, and why open source

Since starting this I've come across other tools aimed at "enterprise
agentic ops," so the gap wasn't as empty as I assumed going in. What I still
haven't found is one that's open source and built around the
trust/calibration/audit layer as the actual product, rather than a feature
bullet on top of an orchestration engine. If you know of one, I'd genuinely
like to hear about it.

I also wanted this to be something a DevOps engineer would actually want to
run, not something a platform team has to be sold on: YAML pipelines,
webhook triggers, self-hosted, Apache-2.0, no SaaS lock-in — the stuff that
makes a tool easy to adopt on a Tuesday afternoon without a procurement
conversation.

To be clear about where this is: VectorStep is early. It's one engineer's
opinionated answer to a problem I kept running into, not a finished
enterprise platform. If that's the kind of project you'd want to poke at,
break, or contribute to, the code and docs are at
[vectorstep.io](https://vectorstep.io).
