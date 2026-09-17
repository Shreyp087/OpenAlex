"""Small localhost-only API plus static demo assets; no network ingestion."""
import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from .engine import ROOT
from .scenarios import SCENARIO_IDS, build_demo, replay
from .evaluation import evaluate


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / "web"), **kwargs)

    def _json(self, status, data):
        payload = (json.dumps(data, ensure_ascii=False) + "\n").encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(payload)

    def _host_allowed(self):
        return self.headers.get("Host", "") in {
            "127.0.0.1:{}".format(self.server.server_port),
            "localhost:{}".format(self.server.server_port)
        }

    def _route(self):
        return urlsplit(self.path).path

    def do_GET(self):
        if not self._host_allowed():
            return self._json(403, {"error": "This service accepts localhost requests only."})
        route = self._route()
        if route == "/api/scenarios":
            data = build_demo()
            return self._json(200, {"meta": data["meta"], "scenarios": data["scenarios"]})
        if route == "/api/evaluation":
            return self._json(200, evaluate())
        if route == "/data/demo.json":
            return self._json(200, build_demo())
        permitted_files = {
            "/data/source/openalex-work.json": ROOT / "data/source/openalex-work.json",
            "/data/source/provenance.json": ROOT / "data/source/provenance.json"
        }
        if route in permitted_files:
            payload = permitted_files[route].read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        if route.startswith("/api/"):
            return self._json(404, {"error": "Unknown API route."})
        return super().do_GET()

    def do_POST(self):
        if not self._host_allowed():
            return self._json(403, {"error": "This service accepts localhost requests only."})
        if self._route() != "/api/replay":
            return self._json(404, {"error": "Unknown API route."})
        origin = self.headers.get("Origin")
        if origin and origin != "http://" + self.headers.get("Host", ""):
            return self._json(403, {"error": "Cross-origin replay requests are not accepted."})
        if self.headers.get("Content-Type", "").split(";", 1)[0].strip() != "application/json":
            return self._json(415, {"error": "Use application/json."})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 1 or length > 8192:
                raise ValueError("Replay requests must be between 1 and 8192 bytes.")
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict) or set(payload) != {"scenario"}:
                raise ValueError("Expected exactly one field: scenario.")
            key = payload["scenario"]
            if not isinstance(key, str) or key not in SCENARIO_IDS:
                raise ValueError("Unknown scenario. Only bundled fixtures can be replayed.")
            result = replay(key)
        except (ValueError, UnicodeError) as exc:
            return self._json(400, {"error": str(exc)})
        return self._json(200, result)

    def translate_path(self, path):
        candidate = Path(super().translate_path(path)).resolve()
        web_root = (ROOT / "web").resolve()
        if candidate != web_root and web_root not in candidate.parents:
            return str(web_root / "__not_found__")
        return str(candidate)

    def list_directory(self, path):
        self.send_error(404, "Directory listing is disabled")
        return None


def serve(port=8765):
    if not 0 <= port <= 65535:
        raise ValueError("port must be between 0 and 65535")
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print("The Repair Desk is running at http://127.0.0.1:{}/".format(server.server_port), flush=True)
    print("Pinned local fixtures only. Press Ctrl+C to stop.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
