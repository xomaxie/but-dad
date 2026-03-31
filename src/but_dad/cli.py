from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

from .loop import LoopConfig, SpecLoopState


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="but-dad", description="Render a bounded writer/coach spec loop artifact.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Build a spec artifact from a structured turn log.")
    run_parser.add_argument("--input", required=True, type=Path, help="Path to a JSON file describing the loop turns.")
    run_parser.add_argument("--output", required=True, type=Path, help="Path for the rendered markdown artifact.")
    run_parser.add_argument("--title", help="Optional title override for the rendered artifact.")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        return run(args.input, args.output, args.title)

    parser.error(f"unsupported command: {args.command}")
    return 2


def run(input_path: Path, output_path: Path, title_override: str | None = None) -> int:
    payload = json.loads(input_path.read_text())
    state = _state_from_payload(payload)
    title = title_override or payload.get("title", "But Dad Spec")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(state.build_final_spec(title=title))

    print(
        f"Wrote {output_path} "
        f"(writer turns: {state.writer_turns_used}/{state.config.max_writer_turns}, "
        f"coach turns: {state.coach_turns_used}/{state.config.max_coach_turns})"
    )
    return 0


def _state_from_payload(payload: dict[str, Any]) -> SpecLoopState:
    config_data = payload.get("config", {})
    state = SpecLoopState(
        config=LoopConfig(
            max_writer_turns=config_data.get("max_writer_turns", 6),
            max_coach_turns=config_data.get("max_coach_turns", 6),
        )
    )

    turns = payload.get("turns", [])
    if not isinstance(turns, list):
        raise ValueError("turns must be a list")

    for turn in turns:
        role = turn.get("role")
        if role == "writer":
            state.add_draft(turn["content"], rationale=turn.get("rationale"))
            continue
        if role == "coach":
            state.add_critique(
                turn["claim"],
                turn["recommendation"],
                sources=turn.get("sources"),
            )
            continue
        raise ValueError(f"unsupported turn role: {role!r}")

    return state
