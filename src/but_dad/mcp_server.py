from __future__ import annotations

import argparse
from typing import Sequence

from mcp.server.fastmcp import FastMCP

from .mcp_tool import (
    DEFAULT_OUTPUT_DIR,
    DEFAULT_PREFERRED_MODEL_BACKEND,
    DEFAULT_TITLE,
    SpecLoopRequest,
    SpecLoopRunResult,
    run_spec_loop,
)


def build_server() -> FastMCP:
    server = FastMCP("But Dad", json_response=True)

    @server.tool(
        name="run_spec_loop",
        description="Run the bounded But Dad writer/coach loop and write deterministic review artifacts.",
        structured_output=True,
    )
    def run_spec_loop_tool(
        topic: str,
        title: str = DEFAULT_TITLE,
        run_name: str | None = None,
        output_dir: str = str(DEFAULT_OUTPUT_DIR),
        context: list[str] | None = None,
        constraints: list[str] | None = None,
        acceptance_criteria: list[str] | None = None,
        max_writer_turns: int = 6,
        max_coach_turns: int = 6,
        preferred_model_backend: str = DEFAULT_PREFERRED_MODEL_BACKEND,
    ) -> SpecLoopRunResult:
        request = SpecLoopRequest(
            topic=topic,
            title=title,
            run_name=run_name,
            output_dir=output_dir,
            context=context or [],
            constraints=constraints or [],
            acceptance_criteria=acceptance_criteria or [],
            max_writer_turns=max_writer_turns,
            max_coach_turns=max_coach_turns,
            preferred_model_backend=preferred_model_backend,
        )
        return run_spec_loop(request)

    return server


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m but_dad.mcp_server", description="Run the But Dad MCP server.")
    parser.add_argument("--transport", default="stdio", choices=["stdio", "sse", "streamable-http"])
    args = parser.parse_args(argv)
    build_server().run(transport=args.transport)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
