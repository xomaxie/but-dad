import asyncio
import json
import os
import sys
from pathlib import Path

import anyio
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp_agent.llm.model_factory import ModelFactory

from but_dad.fast_agent_experiment import _patch_mcp_agent_model_registry
from but_dad.mcp_tool import (
    SpecLoopRequest,
    _disable_console_logger_in_fastagent_config,
    _normalize_live_model_for_config,
    _prepare_runtime_live_config,
    _resolve_live_time_budget_seconds,
    run_spec_loop,
)


def test_run_spec_loop_preview_writes_expected_artifacts(tmp_path: Path) -> None:
    result = run_spec_loop(
        SpecLoopRequest(
            topic="Implement a reusable MCP tool for the But Dad loop.",
            run_name="public-preview-sample",
            output_dir=str(tmp_path),
            mode="preview",
            context=["Public sample run for a reusable MCP server."],
            acceptance_criteria=["Artifacts are predictable.", "Tests cover the loop contract."],
        )
    )

    run_dir = tmp_path / "public-preview-sample"
    assert result.output_dir == str(run_dir)
    assert result.preferred_model_backend == "Malachi"
    assert result.status == "bounded_stop"
    assert result.writer_turns_used == 6
    assert result.coach_turns_used == 6
    assert result.warnings == [
        "Preview mode stays deterministic and does not execute Malachi or live research.",
        "Use mode=live with a configured fast-agent setup to run the real writer/coach loop.",
    ]

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
    assert parsed_summary["run_id"] == "public-preview-sample"
    parsed_run = json.loads(run_metadata.read_text())
    assert parsed_run["status"] == "bounded_stop"
    assert parsed_run["artifacts"]["transcript_writer"] == str(writer_transcript)
    assert json.loads(sources.read_text()) == []


async def _call_preview_tool_over_stdio(tmp_path: Path) -> object:
    server = StdioServerParameters(
        command=sys.executable,
        args=["-m", "but_dad.mcp_server", "--transport", "stdio"],
        env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")},
        cwd=str(Path(__file__).resolve().parents[1]),
    )
    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            assert [tool.name for tool in tools.tools] == ["run_spec_loop"]
            result = await session.call_tool(
                "run_spec_loop",
                {
                    "topic": "Round-trip MCP preview test",
                    "title": "Preview Spec",
                    "mode": "preview",
                    "output_dir": str(tmp_path),
                    "max_writer_turns": 1,
                    "max_coach_turns": 1,
                },
            )
            return result


def test_mcp_server_stdio_round_trip_preview(tmp_path: Path) -> None:
    result = anyio.run(_call_preview_tool_over_stdio, tmp_path)

    assert result.isError is False
    payload = result.structuredContent
    assert payload["status"] == "bounded_stop"
    assert payload["writer_turns_used"] == 1
    assert payload["coach_turns_used"] == 1
    assert Path(payload["final_spec_path"]).exists()
    assert Path(payload["summary_path"]).exists()


def test_run_spec_loop_live_runner_writes_terminal_metadata(tmp_path: Path) -> None:
    def stub_live_runner(request: SpecLoopRequest, raw_output_path: Path) -> str:
        assert request.mode == "live"
        assert raw_output_path == tmp_path / "live-sample" / "raw-live-output.md"
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
            run_name="live-sample",
            output_dir=str(tmp_path),
            mode="live",
            config_path=str(tmp_path / "fastagent.config.yaml"),
        ),
        live_runner=stub_live_runner,
    )

    run_dir = tmp_path / "live-sample"
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
            run_name="issue-12-error",
            output_dir=str(tmp_path),
            mode="live",
            config_path=str(config_path),
        )
    )

    run_dir = tmp_path / "issue-12-error"
    assert result.status == "execution_error"
    assert result.error_message == "boom"
    assert "Partial live output was captured" in result.warnings[1]
    assert "Partial spec before crash." in (run_dir / "final-spec.md").read_text()


def test_run_spec_loop_live_partial_structured_output_recovers_without_execution_error(tmp_path: Path) -> None:
    def stub_live_runner(request: SpecLoopRequest, raw_output_path: Path) -> str:
        assert request.mode == "live"
        return """# Final spec

## Objective
Recovered final spec.

# Writer transcript

## Writer turn 1

Draft one

# Run summary

- terminal_status: success
- completed_writer_turns: 1
- completed_coach_turns: 0
- final_assessment: Partial transcript, but the model finished the useful work.
"""

    result = run_spec_loop(
        SpecLoopRequest(
            topic="Recover partial live output without collapsing the run.",
            run_name="issue-14-partial-success",
            output_dir=str(tmp_path),
            mode="live",
            config_path=str(tmp_path / "fastagent.config.yaml"),
        ),
        live_runner=stub_live_runner,
    )

    run_dir = tmp_path / "issue-14-partial-success"
    assert result.status == "success"
    assert result.error_message is None
    assert result.writer_turns_used == 1
    assert result.coach_turns_used == 0
    assert result.warnings == [
        "Recovered artifacts from partial live output even though the full transcript structure was incomplete.",
    ]
    assert json.loads((run_dir / "run.json").read_text())["status"] == "success"
    assert json.loads((run_dir / "summary.json").read_text())["status"] == "success"
    assert "Recovered final spec." in (run_dir / "final-spec.md").read_text()
    assert "Draft one" in (run_dir / "transcript.md").read_text()
    assert (run_dir / "raw-live-output.md").exists()


