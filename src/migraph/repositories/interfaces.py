"""Abstract repository interfaces for migration providers."""

from typing import List, Optional, Protocol

from migraph.domain.models import GraphState, MigrationNode


class MigrationRepository(Protocol):
    """Interface for migration data access - provider agnostic."""

    def find_migrations_root(self, config_path: str | None = None) -> str:
        """Find the migrations directory.

        Args:
            config_path: Path to provider-specific config file.
                If None, will auto-detect from current directory.

        Returns:
            Absolute path to migrations directory.

        Raises:
            FileNotFoundError: If no migrations directory can be found.
        """
        ...

    def scan_migrations(self, directory: str) -> GraphState:
        """Scan a directory for migration files.

        Args:
            directory: Path to the migrations directory.

        Returns:
            GraphState containing all parsed migrations.
        """
        ...

    def read_migration(self, directory: str, path: str) -> str:
        """Read a migration file's content.

        Args:
            directory: Base directory containing migrations.
            path: Relative path to the migration file.

        Returns:
            File content as string.
        """
        ...

    def write_migration(
        self, directory: str, path: str, content: str, dry_run: bool = False
    ) -> None:
        """Write content to a migration file.

        Args:
            directory: Base directory containing migrations.
            path: Relative path to the migration file.
            content: New file content.
            dry_run: If True, don't actually write the file.
        """
        ...


class ProviderRegistry(Protocol):
    """Interface for provider registry/factory."""

    def get_repository(self, provider_name: str) -> MigrationRepository:
        """Get a repository for the given provider."""
        ...

    def detect_provider(self, start_path: str) -> str | None:
        """Auto-detect the provider from the filesystem."""
        ...

    def list_providers(self) -> List[str]:
        """List available provider names."""
        ...
