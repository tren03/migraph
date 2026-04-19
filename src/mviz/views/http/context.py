"""Context object for HTTP handler state management."""

from dataclasses import dataclass, field
from typing import Optional

from mviz.domain.models import GraphState
from mviz.services.writer_service import WriterService


@dataclass
class HandlerContext:
    """Mutable context shared across handler operations.

    This context holds the state needed by API endpoint handlers,
    allowing business logic to be separated from HTTP protocol handling.
    """

    current_graph: GraphState
    writer_service: WriterService
    output_path: Optional[str]
    apply_directory: Optional[str]
    scan_config_path: Optional[str] = None
    scan_provider: Optional[str] = None
    html: bytes = field(default=b"")
    js: bytes = field(default=b"")
