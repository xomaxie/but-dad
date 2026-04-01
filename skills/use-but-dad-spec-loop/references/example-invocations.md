# Example invocations

## Good cases

### Draft a first real spec
Use `preview`.

### Improve an existing architecture or MCP spec
Use `preview` first, then `live` if current docs or standards matter.

### Anything depending on current docs or standards
Use `live`.
Examples:
- MCP transport/lifecycle requirements
- vendor API integration rules
- recently changed product constraints

## Naming runs

Use stable, filesystem-safe names such as:
- `auth-mcp-plan`
- `pricing-redesign-spec`
- `public-mcp-rollout-v2`

## Suggested summary phrasing

- "Ran But Dad spec loop in preview mode and wrote the final spec to ..."
- "Ran the live Malachi-backed spec loop; the coach cited current sources and tightened ..."

## Read order

1. `summary.json`
2. `final-spec.md`
3. `transcript-coach.md`
4. `sources.json`
