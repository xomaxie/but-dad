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

Issue #10 adds a reusable MCP server entrypoint with a deterministic preview loop.

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

Each run writes:

- `final-spec.md`
- `transcript.md`
- `transcript.json`
- `summary.json`

A deterministic sample run is checked in under `docs/experiments/mcp-tool/issue-10-preview/`.

### Verification

The current implementation intentionally ships a deterministic preview mode because the Issue #10 spec files referenced in the issue were not present in the repository checkout. That keeps the loop bounded, testable, and inspectable while still providing a reusable MCP tool contract and predictable artifact layout.
