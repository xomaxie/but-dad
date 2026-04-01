# But Dad reusable MCP tool — implementation-ready spec

## Summary
Build **but-dad-mcp**, a reusable MCP server that exposes the But Dad writer-versus-coach loop as a small, stable tool surface. The server must let any MCP-compatible client: (1) validate a proposed run, (2) execute a bounded improvement loop over a topic or baseline spec, (3) resume from persisted workflow checkpoints, and (4) retrieve final artifacts including transcript, sources, metrics, and run metadata.

This productizes the repo-local experiment into an MCP capability that is:
- reusable across repos and clients,
- transportable over MCP rather than CLI-only,
- bounded, auditable, and automation-friendly,
- grounded in the same writer/coach loop already validated locally.

## Goals
1. Expose the spec-improvement workflow through stable MCP tool contracts.
2. Preserve the tested behavior: one writer, one nitpicking coach, bounded turns, research-backed critique, final artifact bundle.
3. Support both “create from topic” and “improve existing baseline” modes.
4. Make runs reproducible through normalized config, checkpoints, and run metadata.
5. Keep the server decoupled from any single frontend, repo automation path, or GitHub mechanism.
6. Support Malachi-backed execution and repo-approved research tooling.
7. Keep tool outputs structured so automation does not depend on parsing prose.

## Non-goals
- Not a generic multi-agent orchestration platform.
- Not a general-purpose research agent.
- Not a replacement for human approval on important specs.
- Not a webhook server, PR bot, or code-modification server in v1.
- Not cloud-only; **stdio** is required in v1.
- Not a requirement to support multi-coach or rubric ensembles in v1.
- Not responsible for client-specific approval policy; the server is auditable and bounded, while the client decides when humans must confirm.

## Actors
- **Caller / MCP client**: submits requests and consumes outputs.
- **MCP server**: validates, orchestrates, persists, and resumes runs.
- **Writer role**: produces the living spec text.
- **Coach role**: critiques, nitpicks, and cites evidence.
- **Research backend**: supplies web search/extract if enabled.
- **Artifact store**: filesystem run directory managed by the server.
- **Human operator**: may inspect, approve, or cancel in the client layer.

## Tool surface
The v1 server must expose exactly these tools.

### 1) `spec_loop_validate`
Preflights a request without invoking models.

**Input**
- same as `spec_loop_run` below, excluding persistence-only fields.

**Output (`structuredContent`)**
- `valid: boolean`
- `normalized_config: object`
- `artifact_plan: object`
- `warnings: string[]`
- `errors: string[]`

### 2) `spec_loop_run`
Runs the full bounded writer-versus-coach workflow.

**Input**
- `topic?: string`
- `baseline_spec?: string`
- `context?: string`
- `max_writer_turns?: integer` default `6`, min `1`, max `12`
- `max_coach_turns?: integer` default `6`, min `1`, max `12`
- `model?: string`
- `research_mode?: "off" | "bundle_once" | "refresh_each_turn"` default `bundle_once`
- `research_budget_seconds?: number` default `20`, min `0`, max `120`
- `output_dir?: string`
- `run_label?: string`
- `return_transcript?: boolean` default `true`
- `return_intermediate_drafts?: boolean` default `true`
- `strict_sources?: boolean` default `true`
- `stop_on_rating?: "EXCELLENT" | "GOOD" | "FAIR" | "POOR"` default `EXCELLENT`
- `time_budget_seconds?: number`

**Validation rules**
- At least one of `topic` or `baseline_spec` is required.
- `output_dir` must resolve under an allowed artifact root unless unsafe mode is explicitly enabled in server config.
- If `research_mode != "off"`, a research backend must be configured.
- `max_writer_turns` and `max_coach_turns` must match in v1.
- `topic` plus `baseline_spec` is allowed: the baseline is the starting point; topic is framing/context.

**Tool result contract**
- The server must return both:
  - `structuredContent` matching the tool’s `outputSchema`, and
  - a `content` text block containing the serialized JSON for backwards compatibility.
