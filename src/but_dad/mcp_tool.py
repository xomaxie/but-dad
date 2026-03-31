from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from .loop import LoopConfig, SpecLoopState

DEFAULT_TITLE = "But Dad Spec"
DEFAULT_PREFERRED_MODEL_BACKEND = "Malachi"
DEFAULT_OUTPUT_DIR = Path("docs/experiments/mcp-tool")


class SpecLoopRequest(BaseModel):
    topic: str = Field(min_length=1)
    title: str = DEFAULT_TITLE
    run_name: str | None = None
    output_dir: str = str(DEFAULT_OUTPUT_DIR)
    context: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    max_writer_turns: int = Field(default=6, ge=1, le=6)
    max_coach_turns: int = Field(default=6, ge=1, le=6)
    preferred_model_backend: str = DEFAULT_PREFERRED_MODEL_BACKEND
    mode: Literal["preview"] = "preview"


class SpecLoopRunResult(BaseModel):
    run_id: str
    topic: str
    title: str
    mode: Literal["preview"]
    preferred_model_backend: str
    output_dir: str
    final_spec_path: str
    transcript_markdown_path: str
    transcript_json_path: str
    summary_path: str
    writer_turns_used: int
    coach_turns_used: int
    warnings: list[str] = Field(default_factory=list)


def run_spec_loop(request: SpecLoopRequest) -> SpecLoopRunResult:
    state = SpecLoopState(
        config=LoopConfig(
            max_writer_turns=request.max_writer_turns,
            max_coach_turns=request.max_coach_turns,
        )
    )
    run_id = _slugify(request.run_name or request.topic)
    run_dir = Path(request.output_dir) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    transcript_records: list[dict[str, object]] = []
    warnings = [
        "This repository revision ships a deterministic preview loop because the issue referenced spec files were not present in the repo checkout.",
        "No live web research or model calls are executed in preview mode; the preferred backend is recorded for downstream wiring.",
    ]

    while state.can_continue():
        turn = state.writer_turns_used + 1
        prior_recommendation = state.critiques[-1].recommendation if state.critiques else "Define the first living draft."

        draft = state.add_draft(
            content=_build_draft_markdown(request, turn, prior_recommendation),
            rationale=_build_draft_rationale(turn, prior_recommendation),
        )
        critique = state.add_critique(
            claim=_build_critique_claim(turn),
            recommendation=_build_critique_recommendation(turn),
            sources=[],
        )
        transcript_records.extend(
            [
                {
                    "role": "writer",
                    "turn": turn,
                    "content": draft.content,
                    "rationale": draft.rationale,
                },
                {
                    "role": "coach",
                    "turn": turn,
                    "claim": critique.claim,
                    "recommendation": critique.recommendation,
                    "sources": critique.sources,
                },
            ]
        )

    final_spec_path = run_dir / "final-spec.md"
    transcript_markdown_path = run_dir / "transcript.md"
    transcript_json_path = run_dir / "transcript.json"
    summary_path = run_dir / "summary.json"

    final_spec_path.write_text(state.build_final_spec(title=request.title))
    transcript_markdown_path.write_text(_build_transcript_markdown(request, state))
    transcript_json_path.write_text(json.dumps(transcript_records, indent=2) + "\n")

    result = SpecLoopRunResult(
        run_id=run_id,
        topic=request.topic,
        title=request.title,
        mode=request.mode,
        preferred_model_backend=request.preferred_model_backend,
        output_dir=str(run_dir),
        final_spec_path=str(final_spec_path),
        transcript_markdown_path=str(transcript_markdown_path),
        transcript_json_path=str(transcript_json_path),
        summary_path=str(summary_path),
        writer_turns_used=state.writer_turns_used,
        coach_turns_used=state.coach_turns_used,
        warnings=warnings,
    )
    summary_path.write_text(result.model_dump_json(indent=2) + "\n")
    return result


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "but-dad-spec-loop"


def _build_draft_markdown(request: SpecLoopRequest, turn: int, prior_recommendation: str) -> str:
    sections = [
        "## Objective",
        request.topic,
        "",
        "## Preferred model backend",
        request.preferred_model_backend,
        "",
        "## Scope",
        f"- Produce a single living spec artifact after writer turn {turn}.",
        "- Preserve a readable transcript for every writer and coach turn.",
        "- Keep the loop bounded and deterministic for local verification.",
        "",
        "## Working requirements",
        "- Expose a reusable MCP tool surface that callers can invoke locally.",
        "- Write a final spec artifact plus transcript artifacts to a predictable directory.",
        f"- Reflect the latest coach recommendation in this draft: {prior_recommendation}",
        "",
    ]

    if request.context:
        sections.extend(["## Context", *(f"- {item}" for item in request.context), ""])

    if request.constraints:
        sections.extend(["## Constraints", *(f"- {item}" for item in request.constraints), ""])

    acceptance_criteria = request.acceptance_criteria or [
        "A caller can run the loop locally and inspect the final spec.",
        "Artifacts are written under a stable output directory.",
        "Tests cover the core execution path and output contract.",
    ]
    sections.extend(["## Acceptance criteria", *(f"- {item}" for item in acceptance_criteria), ""])

    sections.extend(
        [
            "## Edge cases",
            "- Re-running the same spec loop name should overwrite artifacts deterministically.",
            "- Empty live research should not invent sources in preview mode.",
            "- Writer and coach turns must stop at the configured limits.",
            "",
            "## Changelog",
            f"- Turn {turn}: tightened the draft around the latest coach recommendation.",
        ]
    )
    return "\n".join(sections)


def _build_draft_rationale(turn: int, prior_recommendation: str) -> list[str]:
    return [
        "Preserve a single living specification instead of resetting between turns.",
        f"Use writer turn {turn} to absorb the latest coach feedback: {prior_recommendation}",
    ]


def _build_critique_claim(turn: int) -> str:
    if turn == 1:
        return "The first draft still needs sharper acceptance criteria and explicit artifact paths."
    if turn < 6:
        return "The draft is improving, but it still needs tighter failure-path handling and clearer verification steps."
    return "The loop has reached the configured bound; ship the current draft with the recorded transcript and noted deviations."


def _build_critique_recommendation(turn: int) -> str:
    if turn == 1:
        return "Add exact output filenames, keep the loop bounded, and document how callers verify the result locally."
    if turn < 6:
        return "Call out deterministic overwrite behavior, test the artifact contract, and keep sources empty unless live research actually ran."
    return "Stop iterating, publish the final artifact set, and carry the preferred Malachi backend forward as metadata for future live wiring."


def _build_transcript_markdown(request: SpecLoopRequest, state: SpecLoopState) -> str:
    lines = [
        "# But Dad MCP transcript",
        "",
        f"- Topic: {request.topic}",
        f"- Preferred model backend: {request.preferred_model_backend}",
        f"- Mode: {request.mode}",
        "",
    ]
    for turn, draft in enumerate(state.drafts, start=1):
        lines.extend([f"## Writer turn {turn}", "", draft.content, ""])
        if draft.rationale:
            lines.append("Rationale:")
            lines.extend(f"- {item}" for item in draft.rationale)
            lines.append("")
        critique = state.critiques[turn - 1]
        lines.extend(
            [
                f"## Coach turn {turn}",
                "",
                f"Claim: {critique.claim}",
                "",
                f"Recommendation: {critique.recommendation}",
                "",
                "Sources: _No live sources captured in preview mode._",
                "",
            ]
        )
    return "\n".join(lines)
