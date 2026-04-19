"""CLI utility functions for migraph."""

import json
import sys
from typing import Any, Optional

import typer

from migraph.domain.models import ErrorResult


def format_json(data: Any) -> str:
    """Format data as JSON string."""
    return json.dumps(data, indent=2, default=str)


def error_and_exit(
    error_type: str, message: str, suggestion: Optional[str] = None, exit_code: int = 1
) -> None:
    """Print error JSON to stderr and exit."""
    error = ErrorResult(error_type=error_type, message=message, suggestion=suggestion)
    print(format_json(error.model_dump()), file=sys.stderr)
    raise typer.Exit(exit_code)