- If the workflow reaches a terminal state, `isError` should be `false` even for non-success terminal statuses like `timeout` or `bounded_stop`.
- Use `isError: true` only when no valid terminal workflow result can be produced.

**Output**
- `status: "success" | "bounded_stop" | "timeout" | "config_error" | "execution_error"`
- `run_id: string`
- `final_spec: string`
- `summary: string`
- `completed_writer_turns: integer`
- `completed_coach_turns: integer`
- `artifacts: object` with paths or URIs for:
  - `final_spec`
  - `transcript_interleaved`
  - `transcript_writer`
  - `transcript_coach`
  - `sources`
  - `metrics`
  - `run_metadata`
  - `logs`
- `metrics: object`
- `sources: array<object>`
- `warnings: string[]`
- `resumed_from_run_dir?: string`

### 3) `spec_loop_resume`
Resumes an interrupted run from persisted artifacts/checkpoints.

**Input**
- `run_dir: string`
- `additional_writer_turns?: integer` default `0`
- `additional_coach_turns?: integer` default `0`
- `time_budget_seconds?: number`

**Resume rules**
- Resume only from a run directory created by this server.
- Resume only if a compatible checkpoint exists.
- Resume from the last completed checkpoint; never replay a partially committed turn.
- Resume must fail fast if the prior run is already terminal-success and the caller did not explicitly request continuation.
- Checkpoint compatibility is versioned: a run may resume only across compatible minor versions, not across incompatible major-format changes.

### 4) `spec_loop_artifact`
Fetches a stored artifact or metadata for a prior run.

**Input**
- `run_dir: string`
- `artifact: "final_spec" | "interleaved" | "writer" | "coach" | "sources" | "metrics" | "metadata" | "logs"`
- `inline_threshold_bytes?: integer` default `32768`

**Output**
- `artifact_type: string`
- `path: string`
- `content?: string`
- `truncated: boolean`
- `size_bytes?: integer`
- `sha256?: string`

## Core flows
1. **Validate**: normalize input, resolve artifact path, and produce a run plan.
2. **Start run**: create an isolated run directory and write `run.json` immediately.
3. **Baseline**: use `baseline_spec` if present; otherwise draft from `topic` and `context`.
4. **Research**: gather sources per `research_mode`; dedupe by canonical URL.
5. **Loop**: writer revises; coach critiques; repeat until turn limit, rating target, unresolved issues exhausted, timeout, or cancellation.
6. **Finalize**: write final spec, transcripts, sources, metrics, and manifest.
7. **Resume**: continue from the last durable checkpoint and repair any incomplete manifest state.
8. **Artifact fetch**: return either inline content or a path-only summary.

## Functional requirements
- The server must declare MCP `tools` capability and expose stable tool names within a minor version line.
- Tool definitions must include `inputSchema`; `outputSchema` is required for all four tools.
- Tool results must be machine-readable first, with plain text as a serialized JSON mirror.
- `run.json` must include run id, timestamps, config snapshot, terminal status, completed turns, model info, error class/message, and artifact manifest.
- Required artifact files:
  - `final-spec.md`
  - `transcript-interleaved.md`
  - `transcript-writer.md`
  - `transcript-coach.md`
  - `sources.json`
  - `metrics.json`
  - `run.json`
  - `logs.txt`
- Recommended checkpoint files:
  - `checkpoints/turn-<n>.json`
  - `normalized-input.json`
  - `baseline-spec.md`
- Writer must preserve accepted requirements, unresolved questions, and explicit assumptions.
- Coach must nitpick aggressively and convert unsupported claims into explicit objections or assumptions.
- Every external-fact objection by the coach must cite one or more URLs.
- Every URL in `sources.json` must map to at least one turn or claim.
- If research is disabled or unavailable, the final spec must say so plainly.

