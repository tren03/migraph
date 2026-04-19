"""Alembic repository implementation - thin orchestrator."""

from pathlib import Path
from typing import List

from migraph.domain.models import GraphState, MigrationNode, ValidationError
from migraph.repositories.alembic.config import (
    find_alembic_ini,
    resolve_migrations_root,
)
from migraph.repositories.alembic.parsing import parse_migration_file
from migraph.repositories.interfaces import MigrationRepository


class AlembicRepository(MigrationRepository):
    """Alembic-specific migration repository.

    This class is a thin orchestrator that delegates to the module-level
    functions in config.py and parsing.py. It implements the
    MigrationRepository protocol.
    """

    PROVIDER_NAME = "alembic"
    CONFIG_FILENAME = "alembic.ini"

    def find_migrations_root(self, config_path: str | None = None) -> str:
        """Find the Alembic migrations directory."""
        return resolve_migrations_root(config_path)

    def scan_migrations(self, directory: str) -> GraphState:
        """Scan a directory for Alembic migration files."""
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

    def read_migration(self, directory: str, path: str) -> str:
        """Read a migration file's content."""
        file_path = Path(directory) / path
        return file_path.read_text(encoding="utf-8")

    def write_migration(
        self,
        directory: str,
        path: str,
        content: str,
        dry_run: bool = False,
    ) -> None:
        """Write content to a migration file."""
        if dry_run:
            return
        file_path = Path(directory) / path
        file_path.write_text(content, encoding="utf-8")

    @classmethod
    def detect(cls, start_path: str | None = None) -> bool:
        """Detect if Alembic is present in the given path."""
        return find_alembic_ini(start_path) is not None
