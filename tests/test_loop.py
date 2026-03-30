from but_dad.loop import LoopConfig, SpecLoopState


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
