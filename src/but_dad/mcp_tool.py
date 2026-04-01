from __future__ import annotations

import asyncio
import json
import os
import re
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Callable, Literal

from pydantic import BaseModel, Field

from .fast_agent_experiment import (
    DEFAULT_CONFIG_PATH,
    DEFAULT_LIVE_MODEL,
    extract_terminal_status,
    run_live_experiment,
)
from .loop import LoopConfig, SpecLoopState

DEFAULT_TITLE = "But Dad Spec"
DEFAULT_MODE = "preview"
DEFAULT_PREFERRED_MODEL_BACKEND = "Malachi"
DEFAULT_OUTPUT_DIR = Path("docs/experiments/mcp-tool")
DEFAULT_FASTAGENT_CONFIG_ENV = "BUT_DAD_FASTAGENT_CONFIG_PATH"
DEFAULT_FASTAGENT_MODEL_ENV = "BUT_DAD_FASTAGENT_MODEL"
VALID_TERMINAL_STATUSES = {
    "success",
    "bounded_stop",
    "timeout",
    "config_error",
    "execution_error",
}


class ConfigError(ValueError):
    pass


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
    mode: Literal["preview", "live"] = DEFAULT_MODE
    config_path: str | None = None
    model: str | None = None
    time_budget_seconds: float | None = Field(default=None, gt=0)


class SpecLoopRunResult(BaseModel):
    run_id: str
    topic: str
    title: str
    mode: Literal["preview", "live"]
    status: Literal["success", "bounded_stop", "timeout", "config_error", "execution_error"]
    preferred_model_backend: str
    model: str | None = None
    output_dir: str
    final_spec_path: str
    transcript_markdown_path: str
    writer_transcript_path: str
    coach_transcript_path: str
    transcript_json_path: str
    sources_path: str
    metrics_path: str
    run_metadata_path: str
    summary_path: str
    logs_path: str
    writer_turns_used: int
    coach_turns_used: int
    warnings: list[str] = Field(default_factory=list)
    error_message: str | None = None


@dataclass(slots=True)
class ArtifactBundle:
    final_spec: str
    interleaved_transcript: str
    writer_transcript: str
    coach_transcript: str
    transcript_records: list[dict[str, object]]
    sources: list[dict[str, object]]
    status: str
    writer_turns_used: int
    coach_turns_used: int
    warnings: list[str] = field(default_factory=list)


LiveRunner = Callable[[SpecLoopRequest, Path], str]


