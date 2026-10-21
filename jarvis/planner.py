import json
import urllib.request

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"

SYSTEM_PROMPT = """You are Jarvis, an assistant running on the user's Windows 11 PC.
Reply with ONLY a JSON object, no other text:
{"command": "<one PowerShell command line, or empty>", "answer": "<short reply to the user>"}
Put a command in "command" when the user wants something done on this PC. Leave it empty when
no command is needed. Never put secrets, passwords or API keys into a command."""


def plan(text, api_key, model, timeout=60):
    """Ask Claude to turn a request into a PowerShell command and/or an answer."""
    body = json.dumps({
        "model": model,
        "max_tokens": 800,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": text}],
    }).encode("utf-8")
    request = urllib.request.Request(API_URL, data=body, headers={
        "content-type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": API_VERSION,
    })
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = json.load(response)

    raw = "".join(block.get("text", "") for block in data.get("content", []) if block.get("type") == "text").strip()
    if raw.startswith("```"):
        raw = raw.strip("`").removeprefix("json").strip()
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        return {"command": "", "answer": raw}
    return {"command": str(result.get("command") or ""), "answer": str(result.get("answer") or "")}
