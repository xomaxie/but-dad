# But Dad

But Dad is a reusable spec-improvement tool built around a bounded **writer vs. coach** loop.

It helps turn rough ideas into implementation-ready specs by having:

- a **writer** drafts and revises the spec,
- a **coach** challenge ambiguity, omissions, and weak assumptions,
- optional **live research** to support stronger critiques,
- and a consistent artifact bundle for review.

## What But Dad is for

Use But Dad when you want a stronger version of:

- a product spec,
- implementation plan,
- architecture note,
- MCP/tool design,
- rollout plan,
- or any serious requirements document.

But Dad is designed to be:

- **bounded** — finite turns, explicit stop conditions,
- **inspectable** — transcripts, metrics, summaries, and sources are saved,
- **reusable** — exposed as an MCP tool for clients and local workflows,
- **practical** — preview mode for deterministic iteration, live mode for research-backed critique.

## Core concepts

### Writer
Produces the baseline draft and incorporates feedback into clearer, more testable requirements.

### Coach
Nitpicks aggressively, pushes on unclear claims, and in live mode can ground major objections in current sources.

### Artifact bundle
Each run writes a final spec plus supporting transcripts and metadata so the result can be inspected instead of treated as a black box.

## Repository layout

- `src/but_dad/` — MCP server and loop implementation
- `tests/` — regression and integration-oriented tests
- `docs/planning/` — planning and design notes
- `docs/experiments/` — experiment outputs and proof artifacts
- `skills/use-but-dad-spec-loop/` — companion skill for when to use the tool

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

To include the fast-agent-backed live path:

```bash
pip install -e '.[dev,fast-agent]'
```

## Running tests

```bash
PYTHONPATH=src .venv/bin/python -m pytest -q
```

## MCP server

Start the server over stdio:

```bash
PYTHONPATH=src .venv/bin/python -m but_dad.mcp_server --transport stdio
```

The server exposes one primary tool:

- `run_spec_loop`

## `run_spec_loop` overview

Key inputs:

- `topic` — the problem or spec goal
- `run_name` — stable artifact directory name
- `mode` — `preview` or `live`
- `context` — optional project background
- `constraints` — optional hard requirements
- `acceptance_criteria` — optional success conditions
- `time_budget_seconds` — optional whole-run timeout

### Modes

#### `preview`

Use preview mode when you want:

- deterministic local verification,
- a fast dry run,
- or a first serious pass on a draft.

#### `live`

Use live mode when you want:

- research-backed coach objections,
- stronger pressure on factual correctness,
- or a more realistic end-to-end run.

Live mode depends on caller-supplied local configuration. This repo does **not** commit fast-agent config files or model credentials.

Set local environment variables if needed:

```bash
export BUT_DAD_FASTAGENT_CONFIG_PATH=/absolute/path/to/fastagent.config.yaml
export BUT_DAD_FASTAGENT_MODEL=Malachi
```

## Output artifacts

Each run writes an artifact bundle under:

- `docs/experiments/mcp-tool/<run-name>/`

Typical outputs:

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

## Example payload

```json
{
  "topic": "Turn a tested writer-vs-coach workflow into a reusable MCP tool.",
  "run_name": "reusable-mcp-tool-spec",
  "mode": "preview",
  "time_budget_seconds": 180
}
```

## Companion skill

This repo bundles a companion skill here:

- `skills/use-but-dad-spec-loop/SKILL.md`

Use it when generating a meaningful spec, plan, design doc, architecture note, or implementation brief.
