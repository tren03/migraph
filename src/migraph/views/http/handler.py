"""HTTP request handler for the migration viewer."""

from http.server import BaseHTTPRequestHandler
from typing import Any

from migraph.domain.models import GraphState
from migraph.views.http.api import handle_apply, handle_preview, handle_save
from migraph.views.http.context import HandlerContext
from migraph.views.http.responses import serve_static, write_json


class ViewerHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the migration viewer.

    This handler serves the viewer UI and handles API requests.
    Business logic is delegated to functions in the api module.
    HTTP response utilities are in the responses module.
    """

    context: HandlerContext = None  # type: ignore[assignment]

    def do_GET(self) -> None:  # noqa: N802
        """Handle GET requests for static assets and API."""
        if self.path in {"/", "/index.html"}:
            serve_static(self, self.context.html, "text/html; charset=utf-8")
            return
        if self.path == "/static/app.js":
            serve_static(self, self.context.js, "application/javascript")
            return
        if self.path == "/api/graph":
            from migraph.views.view_model import preview_graph_state

            write_json(self, 200, preview_graph_state(self.context.current_graph))
            return
        if self.path == "/api/refresh":
            from migraph.services.scanner_service import ScannerService
            from migraph.views.view_model import preview_graph_state

            try:
                graph = ScannerService().scan(
                    config_path=self.context.scan_config_path,
                    provider=self.context.scan_provider,
                )
                self.context.current_graph = graph
                write_json(self, 200, preview_graph_state(self.context.current_graph))
            except Exception as exc:
                write_json(self, 500, {"status": "error", "message": str(exc)})
            return
        self.send_response(404)
        self.end_headers()

    def do_POST(self) -> None:  # noqa: N802
        """Handle POST requests for API endpoints."""
        content_length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_length)

        try:
            proposed_graph = GraphState.model_validate_json(body)
        except Exception as exc:
            write_json(
                self,
                400,
                {
                    "status": "error",
                    "message": f"Invalid GraphState payload: {exc}",
                },
            )
            return

        if self.path == "/api/preview":
            response = handle_preview(self.context, proposed_graph)
            write_json(self, 200, response)

        elif self.path == "/api/save":
            response = handle_save(self.context, proposed_graph)
            write_json(self, 200, response)

        elif self.path == "/api/apply":
            response = handle_apply(self.context, proposed_graph)
            # Determine status code based on response
            if response.get("status") == "success":
                write_json(self, 200, response)
            else:
                # Check if it's a validation error (400) or conflict (409)
                message = response.get("message", "")
                if "invalid" in message.lower() or "validation" in message.lower():
                    write_json(self, 400, response)
                elif (
                    "conflict" in message.lower()
                    or "changed on disk" in message.lower()
                ):
                    write_json(self, 409, response)
                else:
                    write_json(self, 500, response)

        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress default logging."""
        return