## Non-functional requirements
- Primary transport in v1 is **stdio**; the architecture must allow Streamable HTTP later without changing tool semantics.
- The server must be deterministic in output shaping and tolerant of bounded retries/timeouts.
- Raw secrets and environment variables must never be written to artifacts.
- Unsafe filesystem writes outside the configured artifact root are disabled by default.
- Progress notifications may be emitted when supported, but the tool contract must not depend on them.
- The implementation should share one orchestration path between CLI and MCP.

## Failure modes and edge cases
- Invalid arguments: return protocol/tool validation error immediately.
- Research backend missing when required: `config_error`.
- Model/network timeout before terminal artifacts are written: `execution_error`.
- Whole-run budget exceeded after partial progress: `timeout`.
- Partial artifact write: record warning, persist best-effort manifest, and mark incomplete state.
- Missing or incompatible checkpoint on resume: explicit invalid result.
- Duplicate source URLs: dedupe and merge usage metadata.
- Conflicting `topic` and `baseline_spec`: baseline wins as the source text; topic remains framing context.
- Large outputs: inline only if under threshold; artifacts remain authoritative.
- Cancelled run: stop at the next safe boundary, persist terminal state, and allow resume from the last complete checkpoint.

## Acceptance criteria
1. `tools/list` discovers all four tools over stdio.
2. `spec_loop_validate` returns a stable normalized config and artifact plan for the same input.
3. `spec_loop_run` returns a structured result with serialized JSON text and artifact paths.
4. A run with only `topic` creates a baseline and final spec.
5. A run with `baseline_spec` improves the provided draft.
6. A failed run still writes `run.json` and any completed artifacts.
7. `spec_loop_resume` continues from a checkpoint fixture without replaying completed turns.
8. Research-enabled runs include real consulted URLs in `sources.json`, and the final spec includes a source appendix.
9. Mocked-backend tests and live-backend tests are separate.
10. On the pinned benchmark host class, a default `2x2` smoke run completes within 180 seconds and a default `6x6` run completes within 480 seconds, measured from tool-call start to terminal artifact write completion; any variance must be recorded in the findings.

## Assumptions
- Malachi remains available through an OpenAI-compatible endpoint in the target environment.
- The repo-local research path can be wrapped behind a stable interface.
- Clients may enforce their own human-approval policy; the server does not.
- Artifact storage is local filesystem-first in v1.
- Source quality is “best effort but explicit”: unsupported claims must be labeled, not invented.

## Unresolved questions
1. Should `spec_loop_run` return only paths for very large outputs by default, or inline excerpts?
2. Should the server support caller-supplied allow/block source lists in v1?
3. Should progress notifications include partial draft text or metadata only?
4. Should Streamable HTTP ship in the same package or a separate entrypoint?
5. Should a separate baseline-generation tool exist, or is `spec_loop_run` sufficient?

## Source appendix
1. MCP tools specification: tool discovery, invocation, `content`, `structuredContent`, and `outputSchema`.
   - https://modelcontextprotocol.io/specification/2025-06-18/server/tools
2. MCP tools concept docs: servers that support tools must declare the `tools` capability; tools are model-controlled but user confirmation policy lives in the client.
   - https://modelcontextprotocol.io/docs/concepts/tools
3. MCP architecture overview: stdio and Streamable HTTP are the two primary transport options; MCP uses JSON-RPC 2.0 and a stateful lifecycle.
   - https://modelcontextprotocol.io/docs/learn/architecture
4. MCP lifecycle docs: initialization is the first phase and capability negotiation occurs during connection setup.
   - https://modelcontextprotocol.io/specification/draft/basic/lifecycle
5. MCP cancellation docs: in-progress requests may be cancelled; task-augmented flows have dedicated cancellation behavior.
   - https://modelcontextprotocol.io/specification/draft/basic/utilities/cancellation

## Changelog
- Tightened the MCP result contract to require both `structuredContent` and serialized JSON text.
- Defined checkpoint/resume semantics, version compatibility, and partial-write handling.
- Added explicit provenance rules for sources and coach objections.
- Clarified that client policy owns human confirmation, not the server.
- Replaced vague performance language with measurable benchmark criteria.
