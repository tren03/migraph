"""Rewrite Alembic migration files from a target graph state."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

import libcst as cst
from alembic_viz_contracts.models import GraphState, MigrationNode
from alembic_viz_graph_ops import validate
from alembic_viz_scanner import scan_directory


class WriterError(Exception):
    """Base writer error."""


class ValidationFailure(WriterError):
    """Raised when the target graph is invalid."""


class ConflictFailure(WriterError):
    """Raised when the target graph no longer matches the filesystem."""


@dataclass(frozen=True)
class FileChange:
    revision: str
    path: str
    old_down_revision: Optional[Union[str, List[str]]]
    new_down_revision: Optional[Union[str, List[str]]]
    applied: bool


def _normalize_parent_value(value: Optional[Union[str, Sequence[str]]]) -> Optional[Union[str, List[str]]]:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return list(value)


def _same_parent_value(left: Optional[Union[str, List[str]]], right: Optional[Union[str, List[str]]]) -> bool:
    return _normalize_parent_value(left) == _normalize_parent_value(right)


def _to_cst_value(value: Optional[Union[str, List[str]]]) -> cst.BaseExpression:
    if value is None:
        return cst.Name("None")
    if isinstance(value, str):
        return cst.SimpleString(repr(value))

    return cst.List(
        [cst.Element(cst.SimpleString(repr(item))) for item in value],
    )


class DownRevisionRewriter(cst.CSTTransformer):
    """Rewrite the down_revision assignment value only."""

    def __init__(self, value: Optional[Union[str, List[str]]]):
        self.value = value
        self.updated = False

    def leave_Assign(self, original_node: cst.Assign, updated_node: cst.Assign) -> cst.Assign:
        if isinstance(original_node.targets[0].target, cst.Name) and original_node.targets[0].target.value == "down_revision":
            self.updated = True
            return updated_node.with_changes(value=_to_cst_value(self.value))
        return updated_node

    def leave_AnnAssign(self, original_node: cst.AnnAssign, updated_node: cst.AnnAssign) -> cst.AnnAssign:
        if isinstance(original_node.target, cst.Name) and original_node.target.value == "down_revision":
            self.updated = True
            return updated_node.with_changes(value=_to_cst_value(self.value))
        return updated_node


def _rewrite_file(file_path: Path, value: Optional[Union[str, List[str]]]) -> None:
    source = file_path.read_text(encoding="utf-8")
    module = cst.parse_module(source)
    transformer = DownRevisionRewriter(value)
    rewritten = module.visit(transformer)
    if not transformer.updated:
        raise WriterError(f"No down_revision assignment found in {file_path.name}")
    file_path.write_text(rewritten.code, encoding="utf-8")


def apply_graph_state(graph: GraphState, directory: str, dry_run: bool = False) -> Dict[str, Any]:
    """Apply graph parent changes back to Alembic migration files."""
    validation_errors = validate(graph)
    if validation_errors:
        raise ValidationFailure(validation_errors[0].message)

    current_graph = scan_directory(directory)
    current_by_revision = {migration.revision: migration for migration in current_graph.migrations}
    target_by_revision = {migration.revision: migration for migration in graph.migrations}

    missing = sorted(target_by_revision.keys() - current_by_revision.keys())
    if missing:
        raise ConflictFailure(f"Target graph references migrations missing from filesystem: {', '.join(missing)}")

    changes: List[FileChange] = []
    for revision, target_node in sorted(target_by_revision.items()):
        current_node = current_by_revision[revision]

        if current_node.content_hash != target_node.content_hash:
            raise ConflictFailure(
                f"Migration {revision} changed on disk since scan; expected {target_node.content_hash}, found {current_node.content_hash}."
            )

        if _same_parent_value(current_node.down_revision, target_node.down_revision):
            continue

        file_path = Path(directory) / current_node.path
        if not dry_run:
            _rewrite_file(file_path, _normalize_parent_value(target_node.down_revision))

        changes.append(
            FileChange(
                revision=revision,
                path=str(file_path),
                old_down_revision=_normalize_parent_value(current_node.down_revision),
                new_down_revision=_normalize_parent_value(target_node.down_revision),
                applied=not dry_run,
            )
        )

    return {
        "status": "success",
        "operation": "apply",
        "data": {
            "directory": str(Path(directory).resolve()),
            "dry_run": dry_run,
            "changes": [change.__dict__ for change in changes],
            "changed_files_count": len(changes),
        },
        "warnings": [],
    }
