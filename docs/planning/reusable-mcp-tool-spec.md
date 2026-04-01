# But Dad reusable MCP tool — implementation-ready spec

## Summary
Build a reusable MCP server for the **But Dad writer-versus-coach spec loop** that exposes the tested workflow as a small set of MCP tools. The server must let any MCP-compatible client request a baseline spec, run a bounded adversarial improvement loop, and retrieve a final artifact bundle with transcript, sources, metrics, and terminal status.

This spec turns the current repo-local experiment into a **productized MCP capability**:
- reusable across repos and clients,
- transportable over MCP instead of hard-coded CLI entrypoints,
- bounded and observable,
- safe for non-interactive automation,
- and still grounded in the same writer/coach loop that was already tested locally with Malachi.

---

## Goals
1. Expose the spec-improvement workflow as an MCP server with stable tool contracts.
2. Support the tested writer/coach behavior: one writer, one nitpicking coach, bounded turns, research-backed critique, artifact output.
3. Make the workflow reusable from MCP clients such as OpenHands, Claude Desktop, Codex-style clients, custom wrappers, or repo automation.
4. Preserve auditability: every run must produce durable artifacts, run metadata, and a clear terminal state.
5. Keep the server implementation decoupled from any single frontend, repo, or issue-trigger mechanism.
6. Support Malachi-backed model execution and repo-approved research tooling.

## Non-goals
- Not a generic multi-agent orchestration platform.
- Not a general-purpose MCP research server for arbitrary tasks.
- Not a replacement for human approval of important specs.
- Not a GitHub webhook server.
- Not a PR-writing or code-modification MCP server in v1.
- Not a cloud-only service; local stdio operation is the primary target in v1.

---

## Product definition
The MCP server product is called **but-dad-mcp**.

It owns:
- the public MCP tool schema,
- run validation,
- turn-loop orchestration,
- Malachi model invocation,
- coach research collection,
- artifact persistence,
- run status reporting,
- and deterministic output shaping.

It does **not** own:
- GitHub issue labeling,
- webhook dispatch,
- OpenHands routing,
- or client-specific UX.

Those stay outside the MCP server and call it as a dependency.

---

## Primary use cases
1. **Generate an improved implementation spec from a prompt**
   - Caller sends a topic or rough request.
   - Server creates a baseline writer draft and iterates with a coach.
   - Server returns final spec plus artifacts.

2. **Improve an existing baseline spec**
   - Caller provides an existing draft/spec.
   - Server runs the coach/writer loop over that text.
   - Final output replaces or supplements the baseline.

3. **Use from repo automation**
   - A wrapper script or OpenHands task calls the MCP tool.
   - The wrapper stores or uploads the returned artifacts.

4. **Use interactively from an MCP client**
   - A developer asks the client to improve a spec.
   - The client invokes the MCP tool with input text and config.
   - The result is shown as a final spec plus links/paths.

---

## User-visible tool surface
The v1 MCP server must expose exactly these tools.

### 1. `spec_loop_run`
Runs the full bounded writer-versus-coach workflow.

**Purpose**
- Main entrypoint for producing or improving a spec.

**Input schema**
- `topic` (`string`, optional): short task/topic statement.
- `baseline_spec` (`string`, optional): existing draft/spec text.
- `context` (`string`, optional): extra project context, constraints, or repo notes.
- `max_writer_turns` (`integer`, optional, default `6`, min `1`, max `12`).
- `max_coach_turns` (`integer`, optional, default `6`, min `1`, max `12`).
- `model` (`string`, optional, default repo-configured Malachi model).
- `research_mode` (`string`, enum: `off`, `bundle_once`, `refresh_each_turn`; default `bundle_once`).
- `research_budget_seconds` (`number`, optional, default `20`, min `0`, max `120`).
- `output_dir` (`string`, optional): absolute or server-approved relative artifact directory.
- `run_label` (`string`, optional): caller-provided name for artifact naming.
- `return_transcript` (`boolean`, default `true`).
- `return_intermediate_drafts` (`boolean`, default `true`).
- `strict_sources` (`boolean`, default `true`): when true, coach must mark unsupported claims instead of inventing support.
- `stop_on_rating` (`string`, enum: `EXCELLENT`, `GOOD`, `FAIR`, `POOR`, optional): early-stop target, default `EXCELLENT`.
- `time_budget_seconds` (`number`, optional): whole-run timeout.

**Validation rules**
- At least one of `topic` or `baseline_spec` is required.
- `output_dir` must resolve under an allowed artifact root unless explicit unsafe mode is enabled in server config.
- If `research_mode != off`, a research backend must be configured.
- `max_writer_turns` and `max_coach_turns` must be equal in v1; mismatches are rejected to keep run semantics simple.

