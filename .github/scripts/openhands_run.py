import json
import os
import sys
import time
from pathlib import Path

import requests


def read_prompt(value: str) -> str:
    path = Path(value)
    if path.exists() and path.is_file():
        return path.read_text(encoding="utf-8")
    return value


def api_session(api_key: str, base_url: str):
    session = requests.Session()
    session.headers.update(
        {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
    )
    return session, base_url.rstrip("/")


def create_conversation(session, base_url: str, initial_user_msg: str, repository: str, selected_branch: str):
    body = {"initial_user_msg": initial_user_msg}
    if repository:
        body["repository"] = repository
    if selected_branch:
        body["selected_branch"] = selected_branch
    response = session.post(f"{base_url}/api/conversations", json=body)
    response.raise_for_status()
    return response.json()


def get_conversation(session, base_url: str, conversation_id: str):
    response = session.get(f"{base_url}/api/conversations/{conversation_id}")
    response.raise_for_status()
    return response.json()


def write_outputs(conversation_id: str, status: str, conversation_url: str) -> None:
    output_path = os.getenv("GITHUB_OUTPUT")
    if not output_path:
        return
    with open(output_path, "a", encoding="utf-8") as handle:
        handle.write(f"conversation-id={conversation_id}\n")
        handle.write(f"status={status}\n")
        handle.write(f"conversation-url={conversation_url}\n")


def main() -> int:
    api_key = os.getenv("OPENHANDS_API_KEY")
    if not api_key:
        print("OPENHANDS_API_KEY is required", file=sys.stderr)
        return 2

    prompt_input = os.getenv("INPUT_PROMPT", "").strip()
    if not prompt_input:
        print("inputs.prompt is required", file=sys.stderr)
        return 2

    initial_user_msg = read_prompt(prompt_input)
    repository = os.getenv("INPUT_REPOSITORY", "").strip() or os.getenv("GITHUB_REPOSITORY", "")
    selected_branch = os.getenv("INPUT_SELECTED_BRANCH", "").strip() or "main"
    base_url = os.getenv("INPUT_BASE_URL", "").strip() or "https://app.all-hands.dev"
    poll = os.getenv("INPUT_POLL", "true").lower() == "true"
    timeout = int(os.getenv("INPUT_TIMEOUT", "1200"))
    interval = int(os.getenv("INPUT_INTERVAL", "30"))

    session, base_url = api_session(api_key, base_url)
    try:
        created = create_conversation(session, base_url, initial_user_msg, repository, selected_branch)
    except requests.HTTPError as exc:
        print(f"Create conversation failed: {exc} - {getattr(exc.response, 'text', '')}", file=sys.stderr)
        return 1

    conversation_id = created.get("conversation_id") or created.get("id") or ""
    status = str(created.get("status", "")).upper() or "UNKNOWN"
    if not conversation_id:
        print(f"Unexpected response: {json.dumps(created, indent=2)}", file=sys.stderr)
        return 1

    conversation_url = f"{base_url}/conversations/{conversation_id}"
    print(f"Conversation created: {conversation_id} (status={status})")
    print(f"View conversation: {conversation_url}")

    if not poll:
        write_outputs(conversation_id, status, conversation_url)
        return 0

    start = time.time()
    last_status = status
    while time.time() - start < timeout:
        try:
            conversation = get_conversation(session, base_url, conversation_id)
        except requests.HTTPError as exc:
            print(f"Polling error: {exc} - {getattr(exc.response, 'text', '')}", file=sys.stderr)
            time.sleep(interval)
            continue

        last_status = str(conversation.get("status", "")).upper() or "UNKNOWN"
        print(f"Status: {last_status}")
        if last_status in {"STOPPED", "FAILED", "ERROR", "CANCELLED"}:
            break
        time.sleep(interval)

    write_outputs(conversation_id, last_status, conversation_url)
    if last_status in {"FAILED", "ERROR", "CANCELLED"}:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
