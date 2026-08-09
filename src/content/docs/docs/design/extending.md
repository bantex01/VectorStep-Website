---
title: Extending VectorStep
description: How to add a new source parser, a new executor, or a new library step — the three extension points that need no other codebase changes.
sidebar:
  order: 2
---

VectorStep does not accept external contributions — but it is Apache-2.0, so
extending your own copy is expected and supported (see
[Licence & contributions](/docs/about/licence-and-contributions/)). These are
the three extension points designed to need no other changes: source
parsers, executors, and library steps. This page is the complete reference
for all three — condensed pointers to it also appear on
[Webhooks](/docs/integrations/webhooks/),
[Executors](/docs/integrations/executors/), and
[Steps](/docs/pipelines/steps/).

## Adding a new source parser

1. Create `src/normaliser/<source>.py`
2. Implement `BaseParser` — produce a `NormalisedContext`
3. Register in `src/normaliser/__init__.py` source map

## Adding a new executor

1. Create `src/executors/<name>.py`
2. Implement `BaseExecutor` — accept `StepConfig` + context dict, return `LLMOutput`
3. Register in `src/executors/__init__.py` executor map
4. Reference by name in pipeline YAML step `executor:` field

No other changes required in either case.

## Adding a library step

1. Create `steps/<your-step-name>.yaml` with at minimum `name`, `executor`,
   and `executor_config.agent`
2. Run `POST /reload` (or send SIGHUP) — the step will appear in `/ui/steps`
   immediately
3. Reference it in any pipeline with `- use: <your-step-name>`

The `steps/` directory is gitignored — steps are personal to your
deployment. Copy starter definitions from `samples/steps/` and adapt them,
or write your own. See
`samples/pipelines/alert-triage-investigation-using-steps.yaml` for a worked
example of a pipeline that uses library steps.
