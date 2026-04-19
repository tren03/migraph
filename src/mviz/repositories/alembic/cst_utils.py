"""CST (LibCST) utility functions for parsing Python migration files."""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import libcst as cst
from libcst import AnnAssign, Assign, Module, Name, SimpleString
from libcst import List as ListNode
from libcst import Tuple as TupleNode


class _AssignmentExtractor(cst.CSTVisitor):
    """CST visitor that extracts assignments for specific target variable names.

    This is a private implementation class used by extract_assignments().
    """

    def __init__(self, targets: List[str]) -> None:
        self.targets = targets
        self.assignments: Dict[str, Any] = {}

    def visit_Assign(self, node: Assign) -> None:
        if isinstance(node.targets[0].target, Name):
            target_name = node.targets[0].target.value
            if target_name in self.targets:
                self.assignments[target_name] = _extract_cst_value(node.value)

    def visit_AnnAssign(self, node: AnnAssign) -> None:
        if isinstance(node.target, Name):
            target_name = node.target.value
            if target_name in self.targets:
                self.assignments[target_name] = _extract_cst_value(node.value)


def _extract_cst_value(node: cst.CSTNode) -> Any:
    """Extract a Python value from a CST node.

    Handles SimpleString (returns string), List/Tuple (returns list),
    and Name (handles None).
    """
    if isinstance(node, SimpleString):
        return node.evaluated_value
    elif isinstance(node, (TupleNode, ListNode)):
        elements = []
        for element in node.elements:
            val = _extract_cst_value(element.value)
            if val is not None:
                elements.append(val)
        return elements if elements else None
    elif isinstance(node, Name):
        if node.value == "None":
            return None
        return node.value
    return None


def extract_assignments(module: Module, targets: List[str]) -> Dict[str, Any]:
    """Extract assignment values for specific target names from a CST module.

    Args:
        module: The CST module to extract from.
        targets: List of variable names to extract (e.g., ["revision", "down_revision"]).

    Returns:
        Dictionary mapping target names to their extracted values.
    """
    extractor = _AssignmentExtractor(targets)
    module.visit(extractor)
    return extractor.assignments


def extract_docstring(module: Module) -> Optional[str]:
    """Extract the module-level docstring from a CST module."""
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
    """Extract description and timestamp from Alembic docstring format.

    Alembic docstrings typically contain:
    - First line: description
    - Create Date line: timestamp

    Returns:
        Tuple of (description, timestamp).
    """
    if not docstring:
        return None, None

    lines = docstring.strip().split("\n")
    description = lines[0].strip() if lines else None
    timestamp = None

    for line in lines:
        match = re.search(
            r"Create Date:\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d+)",
            line,
        )
        if match:
            try:
                timestamp = datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S.%f")
            except ValueError:
                pass
            break

    return description, timestamp