def run_spec_loop(request: SpecLoopRequest, live_runner: LiveRunner | None = None) -> SpecLoopRunResult:
    run_id = _slugify(request.run_name or request.topic)
    run_dir = Path(request.output_dir) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    started_at = _utcnow()
    started_perf = perf_counter()
    logs: list[str] = [f"{started_at} start mode={request.mode} run_id={run_id}"]
    warnings: list[str] = []
    error_message: str | None = None
    error_type: str | None = None

    final_spec_path = run_dir / "final-spec.md"
    transcript_markdown_path = run_dir / "transcript.md"
    writer_transcript_path = run_dir / "transcript-writer.md"
    coach_transcript_path = run_dir / "transcript-coach.md"
    transcript_json_path = run_dir / "transcript.json"
    sources_path = run_dir / "sources.json"
    metrics_path = run_dir / "metrics.json"
    run_metadata_path = run_dir / "run.json"
    summary_path = run_dir / "summary.json"
    logs_path = run_dir / "logs.txt"
    normalized_input_path = run_dir / "normalized-input.json"
    raw_live_output_path = run_dir / "raw-live-output.md"

    normalized_input_path.write_text(request.model_dump_json(indent=2) + "\n")

    try:
        if request.mode == "live":
            bundle = _run_live_bundle(request, raw_live_output_path, live_runner)
        else:
            bundle = _run_preview_bundle(request)
        logs.append(
            f"{_utcnow()} completed mode={request.mode} status={bundle.status} "
            f"writer_turns={bundle.writer_turns_used} coach_turns={bundle.coach_turns_used}"
        )
        warnings.extend(bundle.warnings)
        status = bundle.status
    except TimeoutError as exc:
        status = "timeout"
        error_message = str(exc) or "The spec loop exceeded its time budget."
        error_type = type(exc).__name__
        warnings.append("The run timed out before a clean terminal success state was reached.")
        logs.append(f"{_utcnow()} timeout {error_message}")
        bundle = _recover_live_bundle(
            request=request,
            raw_live_output_path=raw_live_output_path,
            status=status,
            error_message=error_message,
        )
    except ConfigError as exc:
        status = "config_error"
        error_message = str(exc)
        error_type = type(exc).__name__
        warnings.append("The live run could not start because the local fast-agent configuration was invalid.")
        logs.append(f"{_utcnow()} config_error {error_message}")
        bundle = _build_failed_bundle(request, status=status, error_message=error_message)
    except Exception as exc:
        status = "execution_error"
        error_message = str(exc) or type(exc).__name__
        error_type = type(exc).__name__
        warnings.append("The run failed before a clean terminal success state was reached.")
        logs.append(f"{_utcnow()} execution_error {error_type}: {error_message}")
        logs.append(traceback.format_exc().rstrip())
        bundle = _recover_live_bundle(
            request=request,
            raw_live_output_path=raw_live_output_path,
            status=status,
            error_message=error_message,
        )

    warnings = [*warnings, *bundle.warnings]
    final_spec_path.write_text(_ensure_trailing_newline(bundle.final_spec))
    transcript_markdown_path.write_text(_ensure_trailing_newline(bundle.interleaved_transcript))
    writer_transcript_path.write_text(_ensure_trailing_newline(bundle.writer_transcript))
    coach_transcript_path.write_text(_ensure_trailing_newline(bundle.coach_transcript))
    transcript_json_path.write_text(json.dumps(bundle.transcript_records, indent=2) + "\n")
    sources_path.write_text(json.dumps(bundle.sources, indent=2) + "\n")

    duration_seconds = round(perf_counter() - started_perf, 3)
    metrics = {
        "duration_seconds": duration_seconds,
        "source_count": len(bundle.sources),
        "word_count_final_spec": _word_count(bundle.final_spec),
        "iterations_completed": min(bundle.writer_turns_used, bundle.coach_turns_used),
    }
    metrics_path.write_text(json.dumps(metrics, indent=2) + "\n")

    model_name = _resolve_live_model_name(request)
    completed_at = _utcnow()
    result = SpecLoopRunResult(
        run_id=run_id,
        topic=request.topic,
        title=request.title,
        mode=request.mode,
        status=status,
        preferred_model_backend=request.preferred_model_backend,
        model=model_name,
        output_dir=str(run_dir),
        final_spec_path=str(final_spec_path),
        transcript_markdown_path=str(transcript_markdown_path),
        writer_transcript_path=str(writer_transcript_path),
        coach_transcript_path=str(coach_transcript_path),
        transcript_json_path=str(transcript_json_path),
        sources_path=str(sources_path),
        metrics_path=str(metrics_path),
        run_metadata_path=str(run_metadata_path),
        summary_path=str(summary_path),
        logs_path=str(logs_path),
        writer_turns_used=bundle.writer_turns_used,
        coach_turns_used=bundle.coach_turns_used,
        warnings=warnings,
        error_message=error_message,
    )

    run_metadata = {
        "run_id": run_id,
        "topic": request.topic,
        "title": request.title,
        "mode": request.mode,
        "status": status,
        "started_at": started_at,
        "completed_at": completed_at,
        "config_snapshot": request.model_dump(),
        "completed_turns": {
            "writer": bundle.writer_turns_used,
            "coach": bundle.coach_turns_used,
        },
        "model_info": {
            "preferred_model_backend": request.preferred_model_backend,
            "model": model_name,
            "config_path": request.config_path or os.environ.get(DEFAULT_FASTAGENT_CONFIG_ENV),
        },
        "error": {
            "type": error_type,
            "message": error_message,
        },
        "warnings": warnings,
        "artifacts": {
            "normalized_input": str(normalized_input_path),
            "final_spec": str(final_spec_path),
            "transcript_interleaved": str(transcript_markdown_path),
            "transcript_writer": str(writer_transcript_path),
            "transcript_coach": str(coach_transcript_path),
            "transcript_json": str(transcript_json_path),
            "sources": str(sources_path),
            "metrics": str(metrics_path),
            "summary": str(summary_path),
            "logs": str(logs_path),
            "raw_live_output": str(raw_live_output_path) if raw_live_output_path.exists() else None,
        },
    }
    run_metadata_path.write_text(json.dumps(run_metadata, indent=2) + "\n")
    summary_path.write_text(result.model_dump_json(indent=2) + "\n")
    logs.append(f"{completed_at} wrote run metadata and summary")
    logs_path.write_text("\n".join(logs).rstrip() + "\n")
    return result


