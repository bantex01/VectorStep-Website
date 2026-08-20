---
title: Why I built VectorStep
description: OpenClaw showed me what agentic tooling could do. It also showed me why I'd never point it at production — so I built the gateway that would let me.
date: 2026-08-24
tags: [origin-story, agentic-ai, gateway]
excerpt: OpenClaw is a brilliant personal AI assistant. Using it for real work made it obvious why "brilliant personal assistant" and "safe to run against production" are two different design problems - and that the second one didn't have an open-source answer yet.
---

I was a bit late to the party with [OpenClaw](https://myclaw.ai/) but arrived unfashionably late around March this year. When I started reading about implementing a personal AI assistant I couldn't necessarily see what I might need a fleet of agents for in my personal life. I have no interest in having AI check-in for flights (I don't go on many flights these days) or produce a morning briefing (what would AI brief me on?) but I have for many years tried to find ingenious ways to try and make my weekend hobby of sports betting profitable by delving into stats using tools such as Splunk and streaming odds into grafana cloud and analysing from there. What interested me wasn't really the betting itself, but the idea of building a system that could continuously watch a bunch of data, spot something interesting and then help me decide what to do with it.

So it was this use-case that got me tinkering with Openclaw. I liked the idea of agents just continually keeping context and essentially getting to know you and keeping a memory. But in practice, in my opinion, memory management and the idea that your personal agents just "remember" and "know" stuff about you is still some way off.

But what tinkering with these tools and features did do is cement my thinking on how AI could be useful in my working life.

I have worked in observability for an awfully long time and I have heard the term AIOps used so often and for so long i've almost become immune to anything an article says after it. Quite frankly, AIOps used to mean some sort of automation and at best some machine learning. At a stretch you could tag that "Artificial Intelligence", but not as we know it today with LLMs.

Things have moved on though, and genuine alert triage and remediation is possible today. There are loads of tools already out there that do just that.

Most of my career has been spent in highly regulated industries like banking, insurance and medicine. Using AI is becoming more prevalent for engineers in their every day workflow (copilot etc.) but is still fairly scarce when moving into production and asking AI to work completely autonomously.

That got me thinking about something slightly broader than observability. If AI agents were going to become genuinely useful at work, I didn't think they should necessarily be limited to one particular use case. An incident response workflow is one example, but there are potentially thousands of workflows across a company where you might want an agent to gather information, make a decision, take an action and then move on to the next step.

At the time, I was also a bit naive about what tooling already existed. I knew there were plenty of workflow engines and orchestrators, and obviously there were already tools for building AI agents, but I wasn't really seeing the combination I was thinking about. Something that treated an AI workflow as a series of explicit steps, where each step could have its own inputs, outputs, checks and rules around whether the workflow should be allowed to continue.

I also wanted it to feel like something an engineer would actually want to use. I'm a big fan of configuration and infrastructure as code, so I didn't want to build something where the important parts of the workflow lived inside a visual editor that was difficult to version, review, reproduce or understand. 

I wanted to be able to look at a pipeline in a repository, understand what it was going to do, see the decisions it could make and check it into source control like any other piece of software.

And that got me thinking about (yes, I do a lot of thinking about this sort of thing!) a more fundamental question. 

If we are going to break an AI-driven workflow down into explicit steps, what should determine whether it is allowed to move from one step to the next?

## So, how do we gate those steps?

This is essentially the question that led me to VectorStep.

Disclaimer: the original tool was called "PORK", for Prompt Orchestrator. I still love that name, but sensible me thought VectorStep sounded more professional!

I started thinking about each step in an AI workflow as something that shouldn't automatically be trusted just because an LLM had produced an answer. If a step is going to trigger another step, call an API, make a recommendation or ultimately take some action, there should be some way of deciding whether the output is good enough to proceed.

I originally just asked the LLM to report back its own confidence on a task and, in my initial testing, that worked surprisingly well, but I should add here, I think that's because I was very deliberate about the scope of the step and the very specific instructions for the agent (prompt) and its very limited soul (essentially what you tell your agent it can/can't do). 

For now, i'll leave that subject there but I do have some further articles and guides on this subject in the dcos site so please have a look if you want to know more about writing good agents and prompts.

But asking an LLM to mark its own homework is fraught with risk, as you can imagine, so this mechanism evolved. In some cases you might want independent verification. In others you might need evidence from a known source, a deterministic check, or some understanding of how well the agent has performed historically. 

I layered all these checks and balances into what I call the "Truth Vector" (is that woefully corny?).

So VectorStep is my attempt to build all of that into the workflow itself.

## What actually makes up the Truth Vector?

The first version was very simple. The agent did a piece of work and told me how confident it was in the result. That was useful, but I didn't want to rely on the agent marking its own homework, so I started looking at what other signals I could use.

The Truth Vector is currently made up of five signals. They each answer a slightly different question about the output of a step.

