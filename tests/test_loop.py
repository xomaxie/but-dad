import pytest

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


def test_turn_limit_is_enforced() -> None:
    state = SpecLoopState(config=LoopConfig(max_writer_turns=1, max_coach_turns=1))
    state.add_draft("draft 1")
    state.add_critique("claim 1", "fix 1")

    with pytest.raises(TurnLimitError):
        state.add_draft("draft 2")

    with pytest.raises(TurnLimitError):
        state.add_critique("claim 2", "fix 2")


def test_final_spec_deduplicates_sources() -> None:
    state = SpecLoopState(config=LoopConfig(max_writer_turns=2, max_coach_turns=2))
    state.add_draft("draft 1", rationale=["tighten scope"])
    state.add_critique("claim 1", "fix 1", sources=["https://example.com/shared", "https://example.com/one"])
    state.add_draft("draft 2")
    state.add_critique("claim 2", "fix 2", sources=["https://example.com/shared", "https://example.com/two"])

    rendered = state.build_final_spec(title="Reusable MCP Tool")

    assert "# Reusable MCP Tool" in rendered
    assert "## Source appendix" in rendered
    appendix = rendered.split("## Source appendix", maxsplit=1)[1]
    assert appendix.count("https://example.com/shared") == 1
    assert "1. https://example.com/shared" in appendix
    assert "3. https://example.com/two" in appendix