def _run_preview_bundle(request: SpecLoopRequest) -> ArtifactBundle:
    state = SpecLoopState(
        config=LoopConfig(
            max_writer_turns=request.max_writer_turns,
            max_coach_turns=request.max_coach_turns,
        )
    )
    transcript_records: list[dict[str, object]] = []

    while state.can_continue():
        turn = state.writer_turns_used + 1
        prior_recommendation = (
            state.critiques[-1].recommendation if state.critiques else "Define the first living draft."
        )
        draft = state.add_draft(
            content=_build_draft_markdown(request, turn, prior_recommendation),
            rationale=_build_draft_rationale(turn, prior_recommendation),
        )
        critique = state.add_critique(
            claim=_build_critique_claim(turn, state.config),
            recommendation=_build_critique_recommendation(turn, state.config),
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
                    "content": _render_preview_coach_turn(critique),
                    "sources": critique.sources,
                },
            ]
        )

    return ArtifactBundle(
        final_spec=state.build_final_spec(title=request.title),
        interleaved_transcript=_build_preview_interleaved_markdown(request, state),
        writer_transcript=_build_preview_writer_transcript(state),
        coach_transcript=_build_preview_coach_transcript(state),
        transcript_records=transcript_records,
        sources=[],
        status="bounded_stop",
        writer_turns_used=state.writer_turns_used,
        coach_turns_used=state.coach_turns_used,
        warnings=[
            "Preview mode stays deterministic and does not execute Malachi or live research.",
            "Use mode=live with a configured fast-agent setup to run the real writer/coach loop.",
        ],
    )


def _run_live_bundle(
    request: SpecLoopRequest,
    raw_live_output_path: Path,
    live_runner: LiveRunner | None,
) -> ArtifactBundle:
    runner = live_runner or _default_live_runner
    markdown = runner(request, raw_live_output_path)
    raw_live_output_path.write_text(_ensure_trailing_newline(markdown))
    return _parse_live_markdown(request, markdown)


def _default_live_runner(request: SpecLoopRequest, raw_live_output_path: Path) -> str:
    config_path = _resolve_live_config_path(request.config_path)
    loop = LoopConfig(
        max_writer_turns=request.max_writer_turns,
        max_coach_turns=request.max_coach_turns,
    )
    model = _resolve_live_model_name(request)

    async def _execute() -> str:
        task = run_live_experiment(
            topic=request.topic,
            output_path=raw_live_output_path,
            config_path=config_path,
            model=model,
            loop=loop,
        )
        if request.time_budget_seconds is not None:
            return await asyncio.wait_for(task, timeout=request.time_budget_seconds)
        return await task

    return asyncio.run(_execute())


def _resolve_live_config_path(config_path: str | None) -> str:
    candidate = config_path or os.environ.get(DEFAULT_FASTAGENT_CONFIG_ENV) or DEFAULT_CONFIG_PATH
    if candidate == DEFAULT_CONFIG_PATH and not Path(candidate).exists():
        raise ConfigError(
            "Live mode requires a real fast-agent config path. "
            f"Pass config_path=... or set {DEFAULT_FASTAGENT_CONFIG_ENV} to a local fastagent config file."
        )
    if not Path(candidate).exists():
        raise ConfigError(f"Live mode config_path does not exist: {candidate}")
    return candidate


def _resolve_live_model_name(request: SpecLoopRequest) -> str | None:
    if request.mode != "live":
        return request.model
    return request.model or os.environ.get(DEFAULT_FASTAGENT_MODEL_ENV) or request.preferred_model_backend or DEFAULT_LIVE_MODEL


