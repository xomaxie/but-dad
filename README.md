# But Dad

But Dad is a small project for producing deeply detailed specs through a bounded writer-vs-coach loop.

## What it is

The core idea is simple:
- a **writer** drafts an implementation-ready spec
- a **coach** nitpicks, argues, and challenges weak assumptions
- the coach should support major critiques with web research
- the loop runs for a bounded number of turns
- the caller receives a polished final spec with sources and unresolved assumptions clearly marked

## Repository layout

- `AGENTS.md` — product and architecture brief for humans and coding agents
- `.github/workflows/openhands-resolver.yml` — issue-driven OpenHands automation
- `.github/scripts/openhands_run.py` — helper script used by the workflow
- `docs/planning/` — project planning notes
- `src/but_dad/` — project package
- `tests/` — local tests

## OpenHands automation

This repo includes the same OpenHands issue automation pattern used in the two reference automation repositories:
- label an issue with `openhands`, or
- comment with `@openhands ...`

See `/opt/agent-zero/usr/workdir/but-dad/docs/planning/openhands-automation.md` for setup details.

## Local development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest
```
