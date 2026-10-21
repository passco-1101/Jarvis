import json
import urllib.error
import urllib.request


def call(settings, method, path, payload=None):
    """Send one request to the local daemon and return the decoded JSON reply."""
    data = None
    if method == "POST":
        data = json.dumps(payload or {}).encode("utf-8")
    request = urllib.request.Request(
        f"http://127.0.0.1:{settings.port}{path}",
        data=data,
        method=method,
        headers={"X-Jarvis-Token": settings.token, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"Jarvis refused the request ({exc.code}): {exc.read().decode('utf-8', 'replace')}")
    except urllib.error.URLError as exc:
        raise SystemExit(f"Jarvis is not reachable on port {settings.port} ({exc.reason}). Is it running?")
