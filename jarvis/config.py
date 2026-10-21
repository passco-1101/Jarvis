import os
import secrets
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / ".env"
LOG_DIR = ROOT / "logs"

KEYS = ("JARVIS_PORT", "JARVIS_TOKEN", "JARVIS_MODEL", "JARVIS_CLAUDE_CLI", "ANTHROPIC_API_KEY")


@dataclass
class Settings:
    port: int
    token: str
    api_key: str
    model: str
    claude_cli: str = "claude"


def _read_env_file():
    values = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            values[key.strip()] = value.strip().strip("\"'")
    return values


def load(create_token=False):
    """Read settings from .env and the environment. Only the daemon may create the token."""
    values = _read_env_file()
    for key in KEYS:
        if os.environ.get(key):
            values[key] = os.environ[key]

    token = values.get("JARVIS_TOKEN", "")
    if not token:
        if not create_token:
            raise SystemExit("No JARVIS_TOKEN found. Start Jarvis once with: python -m jarvis serve")
        token = secrets.token_urlsafe(32)
        with ENV_FILE.open("a", encoding="utf-8") as f:
            f.write(f"\nJARVIS_TOKEN={token}\n")

    return Settings(
        port=int(values.get("JARVIS_PORT", 8765)),
        token=token,
        api_key=values.get("ANTHROPIC_API_KEY", ""),
        model=values.get("JARVIS_MODEL", "claude-sonnet-5-5"),
        claude_cli=values.get("JARVIS_CLAUDE_CLI", "claude"),
    )
