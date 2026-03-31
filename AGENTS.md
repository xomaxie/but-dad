# But Dad AGENTS.md

## Project purpose
But Dad is a lightweight repository for a spec-first adversarial loop.

The product goal is to generate an implementation-ready specification by pairing:
- a **writer** agent that drafts and revises a spec
- a **coach** agent that nitpicks aggressively and supports major critiques with current web research

The default cadence is a bounded loop of six writer turns and six coach turns.

## Product direction
Optimize for:
- explicit, testable requirements
- pressure against ambiguity and hand-waving
- strong edge-case coverage
- a clean final deliverable with sources
- small, understandable orchestration code

Avoid:
- overbuilt agent frameworks
- hidden state that makes the loop hard to inspect
- feature creep from weak or irrelevant citations
- implementation work that is disconnected from the final spec artifact

## Current technical direction
- Language: **Python**
- Packaging: **pyproject.toml**
- Test runner: **pytest**
- Architecture: **small library + CLI-first workflow**

## Architecture principles
- Keep the loop deterministic where possible.
- Preserve a single living spec document across turns.
- Make critique structured enough to convert into spec edits.
- Separate orchestration, prompting, and source capture.
- Prefer boring, maintainable Python.

## Delivery guidance for issue work
When working an issue:
1. Start with the smallest useful step.
2. Prefer planning/docs first when scope is uncertain.
3. Keep prompts, loop state, and output formatting easy to audit.
4. Add tests for behavior that can be exercised locally.
5. Favor small PRs and crisp documentation.

## MVP bias
For now, prioritize:
- loop orchestration
- turn accounting
- structured critique records
- final spec assembly
- source appendix generation
- clear CLI or callable entrypoints

Defer unless explicitly requested:
- multi-provider abstractions beyond what is necessary
- UI layers
- complex persistence
- background job systems
- generalized agent marketplaces or plugin ecosystems

## Notes for autonomous coding agents
If an issue references this file, treat it as the default product and architecture brief. Keep changes local, incremental, and well-documented.
## Repository notes
- `SpecLoopState.add_draft()` and `.add_critique()` enforce the configured turn budgets via `TurnLimitError`.
- The CLI entrypoint is `but-dad run --input <json> --output <markdown>`, consuming an explicit `turns` array and rendering a markdown artifact.