def _parse_live_markdown(request: SpecLoopRequest, markdown: str) -> ArtifactBundle:
    sections = _extract_sections(markdown)
    final_spec = sections["final_spec"].strip() or "_No final spec was captured._"
    writer_transcript = sections["writer_transcript"].strip() or "_No writer transcript was captured._"
    coach_transcript = sections["coach_transcript"].strip() or "_No coach transcript was captured._"
    run_summary = sections["run_summary"]
    writer_turns = _extract_completed_turns(run_summary, "completed_writer_turns")
    coach_turns = _extract_completed_turns(run_summary, "completed_coach_turns")
    if writer_turns is None:
        writer_turns = len(_split_turn_sections(writer_transcript, "Writer"))
    if coach_turns is None:
        coach_turns = len(_split_turn_sections(coach_transcript, "Coach"))

    status = extract_terminal_status(run_summary)
    if status not in VALID_TERMINAL_STATUSES:
        status = (
            "bounded_stop"
            if writer_turns >= request.max_writer_turns and coach_turns >= request.max_coach_turns
            else "success"
        )

    transcript_records = _build_live_transcript_records(writer_transcript, coach_transcript)
    sources = _build_source_records(sections["source_appendix"], coach_transcript)
    interleaved_transcript = _build_interleaved_live_transcript(
        request=request,
        writer_transcript=writer_transcript,
        coach_transcript=coach_transcript,
        status=status,
    )
    warnings: list[str] = []
    if not sources:
        warnings.append("The live run completed without any captured source URLs.")

    return ArtifactBundle(
        final_spec=final_spec,
        interleaved_transcript=interleaved_transcript,
        writer_transcript=writer_transcript,
        coach_transcript=coach_transcript,
        transcript_records=transcript_records,
        sources=sources,
        status=status,
        writer_turns_used=writer_turns,
        coach_turns_used=coach_turns,
        warnings=warnings,
    )


def _build_failed_bundle(request: SpecLoopRequest, status: str, error_message: str) -> ArtifactBundle:
    final_spec = "\n".join(
        [
            f"# {request.title}",
            "",
            "## Terminal status",
            f"- {status}",
            "",
            "## Failure summary",
            error_message,
            "",
            "## Topic",
            request.topic,
            "",
        ]
    )
    interleaved = "\n".join(
        [
            "# But Dad MCP transcript",
            "",
            f"- Topic: {request.topic}",
            f"- Preferred model backend: {request.preferred_model_backend}",
            f"- Mode: {request.mode}",
            f"- Status: {status}",
            "",
            "_No complete turns were recorded before the run stopped._",
            "",
        ]
    )
    message = "_No transcript captured before the run stopped._"
    return ArtifactBundle(
        final_spec=final_spec,
        interleaved_transcript=interleaved,
        writer_transcript=message,
        coach_transcript=message,
        transcript_records=[],
        sources=[],
        status=status,
        writer_turns_used=0,
        coach_turns_used=0,
    )


def _recover_live_bundle(
    request: SpecLoopRequest,
    raw_live_output_path: Path,
    status: str,
    error_message: str,
) -> ArtifactBundle:
    if not raw_live_output_path.exists():
        return _build_failed_bundle(request, status=status, error_message=error_message)

    markdown = raw_live_output_path.read_text()
    if not markdown.strip():
        return _build_failed_bundle(request, status=status, error_message=error_message)

    try:
        return _parse_partial_live_markdown(
            request=request,
            markdown=markdown,
            status=status,
            error_message=error_message,
        )
    except Exception:
        return _build_failed_bundle(request, status=status, error_message=error_message)


def _parse_partial_live_markdown(
    request: SpecLoopRequest,
    markdown: str,
    status: str,
    error_message: str,
) -> ArtifactBundle:
    sections = _extract_sections(markdown, require_all=False)
    final_spec = sections["final_spec"].strip()
    writer_transcript = sections["writer_transcript"].strip()
    coach_transcript = sections["coach_transcript"].strip()
    run_summary = sections["run_summary"]

    writer_turns = _extract_completed_turns(run_summary, "completed_writer_turns")
    coach_turns = _extract_completed_turns(run_summary, "completed_coach_turns")
    if writer_turns is None:
        writer_turns = len(_split_turn_sections(writer_transcript, "Writer"))
    if coach_turns is None:
        coach_turns = len(_split_turn_sections(coach_transcript, "Coach"))

    transcript_records = _build_live_transcript_records(writer_transcript, coach_transcript)
    sources = _build_source_records(sections["source_appendix"], coach_transcript)

    if not final_spec:
        final_spec = "\n".join(
            [
                f"# {request.title}",
                "",
                "## Terminal status",
                f"- {status}",
                "",
                "## Failure summary",
                error_message,
                "",
            ]
        )

    return ArtifactBundle(
        final_spec=final_spec,
        interleaved_transcript=_build_interleaved_live_transcript(
            request=request,
            writer_transcript=writer_transcript,
            coach_transcript=coach_transcript,
            status=status,
        ),
        writer_transcript=writer_transcript or "_No writer transcript was captured._",
        coach_transcript=coach_transcript or "_No coach transcript was captured._",
        transcript_records=transcript_records,
        sources=sources,
        status=status,
        writer_turns_used=writer_turns,
        coach_turns_used=coach_turns,
        warnings=["Partial live output was captured before the run stopped."],
    )


