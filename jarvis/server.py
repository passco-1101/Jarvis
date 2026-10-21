import json
import logging
import secrets
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import executor, planner, risk

log = logging.getLogger("jarvis")

PENDING_TTL = 600  # seconds a risky command waits for approval
MAX_BODY = 64_000


class Jarvis:
    def __init__(self, settings, run=executor.run_powershell, plan=planner.plan_request):
        self.settings = settings
        self.run = run
        self.plan = plan
        self.pending = {}
        self.lock = threading.Lock()

    def handle_text(self, text):
        text = text.strip()
        if not text:
            return {"status": "error", "output": "empty request"}
        if text.startswith("!"):
            return self.submit(text[1:].strip())
        try:
            result = self.plan(text, self.settings)
        except Exception as exc:
            log.exception("planner failed")
            return {"status": "error", "output": f"planner failed: {exc}. Raw commands still work with a leading !"}
        if not result["command"]:
            return {"status": "done", "output": result["answer"]}
        response = self.submit(result["command"])
        if result["answer"]:
            response["answer"] = result["answer"]
        return response

    def submit(self, command):
        reason = risk.needs_approval(command)
        if reason is None:
            return self.execute(command)
        pending_id = uuid.uuid4().hex[:8]
        with self.lock:
            self.pending[pending_id] = {"command": command, "created": time.time(), "reason": reason}
        log.info("pending %s (%s): %s", pending_id, reason, command)
        return {"status": "pending", "id": pending_id, "command": command, "reason": reason}

    def execute(self, command):
        log.info("run: %s", command)
        code, output = self.run(command)
        if code != 0:
            log.warning("exit %s: %s", code, command)
        return {"status": "done" if code == 0 else "error", "exit_code": code, "command": command, "output": output}

    def approve(self, pending_id):
        with self.lock:
            item = self.pending.pop(pending_id, None)
        if item is None:
            return {"status": "error", "output": "no such pending command"}
        if time.time() - item["created"] > PENDING_TTL:
            return {"status": "error", "output": "that pending command expired"}
        log.info("approved %s", pending_id)
        return self.execute(item["command"])

    def deny(self, pending_id):
        with self.lock:
            item = self.pending.pop(pending_id, None)
        if item is None:
            return {"status": "error", "output": "no such pending command"}
        log.info("denied %s: %s", pending_id, item["command"])
        return {"status": "done", "output": "discarded"}

    def list_pending(self):
        now = time.time()
        with self.lock:
            for pending_id in [k for k, v in self.pending.items() if now - v["created"] > PENDING_TTL]:
                del self.pending[pending_id]
            return [{"id": k, "command": v["command"], "reason": v["reason"]} for k, v in self.pending.items()]


def make_handler(app):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, code, payload):
            body = json.dumps(payload).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _authorized(self):
            supplied = self.headers.get("X-Jarvis-Token", "")
            return secrets.compare_digest(supplied, app.settings.token)

        def _read_json(self):
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_BODY:
                raise ValueError("request too large")
            return json.loads(self.rfile.read(length) or b"{}")

        def do_GET(self):
            if not self._authorized():
                return self._send(401, {"error": "unauthorized"})
            if self.path == "/status":
                return self._send(200, {"status": "running"})
            if self.path == "/pending":
                return self._send(200, {"pending": app.list_pending()})
            self._send(404, {"error": "not found"})

        def do_POST(self):
            if not self._authorized():
                return self._send(401, {"error": "unauthorized"})
            try:
                body = self._read_json()
                if self.path == "/command":
                    return self._send(200, app.handle_text(str(body.get("text", ""))))
                action, _, pending_id = self.path.strip("/").partition("/")
                if action == "approve" and pending_id:
                    return self._send(200, app.approve(pending_id))
                if action == "deny" and pending_id:
                    return self._send(200, app.deny(pending_id))
                self._send(404, {"error": "not found"})
            except (ValueError, json.JSONDecodeError) as exc:
                self._send(400, {"error": f"bad request: {exc}"})
            except Exception:
                log.exception("request failed: %s", self.path)
                self._send(500, {"error": "internal error, see logs/jarvis.log"})

        def log_message(self, fmt, *args):
            log.debug("http %s", fmt % args)

    return Handler


def serve(settings):
    app = Jarvis(settings)
    server = ThreadingHTTPServer(("127.0.0.1", settings.port), make_handler(app))
    log.info("Jarvis listening on 127.0.0.1:%s", settings.port)
    server.serve_forever()
