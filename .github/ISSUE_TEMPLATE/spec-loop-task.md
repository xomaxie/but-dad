---
name: Spec loop task
about: Plan or implement part of the But Dad spec writer and nitpick coach workflow
labels: planning, spec-loop
---

## Base brief
Use `AGENTS.md` in the repository root as the default project brief for this issue.

But Dad is a research-backed spec drafting system that runs a writer agent against a nitpicking coach agent.

## Goal
Describe the smallest useful change needed for this issue.

## Desired outcome
- clearer product behavior
- tighter requirements or implementation steps
- tests or validation notes when code changes are involved

## Constraints
- Keep the writer/coach loop explicit and easy to inspect.
- Default to six writer turns and six coach turns unless the issue says otherwise.
- Coach critiques should be grounded in web research when the workflow is executed.
- Prefer small, composable changes over broad rewrites.

## Acceptance criteria
- [ ] Scope is clear
- [ ] Relevant docs or code are updated
- [ ] Validation approach is described or executed
- [ ] Follow-up work is called out when necessary
