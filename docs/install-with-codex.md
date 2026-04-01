# Install But Dad with Codex

Use these instructions when an LLM or agent should install and run **But Dad** locally.

## Goal

Clone the repo, create a Python virtualenv, install the package with MCP support, and verify the MCP server starts.

## Steps

```bash
git clone https://github.com/xomaxie/but-dad.git
cd but-dad
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev,fast-agent]'
PYTHONPATH=src .venv/bin/python -m pytest -q
PYTHONPATH=src .venv/bin/python -m but_dad.mcp_server --transport stdio
```

## Notes

- Use `pip install -e '.[dev]'` if you only need preview mode.
- Use `pip install -e '.[dev,fast-agent]'` if you want the live Malachi-backed path.
- For live mode, set local config such as:

```bash
export BUT_DAD_FASTAGENT_CONFIG_PATH=/absolute/path/to/fastagent.config.yaml
export BUT_DAD_FASTAGENT_MODEL=Malachi
```

## One-line prompt for an LLM

> Clone `https://github.com/xomaxie/but-dad`, create a virtualenv, install it with `pip install -e '.[dev,fast-agent]'`, run tests, then start the MCP server with `PYTHONPATH=src .venv/bin/python -m but_dad.mcp_server --transport stdio`.
