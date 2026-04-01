import asyncio
import json
from pathlib import Path

from but_dad.mcp_server import build_server
from but_dad.mcp_tool import SpecLoopRequest, run_spec_loop


def test_run_spec_loop_preview_writes_expected_artifacts(tmp_path: Path) -> None:
    result = run_spec_loop(
        SpecLoopRequest(
            topic="Implement a reusable MCP tool for the But Dad loop.",
            run_name="issue-10-sample",
            output_dir=str(tmp_path),
            mode="preview",
            context=["Issue #10 requests a reusable MCP server."],
            acceptance_criteria=["Artifacts are predictable.", "Tests cover the loop contract."],
        )
    )

    run_dir = tmp_path / "issue-10-sample"
    assert result.output_dir == str(run_dir)
    assert result.preferred_model_backend == "Malachi"
    assert result.status == "bounded_stop"
    assert result.writer_turns_used == 6
    assert result.coach_turns_used == 6

    final_spec = run_dir / "final-spec.md"
    transcript = run_dir / "transcript.md"
    transcript_json = run_dir / "transcript.json"
    writer_transcript = run_dir / "transcript-writer.md"
    coach_transcript = run_dir / "transcript-coach.md"
    summary = run_dir / "summary.json"
    run_metadata = run_dir / "run.json"
    sources = run_dir / "sources.json"
    metrics = run_dir / "metrics.json"
    for path in (
        final_spec,
        transcript,
        transcript_json,
        writer_transcript,
        coach_transcript,
        summary,
        run_metadata,
        sources,
        metrics,
    ):
        assert path.exists()

    assert "## Current spec" in final_spec.read_text()
    assert "## Coach turn 6" in transcript.read_text()
    parsed_transcript = json.loads(transcript_json.read_text())
    assert parsed_transcript[0]["role"] == "writer"
    parsed_summary = json.loads(summary.read_text())
    assert parsed_summary["run_id"] == "issue-10-sample"
    parsed_run = json.loads(run_metadata.read_text())
    assert parsed_run["status"] == "bounded_stop"
    assert parsed_run["artifacts"]["transcript_writer"] == str(writer_transcript)
    assert json.loads(sources.read_text()) == []


def test_run_spec_loop_live_runner_writes_terminal_metadata(tmp_path: Path) -> None:
    def stub_live_runner(request: SpecLoopRequest, raw_output_path: Path) -> str:
        assert request.mode == "live"
        assert raw_output_path == tmp_path / "issue-12-live" / "raw-live-output.md"
        return """# Final spec

## Objective
Ship it.

# Writer transcript

## Writer turn 1

Draft one

## Writer turn 2

Draft two

# Coach transcript

## Coach turn 1

Overall rating

GOOD

Blocking issues

Needs sharper acceptance criteria.

Recommended edits

Add explicit verification steps.

Sources consulted
- https://example.com/research/1

## Coach turn 2

Overall rating

EXCELLENT

Blocking issues

None.

Recommended edits

Ship it.

Sources consulted
- https://example.com/research/2

# Source appendix

- https://example.com/research/1
- https://example.com/research/2

# Run summary

- terminal_status: success
- completed_writer_turns: 2
- completed_coach_turns: 2
- final_assessment: Live run completed cleanly.
"""

    result = run_spec_loop(
        SpecLoopRequest(
            topic="Upgrade preview MCP tool to the live path.",
            run_name="issue-12-live",
            output_dir=str(tmp_path),
            mode="live",
            config_path=str(tmp_path / "fastagent.config.yaml"),
        ),
        live_runner=stub_live_runner,
    )

    run_dir = tmp_path / "issue-12-live"
    assert result.status == "success"
    assert result.writer_turns_used == 2
    assert result.coach_turns_used == 2
    assert json.loads((run_dir / "metrics.json").read_text())["source_count"] == 2
    assert json.loads((run_dir / "run.json").read_text())["artifacts"]["metrics"] == str(run_dir / "metrics.json")
    assert "Status: success" in (run_dir / "transcript.md").read_text()
    assert "https://example.com/research/2" in (run_dir / "sources.json").read_text()
    assert (run_dir / "raw-live-output.md").exists()


