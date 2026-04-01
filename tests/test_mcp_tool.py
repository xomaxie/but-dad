import json
from pathlib import Path

from but_dad.mcp_server import build_server
from but_dad.mcp_tool import SpecLoopRequest, run_spec_loop


def test_run_spec_loop_writes_expected_artifacts(tmp_path: Path) -> None:
    result = run_spec_loop(
        SpecLoopRequest(
            topic="Implement a reusable MCP tool for the But Dad loop.",
            run_name="issue-10-sample",
            output_dir=str(tmp_path),
            context=["Issue #10 requests a reusable MCP server."],
            acceptance_criteria=["Artifacts are predictable.", "Tests cover the loop contract."],
        )
    )

    run_dir = tmp_path / "issue-10-sample"
    assert result.output_dir == str(run_dir)
    assert result.preferred_model_backend == "Malachi"
    assert result.writer_turns_used == 6
    assert result.coach_turns_used == 6

    final_spec = run_dir / "final-spec.md"
    transcript = run_dir / "transcript.md"
    transcript_json = run_dir / "transcript.json"
    summary = run_dir / "summary.json"
    for path in (final_spec, transcript, transcript_json, summary):
        assert path.exists()

    assert "## Current spec" in final_spec.read_text()
    assert "## Coach turn 6" in transcript.read_text()
    parsed_transcript = json.loads(transcript_json.read_text())
    assert parsed_transcript[0]["role"] == "writer"
    parsed_summary = json.loads(summary.read_text())
    assert parsed_summary["run_id"] == "issue-10-sample"


def test_run_spec_loop_server_registers_structured_tool() -> None:
    server = build_server()
    tools = server._tool_manager.list_tools()

    assert [tool.name for tool in tools] == ["run_spec_loop"]
    tool = tools[0]
    assert tool.fn_metadata.output_schema is not None
    assert "topic" in tool.parameters["properties"]
    assert "summary_path" in tool.fn_metadata.output_schema["properties"]
