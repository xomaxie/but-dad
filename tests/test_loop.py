import json

import pytest

from but_dad.cli import main
from but_dad.loop import LoopConfig, SpecLoopState, TurnLimitError


def test_loop_respects_default_turn_budget() -> None:
    state = SpecLoopState()

    for idx in range(6):
        assert state.can_continue() is True
        state.add_draft(f"draft {idx + 1}")
        state.add_critique(
            claim=f"claim {idx + 1}",
            recommendation=f"recommendation {idx + 1}",
            sources=[f"https://example.com/{idx + 1}"],
        )

    assert state.writer_turns_used == 6
    assert state.coach_turns_used == 6
    assert state.can_continue() is False


def test_custom_budget_is_supported() -> None:
    state = SpecLoopState(config=LoopConfig(max_writer_turns=2, max_coach_turns=3))

    state.add_draft("draft 1")
    state.add_critique("claim 1", "fix 1")
    assert state.can_continue() is True

    state.add_draft("draft 2")
    assert state.can_continue() is False


def test_add_draft_and_critique_enforce_turn_limits() -> None:
    state = SpecLoopState(config=LoopConfig(max_writer_turns=1, max_coach_turns=1))

    state.add_draft("draft 1")
    state.add_critique("claim 1", "fix 1")

    with pytest.raises(TurnLimitError, match="writer turn limit reached"):
        state.add_draft("draft 2")

    with pytest.raises(TurnLimitError, match="coach turn limit reached"):
        state.add_critique("claim 2", "fix 2")


def test_build_final_spec_includes_latest_draft_and_unique_sources() -> None:
    state = SpecLoopState(config=LoopConfig(max_writer_turns=3, max_coach_turns=3))
    state.add_draft("draft 1", rationale=["start from a minimal brief"])
    state.add_draft("draft 2")
    state.add_critique(
        "missing source appendix",
        "group citations into a dedicated appendix",
        sources=["https://example.com/a", "https://example.com/a", "https://example.com/b"],
    )

    artifact = state.build_final_spec(title="CLI Demo")

    assert "# CLI Demo" in artifact
    assert "- Writer turns: 2/3" in artifact
    assert "- Coach turns: 1/3" in artifact
    assert "## Current spec\ndraft 2" in artifact
    assert "#### Rationale\n- start from a minimal brief" in artifact
    assert "1. https://example.com/a" in artifact
    assert "2. https://example.com/b" in artifact


def test_cli_writes_markdown_artifact(tmp_path, capsys: pytest.CaptureFixture[str]) -> None:
    input_path = tmp_path / "loop.json"
    output_path = tmp_path / "artifacts" / "final-spec.md"
    input_path.write_text(
        json.dumps(
            {
                "title": "Release readiness spec",
                "config": {"max_writer_turns": 2, "max_coach_turns": 2},
                "turns": [
                    {
                        "role": "writer",
                        "content": "Define the webhook recovery flow.",
                        "rationale": ["Keep the initial scope small."],
                    },
                    {
                        "role": "coach",
                        "claim": "The failure mode is underspecified.",
                        "recommendation": "Document retry boundaries.",
                        "sources": ["https://example.com/retries"],
                    },
                ],
            }
        )
    )

    exit_code = main(["run", "--input", str(input_path), "--output", str(output_path)])

    assert exit_code == 0
    artifact = output_path.read_text()
    assert "# Release readiness spec" in artifact
    assert "Define the webhook recovery flow." in artifact
    assert "Document retry boundaries." in artifact
    assert "1. https://example.com/retries" in artifact

    captured = capsys.readouterr()
    assert f"Wrote {output_path}" in captured.out
    assert "writer turns: 1/2" in captured.out
    assert "coach turns: 1/2" in captured.out
