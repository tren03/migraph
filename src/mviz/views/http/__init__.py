"""HTTP server components for the migration viewer."""

from mviz.views.http.api import handle_apply, handle_preview, handle_save
from mviz.views.http.context import HandlerContext
from mviz.views.http.handler import ViewerHandler
from mviz.views.http.responses import serve_static, write_json
from mviz.views.http.server import serve_graph
from mviz.views.http.state import load_template, save_graph_state

__all__ = [
    # Server
    "serve_graph",
    # Handler
    "ViewerHandler",
    # Context
    "HandlerContext",
    # API functions
    "handle_preview",
    "handle_save",
    "handle_apply",
    # Response utilities
    "write_json",
    "serve_static",
    # State utilities
    "load_template",
    "save_graph_state",
]
