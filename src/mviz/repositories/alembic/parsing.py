"""Alembic migration file parsing functions."""

from pathlib import Path
from typing import Optional

from mviz.domain.exceptions import FileParseError
from mviz.domain.models import MigrationMetadata, MigrationNode
from mviz.repositories.alembic.cst_utils import (
    extract_assignments,
    extract_docstring,
    parse_docstring_metadata,
)


def parse_migration_file(file_path: str) -> Optional[MigrationNode]:
    """Parse a single Alembic migration file into a MigrationNode.

    Args:
        file_path: Path to the migration Python file.

    Returns:
        MigrationNode if valid migration, None otherwise.

    Raises:
        FileParseError: If file cannot be parsed.
    """
    import libcst as cst

    try:
        source = Path(file_path).read_text(encoding="utf-8")
        module = cst.parse_module(source)

        # Extract revision assignments using CST utilities
        assignments = extract_assignments(
            module, ["revision", "down_revision", "branch_labels", "depends_on"]
        )
        revision = assignments.get("revision")

        if not revision:
            return None  # Not a valid migration file

        # Extract metadata using CST utilities
        docstring = extract_docstring(module)
        description, timestamp = parse_docstring_metadata(docstring)

        return MigrationNode(
            revision=revision,
            down_revision=assignments.get("down_revision"),
            branch_labels=assignments.get("branch_labels"),
            depends_on=assignments.get("depends_on"),
            path=Path(file_path).name,
            timestamp=timestamp,
            metadata=MigrationMetadata(description=description),
        )
    except Exception as exc:
        raise FileParseError(file_path, str(exc))
