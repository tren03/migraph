"""migraph - Alembic migration visualizer and reorganizer."""

__version__ = "0.1.0"

# Domain exports
from migraph.domain.models import (
    GraphState,
    MigrationNode,
    MigrationMetadata,
    Position,
    UIState,
    ValidationError,
)

# Service exports
from migraph.services.scanner_service import ScannerService

# View exports
from migraph.views.http import serve_graph

__all__ = [
    # Domain
    "GraphState",
    "MigrationNode",
    "MigrationMetadata",
    "Position",
    "UIState",
    "ValidationError",
    # Services
    "ScannerService",
    # Views
    "serve_graph",
    # Meta
    "__version__",
]
