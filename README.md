# But Dad

But Dad is a small project for producing deeply detailed specs through a bounded writer-vs-coach loop.

## What it is

The core idea is simple:
- a **writer** drafts an implementation-ready spec
- a **coach** nitpicks, argues, and challenges weak assumptions
- the coach should support major critiques with web research
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