**Output schema**
- `status` (`string`): one of `success`, `bounded_stop`, `timeout`, `config_error`, `execution_error`.
- `final_spec` (`string`)
- `summary` (`string`): compact human-readable outcome.
- `completed_writer_turns` (`integer`)
- `completed_coach_turns` (`integer`)
- `artifacts` (`object`) with paths/URIs for:
  - `final_spec`
  - `transcript_interleaved`
  - `transcript_writer`
  - `transcript_coach`
  - `sources`
  - `metrics`
  - `run_metadata`
  - `logs`
- `metrics` (`object`) with at least:
  - `duration_seconds`
  - `research_duration_seconds`
  - `source_count`
  - `word_count_final_spec`
  - `iterations_completed`
- `sources` (`array`) of objects:
  - `title`
  - `url`
  - `used_in_turns`
  - `notes`
- `warnings` (`array[string]`)

### 2. `spec_loop_validate`
Validates inputs and returns the normalized run plan without invoking models.

**Purpose**
- Fast preflight for clients, CI, or wrappers.

**Input schema**
- Same accepted run inputs as `spec_loop_run`, except model execution fields are optional.

**Output schema**
- `valid` (`boolean`)
- `normalized_config` (`object`)
- `artifact_plan` (`object`)
- `warnings` (`array[string]`)
- `errors` (`array[string]`)

### 3. `spec_loop_resume`
Resumes an interrupted run from saved artifacts/checkpoints.

**Purpose**
- Continue after timeout or transport interruption.

**Input schema**
- `run_dir` (`string`, required)
- `additional_writer_turns` (`integer`, optional, default `0`)
- `additional_coach_turns` (`integer`, optional, default `0`)
- `time_budget_seconds` (`number`, optional)

**Output schema**
- Same as `spec_loop_run`, plus `resumed_from_run_dir`.

### 4. `spec_loop_artifact`
Returns a requested artifact or metadata for a prior run.

**Purpose**
- Lets clients fetch outputs without rerunning the loop.

**Input schema**
- `run_dir` (`string`, required)
- `artifact` (`string`, enum: `final_spec`, `interleaved`, `writer`, `coach`, `sources`, `metrics`, `metadata`, `logs`)

**Output schema**
- `artifact_type` (`string`)
- `path` (`string`)
- `content` (`string`, optional if too large)
- `truncated` (`boolean`)

---

## Optional future MCP surfaces
Not required in v1, but the design must leave room for:
- a prompt template surface for generating caller-side task framing,
- resources exposing recent run metadata,
- progress notifications during long runs,
- Streamable HTTP transport,
- multi-coach or rubric-based evaluation.

---

## Core workflow semantics

### Run phases
1. **Input normalization**
   - Build a normalized run request from raw tool args.
   - Compute artifact directory and run id.

2. **Baseline creation**
   - If `baseline_spec` is present, use it.
   - Otherwise create an initial writer draft from `topic` and `context`.

3. **Research collection**
   - If `research_mode = off`, skip.
   - If `bundle_once`, collect a research bundle before the first coach turn and reuse it.
   - If `refresh_each_turn`, collect or refresh research before each coach turn.

4. **Writer/coach loop**
   - Writer produces or revises the living spec.
   - Coach nitpicks, argues, and cites web sources actually used.
   - Loop continues until max turns, explicit acceptance, or timeout.

5. **Finalization**
   - Persist final spec, transcripts, source appendix, metrics, and machine-readable metadata.
   - Return terminal state through MCP tool output.

### Stop conditions
The loop stops when any of these becomes true:
- completed configured turn limit,
- coach rating meets configured stop target with no blocking issues,
- no material unresolved issues remain,
- run hits time budget,
- unrecoverable config or execution failure occurs.

### Writer rules
- Writer maintains one living spec.
- Writer must convert critique into concrete edits.
- Writer must not silently drop accepted requirements.
- Writer must preserve explicit assumptions and unresolved questions.
- Writer must keep a source appendix limited to claims actually grounded by research or provided context.

### Coach rules
- Coach must nitpick aggressively.
- Coach must prioritize ambiguity, missing requirements, false certainty, edge cases, feasibility gaps, and weak acceptance criteria.
- Coach must use current web research when research mode is enabled.
- Coach must distinguish sourced objections from unsourced opinion.
- Coach must recommend concrete edits, not vague dissatisfaction.

---

