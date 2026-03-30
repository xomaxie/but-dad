# But Dad project brief

## Goal

Build a small, dependable system for creating implementation-ready specs through a bounded adversarial loop.

## Core workflow

- a **writer** drafts and revises the spec
- a **coach** nitpicks, argues, and pushes on ambiguity
- substantive coach critiques should cite current web research
- the loop is bounded to **6 writer turns** and **6 coach turns** by default
- the final artifact returned to the caller is a deeply detailed spec with sources and unresolved assumptions called out clearly

## Product principles

- optimize for sharpness of requirements, not maximum autonomy
- keep the loop inspectable and easy to replay
- preserve a single living spec across turns
- treat web research as support for critique, not as automatic scope expansion
- make outputs easy for a caller or downstream coding agent to use directly

## Likely deliverables

- loop orchestration
- transcript or dispute log capture
- citation handling and source appendix generation
- final spec packaging
