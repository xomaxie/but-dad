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
- `.github/ISSUE_TEMPLATE/` — issue templates for OpenHands-friendly tasks
- `docs/planning/` — project planning notes
- `src/but_dad/` — project package
- `tests/` — local tests

## OpenHands automation

This repo includes the same OpenHands issue automation pattern used in the other automation repositories:
- label an issue with `OpenHands`, or
- comment with `@openhands ...`

See `docs/planning/openhands-automation.md` for setup details.

External prerequisites still apply:
- GitHub Actions must be enabled and able to run for the repository/account.
- `OPENHANDS_API_KEY` must be configured in repository secrets.

## Local development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest
```
