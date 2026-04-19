"""Scanner service - use case for scanning migrations from any provider."""

from migraph.domain.models import GraphState
from migraph.repositories.interfaces import MigrationRepository
from migraph.repositories.provider_factory import get_repository


class ScannerService:
    """Service for scanning migration directories from any provider."""

    def __init__(self, repo: MigrationRepository | None = None) -> None:
        self.repo = repo

    def scan(
        self,
        config_path: str | None = None,
        provider: str | None = None,
    ) -> GraphState:
        """Scan for migrations.

        Args:
            config_path: Path to provider-specific config file.
            provider: Provider name (e.g., "alembic"). Auto-detected if not specified.

        Returns:
            GraphState with all found migrations.
        """
        # Get repository (cached or new)
        if self.repo is None:
            self.repo = get_repository(provider)

        # Find migrations root and scan
        migrations_root = self.repo.find_migrations_root(config_path)
        return self.repo.scan_migrations(migrations_root)
