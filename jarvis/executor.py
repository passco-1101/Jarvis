import subprocess

DEFAULT_TIMEOUT = 120
MAX_OUTPUT = 20_000


def run_powershell(command, timeout=DEFAULT_TIMEOUT):
    """Run one PowerShell command line. Returns (exit_code, output). Never opens a console window."""
    try:
        proc = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", command],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except subprocess.TimeoutExpired:
        return -1, f"timed out after {timeout}s"
    except OSError as exc:
        return -1, f"could not start PowerShell: {exc}"

    output = (proc.stdout + proc.stderr).strip()
    if len(output) > MAX_OUTPUT:
        output = output[:MAX_OUTPUT] + "\n... (output truncated)"
    return proc.returncode, output
