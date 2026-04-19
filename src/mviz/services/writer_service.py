"""Writer service - use case for applying graph changes to any provider."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import libcst as cst

from mviz.domain.exceptions import (
    ConflictError,
    ValidationError as DomainValidationError,
)
from mviz.domain.models import GraphState
from mviz.repositories.interfaces import MigrationRepository
from mviz.repositories.provider_factory import get_repository
from mviz.services.graph_service import GraphService


@dataclass(frozen=True)
class FileChange:
    """Represents a change to a migration file."""

    revision: str
    path: str
    old_down_revision: Optional[Union[str, List[str]]]
    new_down_revision: Optional[Union[str, List[str]]]
    applied: bool


class _DownRevisionRewriter(cst.CSTTransformer):
    """Rewrite the down_revision assignment value (Alembic-specific)."""

    def __init__(self, value: Optional[Union[str, List[str]]]):
        self.value = value
        self.updated = False

    def _to_cst_value(
        self, value: Optional[Union[str, List[str]]]
    ) -> cst.BaseExpression:
        if value is None:
            return cst.Name("None")
        if isinstance(value, str):
            return cst.SimpleString(repr(value))
        return cst.List([cst.Element(cst.SimpleString(repr(item))) for item in value])

    def leave_Assign(
        self, original_node: cst.Assign, updated_node: cst.Assign
    ) -> cst.Assign:
        if (
            isinstance(original_node.targets[0].target, cst.Name)
            and original_node.targets[0].target.value == "down_revision"
        ):
            self.updated = True
            return updated_node.with_changes(value=self._to_cst_value(self.value))
        return updated_node

    def leave_AnnAssign(
        self, original_node: cst.AnnAssign, updated_node: cst.AnnAssign
    ) -> cst.AnnAssign:
        if (
            isinstance(original_node.target, cst.Name)
            and original_node.target.value == "down_revision"
        ):
            self.updated = True
            return updated_node.with_changes(value=self._to_cst_value(self.value))
        return updated_node


class WriterService:
    """Service for applying graph changes back to migration files."""

    def __init__(
        self,
        repo: MigrationRepository | None = None,
        graph_service: GraphService | None = None,
    ) -> None:
        self._repo = repo
        self._graph_service = graph_service or GraphService()

    def apply_graph(
        self,
        graph: GraphState,
        directory: str,
        dry_run: bool = False,
        provider: str | None = None,
    ) -> Dict[str, Any]:
        """Apply graph changes back to migration files.

        Args:
            graph: Target graph state.
            directory: Directory containing migration files.
            dry_run: If True, don't actually write changes.
            provider: Provider name. Auto-detected if not specified.

        Returns:
            Result dictionary with change details.

        Raises:
            DomainValidationError: If the graph is invalid.
            ConflictError: If the graph conflicts with filesystem.
        """
        # Get repository if not provided
        if self._repo is None:
            self._repo = get_repository(provider)

        # Validate the graph
        validation_errors = self._graph_service.validate(graph)
        if validation_errors:
            raise DomainValidationError(validation_errors[0].message)

        # Scan current state
        current_graph = self._repo.scan_migrations(directory)
        current_by_revision = {
            migration.revision: migration for migration in current_graph.migrations
        }
        target_by_revision = {
            migration.revision: migration for migration in graph.migrations
        }

        # Check for missing migrations
        missing = sorted(target_by_revision.keys() - current_by_revision.keys())
        if missing:
            raise ConflictError(
                f"Target graph references migrations missing from filesystem: {', '.join(missing)}"
            )

        # Calculate and apply changes
        changes: List[FileChange] = []
        for revision, target_node in sorted(target_by_revision.items()):
            current_node = current_by_revision[revision]

            # Skip if no change needed
            if self._same_parent_value(
                current_node.down_revision, target_node.down_revision
            ):
                continue

            # Apply the change
            file_path = Path(directory) / current_node.path
            if not dry_run:
                self._rewrite_file(
                    file_path, self._normalize_value(target_node.down_revision)
                )

            changes.append(
                FileChange(
                    revision=revision,
                    path=str(file_path),
                    old_down_revision=self._normalize_value(current_node.down_revision),
                    new_down_revision=self._normalize_value(target_node.down_revision),
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

    def _normalize_value(
        self, value: Optional[Union[str, List[str]]]
    ) -> Optional[Union[str, List[str]]]:
        if value is None:
            return None
        if isinstance(value, str):
            return value
        return list(value)

    def _same_parent_value(
        self,
        left: Optional[Union[str, List[str]]],
        right: Optional[Union[str, List[str]]],
    ) -> bool:
        return self._normalize_value(left) == self._normalize_value(right)

    def _rewrite_file(
        self, file_path: Path, value: Optional[Union[str, List[str]]]
    ) -> None:
        """Rewrite a migration file with new parent value.

        Note: This is currently Alembic-specific (down_revision variable).
        For other providers, this method would be overridden or use a
        provider-specific rewriting strategy.
        """
        source = file_path.read_text(encoding="utf-8")
        module = cst.parse_module(source)
        transformer = _DownRevisionRewriter(value)
        rewritten = module.visit(transformer)
        if not transformer.updated:
            raise RuntimeError(f"No down_revision assignment found in {file_path.name}")
        file_path.write_text(rewritten.code, encoding="utf-8")
