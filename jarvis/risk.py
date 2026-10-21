import re

# A command matching any of these needs your approval before it runs. This is a safety net that
# catches mistakes, not a sandbox: anything not listed runs straight away.
DANGEROUS = [re.compile(p, re.IGNORECASE) for p in (
    r"\bRemove-Item\b",
    r"\b(del|erase|rd|rmdir|rm)\b",
    r"(?<![-\w.])format(\.com)?(?=\s+[A-Za-z]:)",
    r"\bdiskpart\b",
    r"\bcipher\b",
    r"\bbcdedit\b",
    r"\bshutdown\b",
    r"\b(Restart|Stop)-Computer\b",
    r"\breg(\.exe)?\s+(delete|add|import)\b",
    r"\bSet-ExecutionPolicy\b",
    r"\b(Stop-Process|taskkill)\b",
    r"\bgit\s+(push|reset|clean|checkout\s+--)\b",
    r"\bnet\s+(user|localgroup)\b",
    r"\b(Invoke-Expression|iex)\b",
    r"\b(Set-Content|Add-Content|Clear-Content|Out-File|Move-Item|Rename-Item)\b",
    r"\b(Register|Set|Unregister)-ScheduledTask\b|\bschtasks\b",
    r"\bStart-Process\b.*\b-Verb\s+RunAs\b",
)]


def needs_approval(command):
    """Return the text that made the command risky, or None if it can run straight away."""
    for pattern in DANGEROUS:
        match = pattern.search(command)
        if match:
            return f"matched '{match.group(0)}'"
    return None