def test_prepare_runtime_live_config_disables_console_logger(tmp_path: Path) -> None:
    source = tmp_path / "fastagent.yaml"
    source.write_text(
        "\n".join(
            [
                "default_model: openai.gpt-5.4",
                "logger:",
                "  type: console",
                "  level: error",
                "",
            ]
        )
    )

    runtime_path = Path(_prepare_runtime_live_config(str(source), tmp_path / "run"))

    assert runtime_path != source
    assert runtime_path.name == "fastagent.runtime.yaml"
    runtime_text = runtime_path.read_text()
    assert "type: none" in runtime_text
    assert "type: console" not in runtime_text
    assert "level: error" in runtime_text


def test_disable_console_logger_in_fastagent_config_appends_logger_block_when_missing() -> None:
    updated = _disable_console_logger_in_fastagent_config("default_model: openai.gpt-5.4\n")

    assert updated.endswith("logger:\n  type: none\n")


def test_normalize_live_model_for_local_malachi_config_strips_provider_prefix(tmp_path: Path) -> None:
    config_path = tmp_path / "fastagent.yaml"
    config_path.write_text(
        "\n".join(
            [
                "openai:",
                "  base_url: http://127.0.0.1:18642/v1",
                "",
            ]
        )
    )

    assert _normalize_live_model_for_config("openai.gpt-5.4", str(config_path)) == "gpt-5.4"
    assert _normalize_live_model_for_config("gpt-5.4", str(config_path)) == "gpt-5.4"


def test_patch_mcp_agent_model_registry_accepts_gpt5_family() -> None:
    _patch_mcp_agent_model_registry()

    parsed = ModelFactory.parse_model_string("gpt-5.4")
    assert parsed.provider.value == "openai"
    assert parsed.model_name == "gpt-5.4"


def test_resolve_live_time_budget_seconds_uses_recommended_floor_for_full_model() -> None:
    request = SpecLoopRequest(
        topic="Verify a live run.",
        mode="live",
        max_writer_turns=1,
        max_coach_turns=1,
        time_budget_seconds=180,
    )

    assert _resolve_live_time_budget_seconds(request, "gpt-5.4") == 420.0


def test_resolve_live_time_budget_seconds_keeps_mini_model_smoke_budget() -> None:
    request = SpecLoopRequest(
        topic="Verify a live run.",
        mode="live",
        max_writer_turns=1,
        max_coach_turns=1,
        time_budget_seconds=180,
    )

    assert _resolve_live_time_budget_seconds(request, "gpt-5.4-mini") == 180.0


def test_resolve_live_time_budget_seconds_preserves_explicit_tiny_timeout() -> None:
    request = SpecLoopRequest(
        topic="Force a live timeout quickly.",
        mode="live",
        max_writer_turns=1,
        max_coach_turns=1,
        time_budget_seconds=0.01,
    )

    assert _resolve_live_time_budget_seconds(request, "gpt-5.4") == 0.01


def test_resolve_live_time_budget_seconds_scales_for_extra_refinement_pairs() -> None:
    request = SpecLoopRequest(
        topic="Run a deeper live loop.",
        mode="live",
        max_writer_turns=3,
        max_coach_turns=3,
        time_budget_seconds=240,
    )

    assert _resolve_live_time_budget_seconds(request, "gpt-5.4") == 660.0


def test_default_live_runner_passes_structured_request_prompt_to_live_experiment(
    tmp_path: Path, monkeypatch
) -> None:
    captured: dict[str, object] = {}

    async def fake_run_live_experiment(
        topic: str,
        output_path: Path,
        config_path: str,
        model: str,
        loop,
    ) -> str:
        captured["topic"] = topic
        captured["output_path"] = output_path
        captured["config_path"] = config_path
        captured["model"] = model
        return """# Final spec

## Objective
Structured request received.

# Writer transcript

## Writer turn 1

Draft one

# Coach transcript

## Coach turn 1

Overall rating

GOOD

Blocking issues

None.

Recommended edits

Ship it.

Sources consulted
- https://example.com/research/1

# Source appendix

- https://example.com/research/1

# Run summary

- terminal_status: success
- completed_writer_turns: 1
- completed_coach_turns: 1
- final_assessment: Structured request completed cleanly.
"""

    monkeypatch.setattr("but_dad.mcp_tool.run_live_experiment", fake_run_live_experiment)
    config_path = tmp_path / "fastagent.config.yaml"
    config_path.write_text("agents: []\n")

    result = run_spec_loop(
        SpecLoopRequest(
            topic="Tighten the PR #29 allowance-fix spec.",
            title="PR #29 insurance upload allowance fixes",
            run_name="structured-live-request",
            output_dir=str(tmp_path),
            mode="live",
            config_path=str(config_path),
            model="openai.gpt-5.4",
            context=["Use prior review notes from local files."],
            constraints=["Keep changes minimal.", "Name exact files."],
            acceptance_criteria=["Call out refund behavior.", "List the exact tests."],
            max_writer_turns=2,
            max_coach_turns=2,
        )
    )

    assert result.status == "success"
    topic = str(captured["topic"])
    assert "Title: PR #29 insurance upload allowance fixes" in topic
    assert "Primary objective:\nTighten the PR #29 allowance-fix spec." in topic
    assert "Context:\n- Use prior review notes from local files." in topic
    assert "Constraints:\n- Keep changes minimal.\n- Name exact files." in topic
    assert "Acceptance criteria:\n- Call out refund behavior.\n- List the exact tests." in topic
