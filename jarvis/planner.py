import json
import subprocess
import urllib.request

from .config import ROOT

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"

SYSTEM_PROMPT = """You are Jarvis, an assistant running on the user's Windows 11 PC.
Reply with ONLY a JSON object, no other text:
{"command": "<one PowerShell command line, or empty>", "answer": "<short reply to the user>"}
Put a command in "command" when the user wants something done on this PC. Leave it empty when
no command is needed. Never put secrets, passwords or API keys into a command."""


def _parse(raw):
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`").removeprefix("json").strip()
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        return {"command": "", "answer": raw}
    return {"command": str(result.get("command") or ""), "answer": str(result.get("answer") or "")}


def plan_with_api(text, api_key, model, timeout=60):
    """Ask Claude through the Anthropic API (needs ANTHROPIC_API_KEY)."""
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
    raw = "".join(block.get("text", "") for block in data.get("content", []) if block.get("type") == "text")
    return _parse(raw)


def plan_with_cli(text, model, claude="claude", timeout=120):
    """Ask Claude through the Claude Code CLI, which uses your existing claude.ai login. No API key needed."""
    proc = subprocess.run(
        [claude, "-p", text, "--system-prompt", SYSTEM_PROMPT, "--tools", "", "--output-format", "text", "--model", model],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        cwd=ROOT,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout).strip() or f"claude exited with code {proc.returncode}")
    return _parse(proc.stdout)


def plan_request(text, settings):
    """Use the API if a key is set, otherwise the logged-in Claude CLI."""
    if settings.api_key:
        return plan_with_api(text, settings.api_key, settings.model)
    return plan_with_cli(text, settings.model, settings.claude_cli)
