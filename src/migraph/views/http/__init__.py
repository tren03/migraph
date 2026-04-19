"""HTTP server components for the migration viewer."""

from migraph.views.http.api import handle_apply, handle_preview, handle_save
from migraph.views.http.context import HandlerContext
from migraph.views.http.handler import ViewerHandler
from migraph.views.http.responses import serve_static, write_json
from migraph.views.http.server import serve_graph
from migraph.views.http.state import load_template, save_graph_state

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
