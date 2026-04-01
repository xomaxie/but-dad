from __future__ import annotations

import argparse
import asyncio
import os
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from textwrap import dedent
from typing import Sequence

from .loop import LoopConfig, SpecLoopState

DEFAULT_TOPIC = "Produce an implementation-ready spec for shipping a reusable MCP tool."
DEFAULT_OUTPUT_PATH = Path("docs/experiments/fast-agent-sample-output.md")
DEFAULT_FINDINGS_PATH = Path("docs/experiments/fast-agent-findings.md")
DEFAULT_CONFIG_PATH = "path/to/fastagent.config.yaml"
DEFAULT_LIVE_MODEL = "Malachi"
DEFAULT_STATUS_TARGET = "success"


@dataclass(frozen=True, slots=True)
class MalachiCheck:
    available: bool
    summary: str
    evidence: tuple[str, ...]


def build_writer_instruction(config: LoopConfig | None = None) -> str:
    loop = config or LoopConfig()
    return dedent(
        f"""
        You are the But Dad writer agent.
        Draft a single living specification that becomes more implementation-ready on every pass.
        You may revise the same spec up to {loop.max_writer_turns} total writer turns.

        Rules:
        - Keep requirements explicit, testable, and concrete.
        - Preserve useful material from earlier drafts instead of restarting.
        - Convert coach feedback into spec edits, edge cases, and acceptance criteria.
        - Keep the final spec self-contained and ready for direct implementation work.
        """
    ).strip()


def build_coach_instruction(config: LoopConfig | None = None) -> str:
    loop = config or LoopConfig()
    return dedent(
        f"""
        You are the But Dad coach agent.
        Act as the evaluator in a writer-versus-coach loop with at most {loop.max_coach_turns} coach turns.

        Your job:
        - Nitpick ambiguity, missing edge cases, missing acceptance criteria, and hand-waving.
        - Use configured web research tools before making major claims whenever the workflow is run live.
        - Cite the sources you actually used and explain why each one matters.
        - Rate the draft overall as EXCELLENT, GOOD, FAIR, or POOR.
        - Provide actionable feedback that the writer can apply in the next revision.

        Respond with sections in this order:
        1. Overall rating
        2. Blocking issues
        3. Recommended edits
        4. Sources consulted
        """
    ).strip()


def build_loop_prompt(topic: str, config: LoopConfig | None = None) -> str:
    loop = config or LoopConfig()
    return dedent(
        f"""
        Topic: {topic}

        Run a bounded writer-versus-coach specification loop.
        - Maximum writer turns: {loop.max_writer_turns}
        - Maximum coach turns: {loop.max_coach_turns}
        - The coach should use web research when live tools are configured.

        Return markdown with these top-level headings in this exact order:
        1. # Final spec
        2. # Writer transcript
        3. # Coach transcript
        4. # Source appendix
        5. # Run summary

        Additional requirements:
        - Under # Writer transcript, include sections named ## Writer turn N.
        - Under # Coach transcript, include sections named ## Coach turn N.
        - Under # Source appendix, list the actual URLs used in the run.
        - Under # Run summary, include bullet lines for:
          - terminal_status: success or bounded_stop
          - completed_writer_turns: integer
          - completed_coach_turns: integer
          - final_assessment: one short sentence

        Final deliverable requirements:
        - one implementation-ready final spec
        - explicit acceptance criteria
        - edge cases and unresolved assumptions
        - a source appendix limited to consulted sources
        - a clear terminal status summary
        """
    ).strip()


def build_live_command(topic: str = DEFAULT_TOPIC) -> str:
    escaped_topic = topic.replace('"', '\\"')
    return (
        "python -m but_dad.fast_agent_experiment "
        f'--live --config-path {DEFAULT_CONFIG_PATH} --model {DEFAULT_LIVE_MODEL} '
        f'--topic "{escaped_topic}" --output docs/experiments/fast-agent-live-output.md'
    )