def test_run_spec_loop_live_config_error_is_persisted(tmp_path: Path) -> None:
    result = run_spec_loop(
        SpecLoopRequest(
            topic="Try the live path without config.",
            run_name="issue-12-config-error",
            output_dir=str(tmp_path),
            mode="live",
            config_path=str(tmp_path / "missing-fastagent.yaml"),
        )
    )

    run_dir = tmp_path / "issue-12-config-error"
    assert result.status == "config_error"
    assert (run_dir / "run.json").exists()
    assert "does not exist" in (run_dir / "final-spec.md").read_text()


def test_run_spec_loop_live_timeout_persists_partial_artifacts(tmp_path: Path, monkeypatch) -> None:
    async def fake_run_live_experiment(
        topic: str,
        output_path: Path,
        config_path: str,
        model: str,
        loop,
    ) -> str:
        output_path.write_text(
            """# Final spec

## Objective
Partial spec before timeout.

# Writer transcript

## Writer turn 1

Partial draft

Rationale:
- start

# Coach transcript

## Coach turn 1

Overall rating

FAIR

Blocking issues

Need more detail.

Recommended edits

Keep going.

Sources consulted
- https://example.com/research/timeout
"""
        )
        await asyncio.sleep(0.05)
        return output_path.read_text()

    monkeypatch.setattr("but_dad.mcp_tool.run_live_experiment", fake_run_live_experiment)
    config_path = tmp_path / "fastagent.config.yaml"
    config_path.write_text("agents: []\n")

    result = run_spec_loop(
        SpecLoopRequest(
            topic="Timeout while running live mode.",
            run_name="issue-12-timeout",
            output_dir=str(tmp_path),
            mode="live",
            config_path=str(config_path),
            time_budget_seconds=0.01,
        )
    )

    run_dir = tmp_path / "issue-12-timeout"
    assert result.status == "timeout"
    assert result.writer_turns_used == 1
    assert result.coach_turns_used == 1
    assert "timed out" in result.warnings[0].lower()
    assert "Partial live output was captured" in result.warnings[1]
    assert "Partial spec before timeout." in (run_dir / "final-spec.md").read_text()
    assert json.loads((run_dir / "run.json").read_text())["status"] == "timeout"
    assert json.loads((run_dir / "sources.json").read_text())[0]["url"] == "https://example.com/research/timeout"


def test_run_spec_loop_live_execution_error_persists_partial_artifacts(tmp_path: Path, monkeypatch) -> None:
    async def fake_run_live_experiment(
        topic: str,
        output_path: Path,
        config_path: str,
        model: str,
        loop,
    ) -> str:
        output_path.write_text(
            """# Final spec

## Objective
Partial spec before crash.

# Writer transcript

## Writer turn 1

Draft before crash
"""
        )
        raise RuntimeError("boom")

    monkeypatch.setattr("but_dad.mcp_tool.run_live_experiment", fake_run_live_experiment)
    config_path = tmp_path / "fastagent.config.yaml"
    config_path.write_text("agents: []\n")

    result = run_spec_loop(
        SpecLoopRequest(
            topic="Crash while running live mode.",
            run_name="issue-12-execution-error",
            output_dir=str(tmp_path),
            mode="live",
            config_path=str(config_path),
        )
    )

    run_dir = tmp_path / "issue-12-execution-error"
    assert result.status == "execution_error"
    assert result.writer_turns_used == 1
    assert result.coach_turns_used == 0
    assert "failed" in result.warnings[0].lower()
    assert "Partial live output was captured" in result.warnings[1]
    assert "Partial spec before crash." in (run_dir / "final-spec.md").read_text()
    assert json.loads((run_dir / "run.json").read_text())["status"] == "execution_error"


def test_run_spec_loop_server_registers_structured_tool() -> None:
    server = build_server()
    tools = server._tool_manager.list_tools()

    assert [tool.name for tool in tools] == ["run_spec_loop"]
    tool = tools[0]
    assert tool.fn_metadata.output_schema is not None
    assert "topic" in tool.parameters["properties"]
    assert "mode" in tool.parameters["properties"]
    assert "status" in tool.fn_metadata.output_schema["properties"]
