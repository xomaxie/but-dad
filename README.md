# But Dad

But Dad is a small project for producing deeply detailed specs through a bounded writer-vs-coach loop.

## What it is

The core idea is simple:
- a **writer** drafts an implementation-ready spec
- a **coach** nitpicks, argues, and challenges weak assumptions
- the coach should support major critiques with web research when the workflow is wired live
- the loop runs for a bounded number of turns
- the caller receives a polished final spec with sources and unresolved assumptions clearly marked

## OpenHands trigger

Create or open an issue, then add the `OpenHands` label to hand it off through the same webhook-driven flow used by `worklane`.

## Repository layout

- `AGENTS.md` — product and architecture brief for humans and coding agents
- `.github/ISSUE_TEMPLATE/` — issue templates for OpenHands-friendly tasks
- `docs/planning/` — project planning notes
- `src/but_dad/` — project package
- `tests/` — local tests

## Local development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest
```

## Reusable MCP server

Issue #10 added the reusable MCP server entrypoint. Issue #12 extends that tool with an opt-in live fast-agent/Malachi-backed execution path while keeping preview mode available for deterministic local verification.

Run the server locally over stdio:

```bash
python -m but_dad.mcp_server --transport stdio
```

The server exposes one structured tool:

- `run_spec_loop` — runs the bounded writer/coach loop and writes artifacts to `docs/experiments/mcp-tool/<run-name>/`

Example tool inputs:

- `topic`: the problem the loop should refine into a spec
- `run_name`: stable artifact directory name; defaults to a slugified topic
- `context`, `constraints`, `acceptance_criteria`: optional lists that seed the living draft
- `preferred_model_backend`: defaults to `Malachi` so downstream live wiring can preserve the intended backend
- `mode`: `preview` for deterministic local artifacts, `live` for the fast-agent/Malachi-backed path
- `config_path`: optional explicit live config path; if omitted, `BUT_DAD_FASTAGENT_CONFIG_PATH` is used before the placeholder default path
- `model`: optional explicit live model override; if omitted, `BUT_DAD_FASTAGENT_MODEL` is used before falling back to `Malachi`
- `time_budget_seconds`: optional whole-run timeout for live execution

Each run writes:

- `final-spec.md`
- `transcript.md`
- `transcript-writer.md`
- `transcript-coach.md`
- `transcript.json`
- `sources.json`
- `metrics.json`
- `run.json`
- `summary.json`
- `logs.txt`

### Verification

Install local dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev,fast-agent]'
```

Run the test suite:

```bash
PYTHONPATH=src .venv/bin/python -m pytest -q
```

Start the MCP server over stdio:

```bash
PYTHONPATH=src .venv/bin/python -m but_dad.mcp_server --transport stdio
```

Preview mode remains deterministic and requires no extra config.

To verify the live path locally:

```bash
export BUT_DAD_FASTAGENT_CONFIG_PATH=/absolute/path/to/fastagent.config.yaml
export BUT_DAD_FASTAGENT_MODEL=Malachi
```

Then invoke `run_spec_loop` with `mode="live"`. You can still override either value per request.

Example live-oriented payload:

```json
{
  "topic": "Upgrade preview MCP tool to the live Malachi-backed path.",
  "run_name": "issue-12-live-smoke",
  "mode": "live",
  "time_budget_seconds": 180
}
```

The current repo still does **not** check in a fast-agent config or Malachi credentials, so live verification depends on caller-supplied local configuration. Preview mode remains available for bounded, inspectable regression coverage.
