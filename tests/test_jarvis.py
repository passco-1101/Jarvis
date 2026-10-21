import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jarvis import risk  # noqa: E402
from jarvis.config import Settings  # noqa: E402
from jarvis.server import Jarvis, make_handler  # noqa: E402


def fake_run(command, timeout=120):
    return 0, f"ran: {command}"


def fake_plan(text, api_key, model, timeout=60):
    return {"command": "Get-Date", "answer": "here is the date"}


class RiskTests(unittest.TestCase):
    def test_safe_commands_run_directly(self):
        for command in ("Get-Date", "Get-ChildItem C:\\Users\\Acer", "Get-Process | Select-Object -First 5",
                        "Get-Date -Format yyyy-MM-dd"):
            self.assertIsNone(risk.needs_approval(command), command)

    def test_destructive_commands_need_approval(self):
        for command in ("Remove-Item C:\\x -Recurse", "del C:\\x.txt", "shutdown /r", "git push --force",
                        "Set-Content C:\\a.txt hi", "taskkill /im app.exe", "iex (irm http://x)",
                        "format D: /q"):
            self.assertIsNotNone(risk.needs_approval(command), command)


class JarvisTests(unittest.TestCase):
    def setUp(self):
        self.app = Jarvis(Settings(port=0, token="t", api_key="", model="m"), run=fake_run, plan=fake_plan)

    def test_raw_safe_command_runs(self):
        result = self.app.handle_text("!Get-Date")
        self.assertEqual(result["status"], "done")
        self.assertEqual(result["output"], "ran: Get-Date")

    def test_risky_command_waits_then_approves(self):
        result = self.app.handle_text("!del C:\\x.txt")
        self.assertEqual(result["status"], "pending")
        self.assertEqual(self.app.list_pending()[0]["id"], result["id"])
        self.assertEqual(self.app.approve(result["id"])["status"], "done")
        self.assertEqual(self.app.list_pending(), [])

    def test_deny_discards(self):
        result = self.app.handle_text("!del C:\\x.txt")
        self.app.deny(result["id"])
        self.assertEqual(self.app.approve(result["id"])["status"], "error")

    def test_plain_language_needs_api_key(self):
        self.assertEqual(self.app.handle_text("what time is it")["status"], "error")

    def test_plain_language_uses_planner(self):
        self.app.settings.api_key = "k"
        result = self.app.handle_text("what time is it")
        self.assertEqual(result["output"], "ran: Get-Date")
        self.assertEqual(result["answer"], "here is the date")


class HttpTests(unittest.TestCase):
    def setUp(self):
        self.settings = Settings(port=0, token="secret", api_key="", model="m")
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(Jarvis(self.settings, run=fake_run)))
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def request(self, method, path, body=None, token="secret"):
        headers = {"X-Jarvis-Token": token, "Content-Type": "application/json"}
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.base + path, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status, json.load(resp)
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read() or b"{}")

    def test_wrong_token_is_rejected(self):
        self.assertEqual(self.request("GET", "/status", token="nope")[0], 401)

    def test_status_with_token(self):
        self.assertEqual(self.request("GET", "/status"), (200, {"status": "running"}))

    def test_command_round_trip(self):
        code, body = self.request("POST", "/command", {"text": "!Get-Date"})
        self.assertEqual((code, body["status"]), (200, "done"))

    def test_bad_json_is_400(self):
        req = urllib.request.Request(self.base + "/command", data=b"{not json", method="POST",
                                     headers={"X-Jarvis-Token": "secret"})
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(req, timeout=10)
        self.assertEqual(ctx.exception.code, 400)


if __name__ == "__main__":
    unittest.main()
