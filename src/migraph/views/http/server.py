"""HTTP server for the browser viewer."""

import threading
import webbrowser
from http.server import ThreadingHTTPServer
from typing import Optional

from migraph.domain.models import GraphState
from migraph.services.writer_service import WriterService
from migraph.views.http.context import HandlerContext
from migraph.views.http.handler import ViewerHandler
from migraph.views.http.state import load_template


def serve_graph(
    graph: GraphState,
    host: str = "127.0.0.1",
    port: int = 0,
    open_browser: bool = True,
    output_path: Optional[str] = None,
    apply_directory: Optional[str] = None,
    scan_config_path: Optional[str] = None,
    scan_provider: Optional[str] = None,
) -> str:
    """Serve a graph locally until interrupted.

    Args:
        graph: The migration graph to serve.
        host: Host interface to bind to.
        port: Port to use. Uses a random port if 0.
        open_browser: Whether to open the browser automatically.
        output_path: Optional path to save exported graph JSON.
        apply_directory: Optional directory to apply changes to.

    Returns:
        The URL the server is running on.
    """
    # Create handler context with all state
    ViewerHandler.context = HandlerContext(
        current_graph=graph.model_copy(deep=True),
        writer_service=WriterService(),
        output_path=output_path,
        apply_directory=apply_directory,
        scan_config_path=scan_config_path,
        scan_provider=scan_provider,
        html=load_template("index.html"),
        js=load_template("app.js"),
    )

    # Create and start server
    httpd = ThreadingHTTPServer((host, port), ViewerHandler)
    url = f"http://{host}:{httpd.server_address[1]}"

    if open_browser:
        threading.Timer(0.2, lambda: webbrowser.open(url)).start()

    try:
        print(f"Viewer running at {url}")
        print("Press Ctrl+C to stop the server.")
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()

    return url