def detect_malachi_support(env_var_names: Sequence[str] | None = None) -> MalachiCheck:
    names = tuple(sorted(env_var_names or os.environ))
    malachi_names = tuple(name for name in names if "MALACHI" in name.upper())

    if malachi_names:
        return MalachiCheck(
            available=True,
            summary="Malachi-related environment variables were detected.",
            evidence=malachi_names,
        )

    return MalachiCheck(
        available=False,
        summary=(
            "No MALACHI-related environment variables were present and no Malachi-specific fast-agent "
            "configuration was checked into the repo, so a live Malachi-backed run could not be verified."
        ),
        evidence=(
            "Environment inspection found no variable names containing MALACHI.",
            "The repo does not ship a fastagent.config.yaml with a Malachi model binding.",
        ),
    )


def build_dry_run_transcript(topic: str, config: LoopConfig | None = None) -> str:
    loop = config or LoopConfig()
    state = SpecLoopState(config=loop)
    lines = [
        "# Final spec",
        "",
        f"## Objective\n{topic}",
        "",
        "## Acceptance criteria",
        "- Keep the loop bounded.",
        "- Preserve a single living spec.",
        "",
        "# Writer transcript",
        "",
        "# Coach transcript",
        "",
        "# Source appendix",
        "- https://example.com/preview",
        "",
        "# Run summary",
        f"- terminal_status: {DEFAULT_STATUS_TARGET}",
        "",
    ]

    writer_transcript: list[str] = []
    coach_transcript: list[str] = []
    while state.can_continue():
        turn = state.writer_turns_used + 1
        draft = state.add_draft(
            content=(
                f"Draft {turn} tightens the scope for `{topic}` and converts the latest critique "
                f"into testable requirements, edge cases, and acceptance criteria."
            ),
            rationale=[
                "Preserve the single living spec.",
                "Turn criticism into concrete edits.",
            ],
        )
        critique = state.add_critique(
            claim=(
                f"Coach turn {turn} says the draft still needs sharper acceptance criteria and "
                "clearer handling of failure paths."
            ),
            recommendation=(
                "Add explicit success/failure examples, call out assumptions, and attach source notes "
                "for any research-backed claims."
            ),
            sources=[
                f"https://example.com/research/{turn}",
            ],
        )
        writer_transcript.extend(
            [
                f"## Writer turn {turn}",
                "",
                draft.content,
                "",
                "Rationale:",
                *(f"- {item}" for item in draft.rationale),
                "",
            ]
        )
        coach_transcript.extend(
            [
                f"## Coach turn {turn}",
                "",
                "Overall rating",
                "",
                "FAIR",
                "",
                "Blocking issues",
                "",
                critique.claim,
                "",
                "Recommended edits",
                "",
                critique.recommendation,
                "",
                "Sources consulted",
                *(f"- {source}" for source in critique.sources),
                "",
            ]
        )

    return "\n".join(
        [
            *lines[:8],
            *writer_transcript,
            lines[8],
            "",
            *coach_transcript,
            *lines[10:],
            f"- completed_writer_turns: {state.writer_turns_used}",
            f"- completed_coach_turns: {state.coach_turns_used}",
            "- final_assessment: Deterministic preview completed without live model calls.",
            "",
        ]
    ).strip() + "\n"


