"""Loopback-only HTTP adapter. All routes are read-only and use the CLI core."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
import json
from pathlib import Path
import sys
from urllib.parse import parse_qs, urlsplit
import webbrowser

from .core import Graph, GraphError, inspect_database

WEB_DIRECTORY = files("knowledge_graph").joinpath("web")
STATIC_FILES = {"/": ("index.html", "text/html; charset=utf-8"),
                "/i18n.js": ("i18n.js", "text/javascript; charset=utf-8"),
                "/app.js": ("app.js", "text/javascript; charset=utf-8"),
                "/style.css": ("style.css", "text/css; charset=utf-8")}


def make_server(database, port=8765, default_lang="en"):
    database = Path(database).resolve()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            # Request text is user-controlled. Keep logs compact and avoid terminal escapes.
            pass

        def send_bytes(self, status, body, content_type):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def send_json(self, status, value):
            self.send_bytes(status, json.dumps(value, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

        def do_GET(self):
            try:
                host = self.headers.get("Host", "")
                if host not in (f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"):
                    raise GraphError("INVALID_HOST", "Use the loopback URL printed by gui.")
                request = urlsplit(self.path)
                if request.path in STATIC_FILES:
                    filename, mime = STATIC_FILES[request.path]
                    self.send_bytes(200, WEB_DIRECTORY.joinpath(filename).read_bytes(), mime)
                    return
                query = parse_qs(request.query, keep_blank_values=True, max_num_fields=20)

                def parameter(name, default=None):
                    values = query.get(name, [default])
                    if len(values) != 1:
                        raise GraphError("INVALID_ARGUMENT", f"Specify {name} once.")
                    value = values[0]
                    if value is None or value == "":
                        raise GraphError("INVALID_ARGUMENT", f"Missing parameter: {name}.")
                    return value

                if request.path == "/api/validate":
                    report, _ = inspect_database(database)
                    self.send_json(200, {"success": True, "data": report})
                    return
                if request.path not in ("/api/graph", "/api/node", "/api/search", "/api/walk"):
                    self.send_json(404, GraphError("NOT_FOUND", "Unknown route.").response())
                    return
                graph = Graph.load(database, parameter("lang", default_lang))
                if request.path == "/api/graph":
                    data = graph.snapshot()
                elif request.path == "/api/node":
                    data = graph.node(parameter("id"))
                elif request.path == "/api/search":
                    data = graph.search(parameter("q"), int(parameter("limit", "20")))
                else:
                    data = graph.walk(parameter("id"), int(parameter("depth", "1")), int(parameter("max_nodes", "50")))
                self.send_json(200, {"success": True, "data": data})
            except GraphError as exc:
                status = 422 if exc.code == "INVALID_DATABASE" else 404 if exc.code == "UNKNOWN_NODE" else 400
                self.send_json(status, exc.response())
            except ValueError as exc:
                self.send_json(400, GraphError("INVALID_ARGUMENT", str(exc)).response())
            except OSError as exc:
                self.send_json(500, GraphError("IO_ERROR", str(exc)).response())

        do_HEAD = do_GET

        def reject_write(self):
            self.send_json(405, GraphError("READ_ONLY", "The viewer only supports reading. Edit database files directly.").response())

        do_POST = reject_write
        do_PUT = reject_write
        do_PATCH = reject_write
        do_DELETE = reject_write
        do_OPTIONS = reject_write

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    return server


def serve(database, port=8765, open_browser=True, lang="en"):
    if not 1 <= port <= 65535:
        raise GraphError("INVALID_ARGUMENT", "Port must be between 1 and 65535.")
    with make_server(database, port, lang) as server:
        url = f"http://127.0.0.1:{server.server_port}/" + ("?lang=ru" if lang == "ru" else "")
        print(f"Knowledge Graph: {url}\nDatabase: {Path(database).resolve()}\nCtrl+C to stop.", file=sys.stderr, flush=True)
        if open_browser:
            webbrowser.open(url)
        try:
            server.serve_forever(poll_interval=0.25)
        except KeyboardInterrupt:
            pass
