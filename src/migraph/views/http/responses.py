"""HTTP response utility functions."""

import json
from http.server import BaseHTTPRequestHandler
from typing import Any


def write_json(
    handler: BaseHTTPRequestHandler, status_code: int, payload: dict
) -> None:
    """Write a JSON response to the handler.

    Args:
        handler: The HTTP request handler.
        status_code: HTTP status code to send.
        payload: Dictionary to serialize as JSON.
    """
    response = json.dumps(payload).encode("utf-8")
    handler.send_response(status_code)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(response)))
    handler.end_headers()
    handler.wfile.write(response)


def serve_static(
    handler: BaseHTTPRequestHandler, content: bytes, content_type: str
) -> None:
    """Serve static content through the handler.

    Args:
        handler: The HTTP request handler.
        content: Raw bytes to serve.
        content_type: MIME type of the content.
    """
    handler.send_response(200)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(content)))
    handler.end_headers()
    handler.wfile.write(content)
