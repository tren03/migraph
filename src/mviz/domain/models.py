"""Domain entities and value objects."""

from datetime import datetime
from typing import Any, Dict, Optional, Union

from pydantic import BaseModel, Field


class Position(BaseModel):
    """UI position for a node."""

    x: float = 0.0
    y: float = 0.0


class UIState(BaseModel):
    """UI state for the viewer."""

    positions: Dict[str, Position] = Field(default_factory=dict)
    pinned: list[str] = Field(default_factory=list)
    zoom: float = 1.0
    pan: Dict[str, float] = Field(default_factory=lambda: {"x": 0.0, "y": 0.0})
    selected: list[str] = Field(default_factory=list)


class MigrationMetadata(BaseModel):
    """Optional metadata extracted from migration files."""

    description: Optional[str] = None
    upgrade_preview: Optional[str] = None
    downgrade_preview: Optional[str] = None


class MigrationNode(BaseModel):
    """A single migration in the graph."""

    revision: str
    down_revision: Union[str, list[str], None] = None
    branch_labels: Union[str, list[str], None] = None
    depends_on: Union[str, list[str], None] = None
    path: str
    timestamp: Optional[datetime] = None
    metadata: MigrationMetadata = Field(default_factory=MigrationMetadata)


class ValidationError(BaseModel):
    """A validation error in the graph."""

    type: str  # cycle, orphan, etc.
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)


class GraphState(BaseModel):
    """The canonical representation of a migration graph."""

    source_directory: str
    migrations: list[MigrationNode] = Field(default_factory=list)
    validation_errors: list[ValidationError] = Field(default_factory=list)
    ui_state: UIState = Field(default_factory=UIState)


class SuccessResult(BaseModel):
    """Success result envelope."""

    status: str = "success"
    operation: str
    data: Dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class ErrorResult(BaseModel):
    """Error result envelope."""

    status: str = "error"
    error_type: str  # parse_error, validation_error, conflict_error, etc.
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)
    suggestion: Optional[str] = None


ResultEnvelope = Union[SuccessResult, ErrorResult]
