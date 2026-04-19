"""Local HTTP server for viewing migration graphs in a browser."""

import json
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional

from alembic_viz.models import GraphState
from alembic_viz.viewer.storage import apply_graph_to_repo, save_graph_state
from alembic_viz.viewer.utils import load_template
from alembic_viz.viewer.view_model import preview_graph_state
from alembic_viz.writer.rewriter import ConflictFailure, ValidationFailure, WriterError


def serve_graph(
    graph: GraphState,
    host: str = "127.0.0.1",
    port: int = 0,
    open_browser: bool = True,
    output_path: Optional[str] = None,
    apply_directory: Optional[str] = None,
) -> str:
    """Serve a graph locally until interrupted."""
    # Load static assets
    html = load_template("index.html")
    js = load_template("app.js")

    current_graph = graph.model_copy(deep=True)

    class ViewerHandler(BaseHTTPRequestHandler):
        def _write_json(self, status_code: int, payload: Dict[str, Any]) -> None:
            response = json.dumps(payload).encode("utf-8")
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response)))
            self.end_headers()
            self.wfile.write(response)

        def _serve_static(self, content: bytes, content_type: str) -> None:
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

        def do_GET(self) -> None:  # noqa: N802
            if self.path in {"/", "/index.html"}:
                self._serve_static(html, "text/html; charset=utf-8")
                return

            if self.path == "/static/app.js":
                self._serve_static(js, "application/javascript")
                return

            if self.path == "/api/graph":
                self._write_json(200, preview_graph_state(current_graph))
                return

            self.send_response(404)
            self.end_headers()

        def do_POST(self) -> None:  # noqa: N802
            nonlocal current_graph

            content_length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(content_length)

            try:
                proposed_graph = GraphState.model_validate_json(body)
            except Exception as exc:
                self._write_json(
                    400,
                    {
                        "status": "error",
                        "message": f"Invalid GraphState payload: {exc}",
                    },
                )
                return

            if self.path == "/api/preview":
                current_graph = proposed_graph
                self._write_json(200, preview_graph_state(current_graph))
                return

            if self.path == "/api/save":
                current_graph = proposed_graph
                saved_output = save_graph_state(current_graph, output_path)
                self._write_json(
                    200,
                    {
                        "status": "success",
                        "output_file": saved_output,
                        "migrations_count": len(current_graph.migrations),
                    },
                )
                return

            if self.path == "/api/apply":
                current_graph = proposed_graph
                try:
                    result = apply_graph_to_repo(current_graph, apply_directory)
                    self._write_json(200, result)
                except ValidationFailure as exc:
                    self._write_json(400, {"status": "error", "message": str(exc)})
                except ConflictFailure as exc:
                    self._write_json(409, {"status": "error", "message": str(exc)})
                except WriterError as exc:
                    self._write_json(500, {"status": "error", "message": str(exc)})
                return

            self.send_response(404)
            self.end_headers()

        def log_message(self, format: str, *args: Any) -> None:
            return

    server = ThreadingHTTPServer((host, port), ViewerHandler)
    url = f"http://{host}:{server.server_address[1]}"

    if open_browser:
        threading.Timer(0.2, lambda: webbrowser.open(url)).start()

    try:
        print(f"Viewer running at {url}")
        print("Press Ctrl+C to stop the server.")
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

    return url
