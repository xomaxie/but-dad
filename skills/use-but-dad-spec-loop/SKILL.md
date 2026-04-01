---
name: "use-but-dad-spec-loop"
description: "Use the But Dad MCP tool whenever generating a meaningful spec, plan, design doc, architecture note, or implementation brief. It explains when to use preview vs live mode, how to start the MCP server, what payload to send to run_spec_loop, and which artifacts to read before returning the final spec."
---

# Use But Dad Spec Loop

Use this skill any time the task is to **generate or improve a spec** that should be more than a quick informal outline.

## Use it for

- product specs
- implementation plans
- architecture specs
- MCP/tool specs
- rollout plans
- issue-ready planning docs
- revisions of an existing spec

## Skip it for

- tiny one-paragraph notes
- casual brainstorming with no deliverable
- requests where the user explicitly wants a fast rough outline only

## Default rule

If the task says **spec**, **plan**, **design doc**, **proposal**, **implementation brief**, or asks for a polished requirements artifact, use the But Dad MCP tool.

## Tool location

Repo:
- `/opt/agent-zero/usr/workdir/but-dad`

Server entrypoint:
- `python -m but_dad.mcp_server --transport stdio`

Tool name:
- `run_spec_loop`

## Mode choice

### Use `preview` when
- you need a fast deterministic pass
- live research is not necessary
- you want a bounded local artifact for inspection
- you are drafting the first serious version of a spec

### Use `live` when
- the coach should nitpick with current web-backed evidence
- standards, APIs, MCP details, vendor docs, or recent facts matter
- you want the real Malachi-backed writer/coach run

Default to `preview` unless the task benefits from live research or the user asks for current/source-backed critique.

## Workflow

1. Write or gather the baseline spec/problem statement.
2. Choose `preview` or `live`.
3. Start the MCP server from the But Dad repo.
4. Call `run_spec_loop` with a stable `run_name`.
5. Read these outputs before answering:
   - `final-spec.md`
   - `summary.json`
   - `transcript-coach.md` when you need the strongest objections
   - `sources.json` for live runs
6. Return the final spec path and summarize the main improvements.

## Recommended payload

Always provide:
- `topic`
- `run_name`
- `mode`

Usually also provide:
- `context`
- `constraints`
- `acceptance_criteria`

Keep turn counts at the defaults unless the user requests otherwise.

## Minimal payload

```json
{
  "topic": "Create a reusable MCP tool spec for a writer-vs-coach spec loop.",
  "run_name": "reusable-mcp-tool-spec",
  "mode": "preview"
}
```

## Rich payload

```json
{
  "topic": "Turn the tested But Dad workflow into a reusable MCP tool.",
  "run_name": "reusable-mcp-tool-spec",
  "mode": "live",
  "context": [
    "The repo already has a preview MCP server and a proven live Malachi-backed path.",
    "The final deliverable should be reusable across repos and callable over stdio first."
  ],
  "constraints": [
    "Keep the API small and implementation-ready.",
    "Prefer explicit artifact contracts and terminal states.",
    "Avoid vague architectural placeholders."
  ],
  "acceptance_criteria": [
    "Defines the MCP tool surface.",
    "Defines artifact outputs.",
    "Defines failure and resume behavior.",
    "Makes client/server responsibilities explicit."
  ]
}
```

## Running the server

From `/opt/agent-zero/usr/workdir/but-dad`:

```bash
PYTHONPATH=src .venv/bin/python -m but_dad.mcp_server --transport stdio
```

If the venv is missing:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev,fast-agent]'
```

For live mode, set local config first if needed:

```bash
export BUT_DAD_FASTAGENT_CONFIG_PATH=/absolute/path/to/your-fastagent.config.yaml
export BUT_DAD_FASTAGENT_MODEL=Malachi
```

## Artifacts to inspect

The tool writes under:
- `docs/experiments/mcp-tool/<run-name>/`

Key files:
- `final-spec.md` — primary deliverable
- `transcript.md` — interleaved writer/coach transcript
- `transcript-writer.md`
- `transcript-coach.md`
- `sources.json` — consulted sources, especially important in live mode
- `summary.json` — status, paths, warnings
- `metrics.json` — timing and counts

## Response guidance

When using this skill, prefer answering with:
- final spec path
- mode used
- whether the run was preview or live
- the biggest changes the coach forced
- any warnings or incomplete areas

## References

Read these only if needed:
- `references/example-invocations.md`
- `/opt/agent-zero/usr/workdir/but-dad/README.md`
