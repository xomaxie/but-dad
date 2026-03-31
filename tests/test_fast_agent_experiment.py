from but_dad.fast_agent_experiment import (
    build_coach_instruction,
    build_dry_run_transcript,
    build_findings_markdown,
    build_live_command,
    build_loop_prompt,
    detect_malachi_support,
)


def test_dry_run_transcript_uses_six_turn_budget() -> None:
    transcript = build_dry_run_transcript("Draft an issue handoff spec")

    assert transcript.count("## Writer turn") == 6
    assert transcript.count("## Coach turn") == 6
    assert "deterministic preview" in transcript


def test_loop_prompt_mentions_web_research_and_final_artifact() -> None:
    prompt = build_loop_prompt("Design a spec loop")
    coach = build_coach_instruction()

    assert "web research" in prompt.lower()
    assert "source appendix" in prompt.lower()
    assert "Overall rating" in coach
    assert "Sources consulted" in coach


def test_malachi_check_reports_missing_environment_signal() -> None:
    check = detect_malachi_support(env_var_names=("OPENAI_API_KEY", "BRAVE_API_KEY"))

    assert check.available is False
    assert "No MALACHI-related environment variables" in check.summary
    assert len(check.evidence) == 2


def test_findings_include_commands_and_verdict() -> None:
    findings = build_findings_markdown(
        "Design a writer-versus-coach loop",
        detect_malachi_support(env_var_names=()),
    )

    assert "python -m but_dad.fast_agent_experiment" in findings
    assert "--live --config-path" in findings
    assert "good structural fit" in findings.lower()
    assert "Follow-up work" in findings


def test_live_command_contains_placeholder_config_and_model() -> None:
    command = build_live_command("Ship the spec loop")

    assert "--live" in command
    assert "--config-path path/to/fastagent.config.yaml" in command
    assert "--model sonnet" in command
