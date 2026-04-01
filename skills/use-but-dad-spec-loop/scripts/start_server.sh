#!/usr/bin/env bash
set -euo pipefail
cd /opt/agent-zero/usr/workdir/but-dad
PYTHONPATH=src .venv/bin/python -m but_dad.mcp_server --transport stdio