def _extract_sections(markdown: str, require_all: bool = True) -> dict[str, str]:
    pattern = re.compile(
        r"^# (?P<name>Final spec|Writer transcript|Coach transcript|Source appendix|Run summary)\s*$",
        re.MULTILINE,
    )
    matches = list(pattern.finditer(markdown))
    if require_all and len(matches) < 5:
        raise ValueError(
            "Live output is missing one or more required sections: "
            "# Final spec, # Writer transcript, # Coach transcript, # Source appendix, # Run summary."
        )

    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown)
        key = match.group("name").lower().replace(" ", "_")
        sections[key] = markdown[start:end].strip()

    required = {"final_spec", "writer_transcript", "coach_transcript", "source_appendix", "run_summary"}
    missing = sorted(required - set(sections))
    if require_all and missing:
        raise ValueError(f"Live output is missing required sections: {', '.join(missing)}")
    for key in required:
        sections.setdefault(key, "")
    return sections


def _extract_completed_turns(run_summary: str, key: str) -> int | None:
    match = re.search(rf"{re.escape(key)}\s*:\s*(\d+)", run_summary, re.IGNORECASE)
    if not match:
        return None
    return int(match.group(1))


def _build_live_transcript_records(
    writer_transcript: str,
    coach_transcript: str,
) -> list[dict[str, object]]:
    writer_turns = {turn: content for turn, content in _split_turn_sections(writer_transcript, "Writer")}
    coach_turns = {turn: content for turn, content in _split_turn_sections(coach_transcript, "Coach")}
    records: list[dict[str, object]] = []
    for turn in sorted(set(writer_turns) | set(coach_turns)):
        writer_content = writer_turns.get(turn)
        if writer_content is not None:
            records.append({"role": "writer", "turn": turn, "content": writer_content})
        coach_content = coach_turns.get(turn)
        if coach_content is not None:
            records.append(
                {
                    "role": "coach",
                    "turn": turn,
                    "content": coach_content,
                    "sources": _extract_urls(coach_content),
                }
            )
    return records


def _build_source_records(source_appendix: str, coach_transcript: str) -> list[dict[str, object]]:
    urls = _extract_urls(source_appendix) or _extract_urls(coach_transcript)
    if not urls:
        return []

    coach_turns = _split_turn_sections(coach_transcript, "Coach")
    records: list[dict[str, object]] = []
    for url in urls:
        used_in_turns = sorted(turn for turn, content in coach_turns if url in content)
        records.append(
            {
                "title": url,
                "url": url,
                "used_in_turns": used_in_turns,
                "notes": "Captured from the live fast-agent transcript.",
            }
        )
    return records


def _build_interleaved_live_transcript(
    request: SpecLoopRequest,
    writer_transcript: str,
    coach_transcript: str,
    status: str,
) -> str:
    writer_turns = {turn: content for turn, content in _split_turn_sections(writer_transcript, "Writer")}
    coach_turns = {turn: content for turn, content in _split_turn_sections(coach_transcript, "Coach")}
    lines = [
        "# But Dad MCP transcript",
        "",
        f"- Topic: {request.topic}",
        f"- Preferred model backend: {request.preferred_model_backend}",
        f"- Mode: {request.mode}",
        f"- Status: {status}",
        "",
    ]
    for turn in sorted(set(writer_turns) | set(coach_turns)):
        if turn in writer_turns:
            lines.extend([f"## Writer turn {turn}", "", writer_turns[turn], ""])
        if turn in coach_turns:
            lines.extend([f"## Coach turn {turn}", "", coach_turns[turn], ""])
    return "\n".join(lines).strip()


