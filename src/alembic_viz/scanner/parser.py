"""Parser for Alembic migration files using libcst."""

import hashlib
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import libcst as cst
from alembic_viz.models import (
    GraphState,
    MigrationMetadata,
    MigrationNode,
    ValidationError,
)
from libcst import AnnAssign, Assign, Module, Name, SimpleString
from libcst import List as ListNode
from libcst import Tuple as TupleNode


class RevisionExtractor(cst.CSTVisitor):
    """Extract revision identifiers from an Alembic migration file."""

    def __init__(self):
        super().__init__()
        self.revision: Optional[str] = None
        self.down_revision: Optional[Union[str, List[str]]] = None
        self.branch_labels: Optional[Union[str, List[str]]] = None
        self.depends_on: Optional[Union[str, List[str]]] = None
        self.assignments: Dict[str, Any] = {}

    def visit_Assign(self, node: Assign) -> None:
        """Visit regular assignment statements to find revision variables."""
        # Get the target name
        if isinstance(node.targets[0].target, Name):
            target_name = node.targets[0].target.value
            value = self._extract_value(node.value)

            if target_name in [
                "revision",
                "down_revision",
                "branch_labels",
                "depends_on",
            ]:
                self.assignments[target_name] = value

    def visit_AnnAssign(self, node: AnnAssign) -> None:
        """Visit annotated assignment statements (e.g., revision: str = \"abc123\")."""
        # Get the target name
        if isinstance(node.target, Name):
            target_name = node.target.value
            value = self._extract_value(node.value)

            if target_name in [
                "revision",
                "down_revision",
                "branch_labels",
                "depends_on",
            ]:
                self.assignments[target_name] = value

    def _extract_value(self, node) -> Any:
        """Extract a Python value from a CST node."""
        if isinstance(node, SimpleString):
            return node.evaluated_value

        elif isinstance(node, (TupleNode, ListNode)):
            elements = []
            for element in node.elements:
                val = self._extract_value(element.value)
                if val is not None:
                    elements.append(val)
            return elements if elements else None

        elif isinstance(node, Name):
            # Handle None
            if node.value == "None":
                return None
            return node.value

        return None

    def finalize(self) -> None:
        """Finalize extraction after traversal."""
        self.revision = self.assignments.get("revision")
        self.down_revision = self.assignments.get("down_revision")
        self.branch_labels = self.assignments.get("branch_labels")
        self.depends_on = self.assignments.get("depends_on")


def extract_docstring(module: Module) -> Optional[str]:
    """Extract the module docstring."""
    if module.body and isinstance(module.body[0], cst.SimpleStatementLine):
        first_stmt = module.body[0].body[0]
        if isinstance(first_stmt, cst.Expr) and isinstance(
            first_stmt.value, SimpleString
        ):
            return first_stmt.value.evaluated_value
    return None


def parse_docstring_metadata(
    docstring: Optional[str],
) -> Tuple[Optional[str], Optional[datetime]]:
    """Extract description and timestamp from Alembic docstring.

    Alembic docstrings typically have format with description,
    Revision ID, Revises, and Create Date fields.

    Returns:
        Tuple of (description, timestamp)
    """
    if not docstring:
        return None, None

    # Extract description (first line or before Revision ID)
    lines = docstring.strip().split("\n")
    description = lines[0].strip() if lines else None

    # Extract timestamp from Create Date line
    timestamp = None
    for line in lines:
        match = re.search(
            r"Create Date:\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d+)", line
        )
        if match:
            try:
                timestamp = datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S.%f")
            except ValueError:
                pass
            break

    return description, timestamp


def calculate_content_hash(file_path: str) -> str:
    """Calculate MD5 hash of file contents."""
    with open(file_path, "rb") as f:
        content = f.read()
    return f"md5:{hashlib.md5(content).hexdigest()}"


def find_assignment_line_number(module: Module, target_name: str) -> int:
    """Find the line number of an assignment statement."""
    for i, stmt in enumerate(module.body, start=1):
        if isinstance(stmt, cst.SimpleStatementLine):
            for node in stmt.body:
                if isinstance(node, cst.Assign):
                    if isinstance(node.targets[0].target, Name):
                        if node.targets[0].target.value == target_name:
                            return (
                                stmt.line_number if hasattr(stmt, "line_number") else i
                            )
    return 1


def parse_migration_file(file_path: str) -> Optional[MigrationNode]:
    """Parse a single Alembic migration file.

    Args:
        file_path: Path to the migration Python file.

    Returns:
        MigrationNode if parsing succeeds, None if not a valid migration.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()

        # Parse with libcst
        module = cst.parse_module(source)

        # Extract revision info
        extractor = RevisionExtractor()
        module.visit(extractor)
        extractor.finalize()

        # Must have a revision to be a valid migration
        if not extractor.revision:
            return None

        # Extract metadata
        docstring = extract_docstring(module)
        description, timestamp = parse_docstring_metadata(docstring)

        # Calculate content hash
        content_hash = calculate_content_hash(file_path)

        # Find line number of revision assignment
        line_number = find_assignment_line_number(module, "revision")

        # Build metadata
        metadata = MigrationMetadata(
            description=description,
        )

        return MigrationNode(
            revision=extractor.revision,
            down_revision=extractor.down_revision,
            branch_labels=extractor.branch_labels,
            depends_on=extractor.depends_on,
            path=os.path.basename(file_path),
            content_hash=content_hash,
            line_number=line_number,
            timestamp=timestamp,
            metadata=metadata,
        )

    except Exception:
        # Failed to parse - not a valid migration file
        return None


def scan_directory(directory: str) -> GraphState:
    """Scan a directory for Alembic migration files.

    Args:
        directory: Path to the versions directory.

    Returns:
        GraphState containing all parsed migrations.
    """
    migrations: List[MigrationNode] = []
    validation_errors: List[ValidationError] = []

    dir_path = Path(directory)

    if not dir_path.exists():
        validation_errors.append(
            ValidationError(
                type="io_error",
                message=f"Directory not found: {directory}",
            )
        )
        return GraphState(
            source_directory=directory,
            migrations=[],
            validation_errors=validation_errors,
        )

    # Find all Python files
    py_files = sorted(dir_path.glob("*.py"))

    for file_path in py_files:
        try:
            node = parse_migration_file(str(file_path))
            if node:
                migrations.append(node)
        except Exception as e:
            validation_errors.append(
                ValidationError(
                    type="parse_error",
                    message=f"Failed to parse {file_path.name}: {str(e)}",
                    details={"file": file_path.name},
                )
            )

    return GraphState(
        source_directory=str(dir_path.resolve()),
        migrations=migrations,
        validation_errors=validation_errors,
    )
