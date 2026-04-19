"""Pydantic models for the Data Contract."""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class Position(BaseModel):
    """UI position for a node."""

    x: float = 0.0
    y: float = 0.0


class UIState(BaseModel):
    """UI state for the viewer."""

    positions: Dict[str, Position] = Field(default_factory=dict)
    zoom: float = 1.0
    pan: Dict[str, float] = Field(default_factory=lambda: {"x": 0.0, "y": 0.0})
    selected: List[str] = Field(default_factory=list)


class MigrationMetadata(BaseModel):
    """Optional metadata extracted from migration files."""

    description: Optional[str] = None
    upgrade_preview: Optional[str] = None
    downgrade_preview: Optional[str] = None


class MigrationNode(BaseModel):
    """A single migration in the graph."""

    revision: str
    down_revision: Optional[Union[str, List[str]]] = None
    branch_labels: Optional[Union[str, List[str]]] = None
    depends_on: Optional[Union[str, List[str]]] = None
    path: str
    content_hash: str
    line_number: int = 1
    timestamp: Optional[datetime] = None
    metadata: MigrationMetadata = Field(default_factory=MigrationMetadata)


class ValidationError(BaseModel):
    """A validation error in the graph."""

    type: str  # cycle, orphan, etc.
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)


class GraphState(BaseModel):
    """The canonical representation of a migration graph."""

    schema_version: str = "1.0"
    source_directory: str
    migrations: List[MigrationNode] = Field(default_factory=list)
    validation_errors: List[ValidationError] = Field(default_factory=list)
    ui_state: UIState = Field(default_factory=UIState)


class SuccessResult(BaseModel):
    """Success result envelope."""

    status: str = "success"
    operation: str
    data: Dict[str, Any] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)


class ErrorResult(BaseModel):
    """Error result envelope."""

    status: str = "error"
    error_type: str  # parse_error, validation_error, conflict_error, etc.
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)
    suggestion: Optional[str] = None


ResultEnvelope = Union[SuccessResult, ErrorResult]