def _split_turn_sections(markdown: str, role: str) -> list[tuple[int, str]]:
    pattern = re.compile(rf"^## {role} turn (\d+)\s*$", re.MULTILINE)
    matches = list(pattern.finditer(markdown))
    sections: list[tuple[int, str]] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown)
        sections.append((int(match.group(1)), markdown[start:end].strip()))
    return sections


def _extract_urls(text: str) -> list[str]:
    seen: set[str] = set()
    urls: list[str] = []
    for raw in re.findall(r"https?://[^\s)>]+", text):
        url = raw.rstrip(".,]")
        if url in seen:
            continue
        seen.add(url)
        urls.append(url)
    return urls


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
        "- Keep the loop bounded and inspectable for local verification.",
        "",
        "## Working requirements",
        "- Expose a reusable MCP tool surface that callers can invoke locally.",
        "- Write final-spec.md, transcript.md, run.json, and summary.json to a predictable directory.",
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
            "- Missing live research must be stated explicitly instead of inventing citations.",
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


def _build_critique_claim(turn: int, config: LoopConfig) -> str:
    if turn == 1:
        return "The first draft still needs sharper acceptance criteria and explicit artifact paths."
    if turn < min(config.max_writer_turns, config.max_coach_turns):
        return "The draft is improving, but it still needs tighter failure-path handling and clearer verification steps."
    return "The loop has reached the configured bound; ship the current draft with the recorded transcript and noted deviations."


def _build_critique_recommendation(turn: int, config: LoopConfig) -> str:
    if turn == 1:
        return "Add exact output filenames, keep the loop bounded, and document how callers verify the result locally."
    if turn < min(config.max_writer_turns, config.max_coach_turns):
        return "Call out deterministic overwrite behavior, test the artifact contract, and keep sources empty unless live research actually ran."
    return "Stop iterating, publish the final artifact set, and carry the preferred Malachi backend forward as metadata for future live wiring."


def _build_preview_writer_transcript(state: SpecLoopState) -> str:
    lines = ["# Writer transcript", ""]
    for draft in state.drafts:
        lines.extend([f"## Writer turn {draft.version}", "", draft.content, ""])
        if draft.rationale:
            lines.append("Rationale:")
            lines.extend(f"- {item}" for item in draft.rationale)
            lines.append("")
    return "\n".join(lines).strip()


def _build_preview_coach_transcript(state: SpecLoopState) -> str:
    lines = ["# Coach transcript", ""]
    for index, critique in enumerate(state.critiques, start=1):
        lines.extend([f"## Coach turn {index}", "", _render_preview_coach_turn(critique), ""])
    return "\n".join(lines).strip()


def _build_preview_interleaved_markdown(request: SpecLoopRequest, state: SpecLoopState) -> str:
    lines = [
        "# But Dad MCP transcript",
        "",
        f"- Topic: {request.topic}",
        f"- Preferred model backend: {request.preferred_model_backend}",
        f"- Mode: {request.mode}",
        "- Status: bounded_stop",
        "",
    ]
    for turn, draft in enumerate(state.drafts, start=1):
        lines.extend([f"## Writer turn {turn}", "", draft.content, ""])
        if draft.rationale:
            lines.append("Rationale:")
            lines.extend(f"- {item}" for item in draft.rationale)
            lines.append("")
        lines.extend([f"## Coach turn {turn}", "", _render_preview_coach_turn(state.critiques[turn - 1]), ""])
    return "\n".join(lines).strip()


def _render_preview_coach_turn(critique: object) -> str:
    return "\n".join(
        [
            "Overall rating",
            "",
            "FAIR",
            "",
            "Blocking issues",
            "",
            f"{critique.claim}",
            "",
            "Recommended edits",
            "",
            f"{critique.recommendation}",
            "",
            "Sources consulted",
            "",
            "_No live sources captured in preview mode._",
        ]
    )


def _utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _ensure_trailing_newline(text: str) -> str:
    return text if text.endswith("\n") else f"{text}\n"


def _word_count(text: str) -> int:
    return len(re.findall(r"\b\S+\b", text))
