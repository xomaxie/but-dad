# fast-agent experiment findings

_Generated on 2026-03-31._

## What was added

- `src/but_dad/fast_agent_experiment.py` wires a minimal fast-agent evaluator-optimizer experiment for the But Dad writer/coach loop.
- `docs/experiments/fast-agent-sample-output.md` stores a deterministic dry-run transcript for review.
- The live fast-agent path expects the writer to act as the generator and the coach to act as the evaluator.

## Runnable commands

Dry run:

```bash
python -m but_dad.fast_agent_experiment --topic "Produce an implementation-ready spec for a webhook-based issue handoff." --output docs/experiments/fast-agent-sample-output.md
```

Live run once fast-agent, model credentials, and MCP server config are available:

```bash
python -m but_dad.fast_agent_experiment --live --config-path path/to/fastagent.config.yaml --model sonnet --topic "Produce an implementation-ready spec for a webhook-based issue handoff." --output docs/experiments/fast-agent-live-output.md
```

## Why evaluator-optimizer is the best minimal fit

- It already models a generator/evaluator loop.
- `max_refinements=5` gives at most 6 writer drafts total.
- The coach can return a quality rating plus actionable critique on each pass.
- The final artifact stays inspectable because the loop remains explicit.

## Malachi status

No MALACHI-related environment variables were present and no Malachi-specific fast-agent configuration was checked into the repo, so a live Malachi-backed run could not be verified.

Evidence:
- Environment inspection found no variable names containing MALACHI.
- The repo does not ship a fastagent.config.yaml with a Malachi model binding.

This is an inference from local environment inspection on 2026-03-31; it is not proof that Malachi is impossible everywhere.

## Verdict

fast-agent looks like a **good structural fit** for But Dad's loop, but the current environment does **not** prove operational fit yet.
The missing piece is a live run with a real model plus research-capable MCP servers so the coach can ground critiques in current sources.

## Follow-up work

1. Supply a `fastagent.config.yaml` that defines the search/fetch MCP servers used by the coach.
2. Retry the live run with Malachi if credentials or a supported model binding become available.
3. Save one real transcript from the live run and compare the resulting spec quality against the existing loop state approach.

## Reference links

- fast-agent docs: https://fast-agent.ai/
- fast-agent workflow docs: https://fast-agent.ai/agents/workflows/
- fast-agent model docs: https://fast-agent.ai/models/
- fast-agent package: https://pypi.org/project/fast-agent-mcp/