def build_findings_markdown(
    topic: str,
    malachi_check: MalachiCheck,
    config: LoopConfig | None = None,
) -> str:
    loop = config or LoopConfig()
    today = date.today().isoformat()
    evidence_lines = "\n".join(f"- {item}" for item in malachi_check.evidence)
    return "\n".join(
        [
            "# fast-agent experiment findings",
            "",
            f"_Generated on {today}._",
            "",
            "## What was added",
            "",
            "- `src/but_dad/fast_agent_experiment.py` wires a minimal fast-agent evaluator-optimizer experiment for the But Dad writer/coach loop.",
            "- `docs/experiments/fast-agent-sample-output.md` stores a deterministic dry-run transcript for review.",
            "- The live fast-agent path expects the writer to act as the generator and the coach to act as the evaluator.",
            "",
            "## Runnable commands",
            "",
            "Dry run:",
            "",
            "```bash",
            f'python -m but_dad.fast_agent_experiment --topic "{topic}" --output {DEFAULT_OUTPUT_PATH}',
            "```",
            "",
            "Live run once fast-agent, model credentials, and MCP server config are available:",
            "",
            "```bash",
            build_live_command(topic),
            "```",
            "",
            "## Why evaluator-optimizer is the best minimal fit",
            "",
            "- It already models a generator/evaluator loop.",
            f"- `max_refinements=5` gives at most {loop.max_writer_turns} writer drafts total.",
            "- The coach can return a quality rating plus actionable critique on each pass.",
            "- The final artifact stays inspectable because the loop remains explicit.",
            "",
            "## Malachi status",
            "",
            malachi_check.summary,
            "",
            "Evidence:",
            evidence_lines,
            "",
            (
                f"This is an inference from local environment inspection on {today}; "
                "it is not proof that Malachi is impossible everywhere."
            ),
            "",
            "## Verdict",
            "",
            (
                "fast-agent looks like a **good structural fit** for But Dad's loop, "
                "but the current environment does **not** prove operational fit yet."
            ),
            (
                "The missing piece is a live run with a real model plus research-capable MCP "
                "servers so the coach can ground critiques in current sources."
            ),
            "",
            "## Follow-up work",
            "",
            "1. Supply a `fastagent.config.yaml` that defines the search/fetch MCP servers used by the coach.",
            "2. Retry the live run with Malachi if credentials or a supported model binding become available.",
            "3. Save one real transcript from the live run and compare the resulting spec quality against the existing loop state approach.",
            "",
            "## Reference links",
            "",
            "- fast-agent docs: https://fast-agent.ai/",
            "- fast-agent workflow docs: https://fast-agent.ai/agents/workflows/",
            "- fast-agent model docs: https://fast-agent.ai/models/",
            "- fast-agent package: https://pypi.org/project/fast-agent-mcp/",
            "",
        ]
    )


def extract_terminal_status(markdown: str) -> str | None:
    match = re.search(r"terminal_status:\s*([a-z_]+)", markdown, re.IGNORECASE)
    if not match:
        return None
    return match.group(1).lower()


def _stringify_fast_agent_result(result: object) -> str:
    if isinstance(result, str):
        return result

    first_text = getattr(result, "first_text", None)
    if callable(first_text):
        text = first_text()
        if isinstance(text, str):
            return text

    text = getattr(result, "text", None)
    if isinstance(text, str):
        return text

    return str(result)


async def run_live_experiment(
    topic: str,
    output_path: Path,
    config_path: str,
    model: str,
    loop: LoopConfig,
) -> str:
    try:
        from mcp_agent.core.fastagent import FastAgent
    except ImportError as exc:
        raise RuntimeError(
            "fast-agent-mcp is not installed. Install it with `pip install -e '.[fast-agent]'` first."
        ) from exc

    fast = FastAgent(
        "But Dad fast-agent experiment",
        config_path=config_path,
        parse_cli_args=False,
        quiet=True,
    )

    @fast.agent(
        name="Writer",
        model=model,
        instruction=build_writer_instruction(loop),
        use_history=True,
    )
    @fast.agent(
        name="Coach",
        model=model,
        instruction=build_coach_instruction(loop),
        servers=["brave", "fetch"],
        use_history=True,
    )
    @fast.evaluator_optimizer(
        name="SpecLoop",
        generator="Writer",
        evaluator="Coach",
        min_rating="EXCELLENT",
        max_refinements=max(loop.max_writer_turns - 1, 0),
        instruction=(
            "Revise the same living spec to address every blocking issue, preserve valid content, "
            "and improve acceptance criteria, edge cases, and source appendix quality."
        ),
    )
    async def run() -> str:
        async with fast.run() as agent:
            result = await agent.SpecLoop.send(build_loop_prompt(topic, loop))
            rendered = _stringify_fast_agent_result(result)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(rendered)
            return rendered

    return await run()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the But Dad fast-agent experiment.")
    parser.add_argument("--topic", default=DEFAULT_TOPIC)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--findings", type=Path, default=DEFAULT_FINDINGS_PATH)
    parser.add_argument("--config-path", default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--model", default=DEFAULT_LIVE_MODEL)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args(argv)

    loop = LoopConfig()
    malachi_check = detect_malachi_support()
    output_text = build_dry_run_transcript(args.topic, loop)

    if args.live:
        output_text = asyncio.run(run_live_experiment(args.topic, args.output, args.config_path, args.model, loop))
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output_text)

    args.findings.parent.mkdir(parents=True, exist_ok=True)
    args.findings.write_text(build_findings_markdown(args.topic, malachi_check, loop))
    print(f"Wrote output to {args.output}")
    print(f"Wrote findings to {args.findings}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
