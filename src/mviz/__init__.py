"""mviz - Alembic migration visualizer and reorganizer."""

__version__ = "0.1.0"

# Domain exports
from mviz.domain.models import (
    GraphState,
    MigrationNode,
    MigrationMetadata,
    Position,
    UIState,
    ValidationError,
)

# Service exports
from mviz.services.scanner_service import ScannerService

# View exports
from mviz.views.http import serve_graph

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