## MCP behavior requirements
1. The server must declare the MCP `tools` capability.
2. Tool names and schemas must remain stable within a minor version line.
3. Tool outputs must be machine-readable first, with human-readable text nested inside structured fields instead of replacing them.
4. Validation failures must be returned as tool errors or explicit invalid results, not hidden in prose.
5. Long-running runs should emit progress notifications when supported by the chosen transport/SDK.
6. The server should work over **stdio** in v1.
7. The server should be designed so **Streamable HTTP** can be added later without changing tool semantics.

**Inference note:** stdio-first is a product choice for local reliability, not an MCP requirement. Streamable HTTP readiness is included because official MCP docs and SDK guidance treat it as the modern HTTP transport.

---

## Implementation architecture

### Module layout
Recommended package layout inside `but-dad`:

- `src/but_dad/mcp_server.py`
  - MCP server bootstrap and tool registration
- `src/but_dad/mcp_models.py`
  - request/response schemas and normalization helpers
- `src/but_dad/spec_loop_service.py`
  - orchestration entrypoint used by both CLI and MCP tools
- `src/but_dad/research_service.py`
  - web search, page extraction, source normalization, citations
- `src/but_dad/malachi_client.py`
  - OpenAI-compatible Malachi wrapper with bounded retries and timeouts
- `src/but_dad/artifacts.py`
  - run directory creation, file writing, checkpointing, resume metadata
- `src/but_dad/transcript.py`
  - writer/coach/interleaved transcript shaping
- `src/but_dad/config.py`
  - env/config loading
- `src/but_dad/cli.py`
  - local debugging CLI layered on the same service

### Reuse requirement
The current `fast_agent_experiment.py` logic must be treated as a prototype source, not the permanent public API. The production MCP server should lift reusable pieces out into service modules so:
- CLI and MCP share the same orchestration path,
- tests do not depend on shelling out where unnecessary,
- and future backends can be swapped with minimal surface change.

---

## Model/backend requirements
1. The primary model path in v1 is Malachi through its OpenAI-compatible endpoint.
2. Server config must support:
   - `base_url`
   - `api_key`
   - `default_model`
   - writer and coach token caps
   - per-call timeout
3. Writer and coach may use the same model in v1.
4. The architecture must permit different models per role later.
5. Streaming is optional at the model layer; non-streaming execution is acceptable if it is more reliable.
6. Timeouts, retries, and transport failures must be normalized into wrapper/server states rather than leaking raw client exceptions as the only signal.

---

## Research requirements
1. Research collection must be pluggable and isolated from orchestration.
2. V1 may use the same repo-local search/extract approach that succeeded in testing.
3. Source objects must store at least title, URL, snippet or extract, and turns used.
4. The coach must be able to say the research bundle is weak or incomplete.
5. The server must never fabricate URLs.
6. The final output must preserve a source appendix separate from the coach prose.

---

## Artifact contract
Each run must create an isolated run directory under a configured artifact root.

### Required files
- `final-spec.md`
- `transcript-interleaved.md`
- `transcript-writer.md`
- `transcript-coach.md`
- `sources.json`
- `metrics.json`
- `run.json`
- `logs.txt`

### Recommended optional files
- `baseline-spec.md`
- `normalized-input.json`
- `research-bundle.md`
- `checkpoints/turn-<n>.json`

### Run metadata
`run.json` must include:
- run id
- created timestamp
- terminal status
- config snapshot
- model info
- duration
- completed turns
- error class/message if any
- artifact manifest

---

## Error model
### Terminal states
- `success`
- `bounded_stop`
- `timeout`
- `config_error`
- `execution_error`

### Tool-level behavior
- Invalid arguments: reject immediately.
- Research backend unavailable when required: `config_error`.
- Malachi/network timeout: `execution_error` unless whole-run budget was exceeded first, then `timeout`.
- Partial artifact write: record warning and best-effort manifest.
- Resume on missing checkpoint: explicit invalid result.

---

## Security and safety
1. Output directories must be path-validated.
2. Raw environment variables and secrets must never be written to artifacts.
3. Tool descriptions must avoid promising silent network access beyond the documented research/model backends.
4. Clients should be expected to show tool inputs before execution when appropriate; the server must assume tool invocations are high-trust but auditable.
5. The server must log enough for debugging without dumping sensitive prompt context unnecessarily.
6. Unsafe filesystem writes outside the configured artifact root must be disabled by default.

---

## Performance targets
These targets are based on the local runs already observed in the repo and are meant as initial acceptance targets, not vendor guarantees.

### Baseline targets
- `2x2` run should usually complete within **180 seconds** locally.
- `6x6` run should usually complete within **480 seconds** locally.
- Peak memory for normal runs should usually remain below **300 MB**.
- Artifact writing should remain negligible relative to model latency.

