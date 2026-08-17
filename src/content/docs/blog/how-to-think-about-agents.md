---
title: How I think about agent design
description: Why narrow, sparingly-tooled agents beat broad capable ones once anything they touch matters — the philosophy behind VectorStep's agent-design guide.
date: 2026-09-07
tags: [agents, design, philosophy]
excerpt: A capable agent with broad access is a demo. A narrow agent you can actually reason about is a production system. Here's why I keep splitting agents apart instead of making them smarter.
---

[PLACEHOLDER — draft skeleton, not full prose yet. Sketch below is meant to
be expanded, not published as-is.]

The instinct when building an agent is to make it more capable: give it more
tools, let it handle more of the job, trust it to figure out the rest. That
instinct is right for a personal assistant — it's basically what makes
[OpenClaw](/blog/why-i-built-vectorstep/) compelling. It's wrong for
anything you'd call production.

## The temptation

- One agent that triages, investigates, and remediates feels efficient.
  It isn't — its confidence number ends up meaning three different things
  depending on which part of the job it was doing at the time.
- "Just give it all the tools, let it decide" feels flexible. It's actually
  the opposite: more tools is a bigger blast radius and a noisier decision
  space, not more capability where it counts.

## What I do instead

- Split by responsibility, not by convenience. Each agent earns a narrow
  job description and a confidence number that means one specific thing.
- Tools are a capability grant, not a courtesy — an agent can't reach past
  its `tools:` list, so keeping it short is a real security boundary, not
  just tidiness.
- Confidence has to measure "did I do the job," never "how scary does this
  look" — the two get conflated constantly, and it quietly wrecks
  calibration.

## The practical version

The engineering checklist version of this post lives at [Writing good
agents](/docs/guides/writing-good-agents/) — this post is the "why," that
page is the "how."

<!-- TODO: expand each section above into real prose. Consider adding a
     concrete before/after example (a bloated do-everything agent vs the
     split version) — the samples in the repo already show this split in
     practice (first-line-triage / sre-investigation / principal-sre). -->