**Confidence** — how confident is the agent in the result it has produced?

**Verification** — can another process independently check the result?

**Grounding** — can the important claims in the result be backed up by actual evidence?

**Deterministic checks** — does the output pass rules that don't require another LLM to make a judgement?

**Calibration** — does this particular agent's confidence actually bear any relationship to how often it is right?

In my opinion, I don't think any one of these is necessarily enough on its own.

An agent can be highly confident and wrong. A verifier can be wrong. Evidence can be incomplete or misleading. A deterministic check can tell you that something meets a particular rule without telling you whether the overall answer makes sense.

The idea is that these signals give me different ways of looking at the same decision.

And importantly, I'm not trying to turn all of this into one magic number that says "the AI is 87% trustworthy". That would just move the problem somewhere else.

### You are the weakest link. Goodbye!

One of the decisions I made fairly early on was that I didn't want to simply average these signals.

Imagine an agent reports 95% confidence. The verifier is happy. The grounding looks good. But a deterministic check that is critical to the particular action fails.

I don't think it makes sense to say that the first three signals were good enough to outweigh the one that failed.

If that check is important enough to be a requirement for the next step, the workflow should stop.

This is why I tend to think of the Truth Vector less as a score and more as a collection of evidence about whether a step has earned the right to continue.

And that last bit is important because the answer isn't always the same.

### Not every action deserves the same level of trust

I don't think there is a single threshold at which an AI becomes "trusted".

If an agent is writing a draft for me to review, I'm happy to accept a very different level of uncertainty than I would if it was about to make a change to a production system.

The same is true across pretty much any business.

An agent might be allowed to categorise an incoming support ticket with relatively little scrutiny. Asking it to send a customer an email without human approval is a different proposition. Asking it to change something in production is different again.

So rather than asking:

“Is this AI trustworthy?”

it's probably better to ask:

“Has this particular step produced enough evidence for the action we are about to take?”

It belongs to the step, the evidence available to that step and the consequences of allowing it to continue.

And this is where I think treating an AI workflow as a series of explicit steps becomes particularly useful.

### An example

Take a fairly simple example from the sort of work I've spent most of my career around: an agent investigating a production alert.

The first step might gather information from several sources and produce a triage report.

At rung zero, that's all we're doing. The agent investigates and gives us an answer.

Now we can start adding some gates.

Perhaps the agent needs to have a confidence above a certain level.

Then we might independently verify some of its conclusions.

We might require the important claims in the report to be backed by evidence from the systems it has queried.

We might have a deterministic check that says the proposed remediation is only valid for a particular type of alert.

And, once we've accumulated enough historical runs, we can start asking whether the confidence the agent reports is actually useful.

At each point, the workflow has more information available when deciding whether to continue.

And if one of the things we've decided is essential fails, the workflow doesn't need to pretend everything is fine. It can stop, retry, or escalate to a human.

That, to me, is much more interesting than simply asking an LLM to give me an answer and then deciding whether I happen to like the answer.


## So what actually is VectorStep?

This is where VectorStep started to take shape.

I wanted a way to describe an AI workflow as a series of explicit, version-controlled steps, while also making the conditions for progressing between those steps explicit.

The AI can do the work. It can use tools, gather information, reason over it and produce an output. But the workflow gets to decide what happens next.

Sometimes that will be another automated step.

Sometimes it will be a retry.

Sometimes it will be a human.

And sometimes the correct decision is simply to stop.

VectorStep is my attempt to make those decisions a first-class part of the workflow rather than something that gets bolted on afterwards.

It's open source, it's designed to be engineer-friendly and the workflows are defined as code. I'm deliberately trying to make the whole thing inspectable and reproducible rather than hiding the important decisions inside a visual workflow builder.

I don't think this solves "AI trust", i'm not sure that's possible right now.

I don't think VectorStep can tell you whether an AI agent is telling the truth with absolute certainty, that's a much harder problem because a verifier can be wrong, a source can be wrong. An agent can find convincing evidence for the wrong conclusion. And no amount of configuration can remove uncertainty from a system that is ultimately making decisions in a changing environment.

What I think we can try and do though, is make that uncertainty much more explicit.

Instead of an agent simply producing an answer and the system assuming it is good enough, we can ask what evidence we have for that answer, what checks it has passed, how the agent has performed historically and whether that is sufficient for the action we are about to allow.

That's the idea behind VectorStep.

Don't blindly trust the agent. Give it a way to earn the right to take the next step.

I'm going to be exploring that idea through the project, and I'm sure some of my assumptions will turn out to be wrong along the way.

I'm particularly interested in hearing from people who are trying to put agents into real production workflows, especially where the consequences of getting the decision wrong actually matter.

If that's the kind of project you'd want to poke at, break, or contribute to, the code and docs are at
[vectorstep.io](https://vectorstep.io).