### Observability requirements
Metrics must capture:
- total duration,
- per-turn writer duration,
- per-turn coach duration,
- research duration,
- source count,
- final spec word count,
- and terminal status.

---

## Test plan

### Unit tests
- input validation for each tool
- artifact path normalization
- transcript splitting and formatting
- source normalization and deduping
- terminal state mapping

### Integration tests
- MCP server starts over stdio
- `tools/list` exposes expected tool names
- `spec_loop_validate` returns stable normalized config
- `spec_loop_run` succeeds with mocked model/research backends
- `spec_loop_resume` resumes from a checkpoint fixture
- `spec_loop_artifact` retrieves stored outputs

### Live tests
- one `2x2` Malachi-backed run
- one `6x6` Malachi-backed run
- at least one run with research enabled proving coach citations are carried into outputs

### Debugging tools
Use MCP Inspector against the stdio server during development.

---

## CLI compatibility
A repo-local CLI should remain available for debugging, but it must become a thin wrapper over the same service used by MCP. CLI parity matters so:
- developers can reproduce MCP behavior locally,
- failures can be debugged outside client integrations,
- and performance tests can run in CI without a full MCP client stack.

---

## Rollout plan
### Phase 1
- Extract orchestration/artifact logic out of `fast_agent_experiment.py`
- Implement `spec_loop_validate` and `spec_loop_run`
- Support stdio MCP transport
- Support Malachi and current research path
- Add live `2x2` verification

### Phase 2
- Add resume support and `spec_loop_artifact`
- Add richer progress notifications
- Add live `6x6` verification and performance reporting

### Phase 3
- Add optional Streamable HTTP transport
- Add richer source filtering and structured citation metadata
- Consider prompt/resource surfaces if clients benefit

---

## Acceptance criteria
1. An MCP Inspector session over stdio can discover all v1 tools.
2. A caller can provide a rough topic and get back a final spec plus artifact paths.
3. A caller can provide an existing baseline spec and receive an improved spec.
4. Tool outputs are structured enough for automation without brittle markdown parsing.
5. A failed run still writes machine-readable run metadata and partial artifacts when possible.
6. A `2x2` and `6x6` live Malachi run complete successfully under the stated performance targets in the target environment, or the variance is recorded in the findings.
7. Coach outputs in research-enabled runs include real consulted URLs and the final result preserves a source appendix.
8. CLI and MCP paths share the same orchestration implementation.

---

## Open questions
1. Should `spec_loop_run` optionally return only artifact paths for very large outputs?
2. Should the server support caller-supplied source allow/block preferences in v1?
3. Should progress notifications include partial draft text, or only status metadata?
4. Do we want a separate `spec_loop_generate_baseline` tool, or is it unnecessary if `spec_loop_run` already accepts missing `baseline_spec`?
5. Should Streamable HTTP be shipped in the same package or a separate entrypoint?

---

## Recommended file target
This spec should drive implementation in:
- `/opt/agent-zero/usr/workdir/but-dad/src/but_dad/`
- with planning docs under `/opt/agent-zero/usr/workdir/but-dad/docs/planning/`

---

## Source appendix
1. MCP tools specification: tools are exposed via `tools/list` and invoked with `tools/call`; tool definitions include `name`, `description`, `inputSchema`, and optional `outputSchema`.
   - https://modelcontextprotocol.io/specification/2025-06-18/server/tools
2. MCP concepts docs: servers exposing tools must declare the `tools` capability; MCP tools are model-controlled but clients may choose their own interaction model.
   - https://modelcontextprotocol.io/docs/concepts/tools
3. MCP SDK docs: official SDKs exist for TypeScript and Python; current guidance identifies standard transports including stdio and Streamable HTTP.
   - https://modelcontextprotocol.io/docs/sdk
   - https://github.com/modelcontextprotocol/typescript-sdk
4. MCP Inspector docs: recommended for testing/debugging locally developed MCP servers.
   - https://modelcontextprotocol.io/docs/tools
5. OpenHands headless docs: headless runs are file/task-driven automation runs and can emit JSONL, which is relevant to the existing repo automation context even though the MCP server itself is frontend-agnostic.
   - https://docs.openhands.dev/openhands/usage/cli/headless

**Inference note:** the exact v1 tool split (`spec_loop_run`, `spec_loop_validate`, `spec_loop_resume`, `spec_loop_artifact`) is an implementation design choice derived from the tested But Dad workflow and MCP tool semantics; it is not mandated by the MCP spec.
