# OpenHands automation

This repository includes a GitHub Actions workflow at `.github/workflows/openhands-resolver.yml`.

## Trigger modes

The workflow starts OpenHands when either of these happens:
- an issue is labeled `OpenHands`
- a new issue comment starts with `@openhands`

It can also be started manually with `workflow_dispatch` by passing an issue number.

## Required GitHub configuration

Add this repository secret:
- `OPENHANDS_API_KEY` — API key for the OpenHands instance

Optional repository variable:
- `OPENHANDS_BASE_URL` — base URL for a self-hosted OpenHands API
  - default: `https://app.all-hands.dev`
  - for your tailnet-hosted deployment, set this to the API base URL exposed by that instance if you want the workflow to use it instead of OpenHands Cloud

## What the workflow does

1. Loads the target issue and its comments.
2. Builds a focused prompt that tells OpenHands to follow `AGENTS.md`.
3. Starts an OpenHands conversation for the repository.
4. Posts a status comment back on the issue with the conversation link.

## Expected repo setup

For the easiest flow later:
1. open or create an issue
2. use the **Spec loop task** issue template if it fits
3. add the `OpenHands` label to start automation
4. steer the run by commenting with `@openhands ...` if needed

If the `OPENHANDS_API_KEY` secret is missing, the workflow will comment on the issue and explain what needs to be configured.

## Notes

- The workflow accepts the `OpenHands` label regardless of case.
- The workflow is biased toward small, issue-focused changes.
- Planning issues should result in planning/docs work first, matching the repository guidance.
- If you want OpenHands to work from a comment, begin the comment with `@openhands`.
