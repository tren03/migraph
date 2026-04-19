"""Provider factory for migration repositories."""

from typing import Dict, List, Type

from migraph.repositories.alembic import AlembicRepository
from migraph.repositories.interfaces import MigrationRepository


class MigrationProviderFactory:
    """Factory for creating migration repository instances."""

    def __init__(self) -> None:
        self._providers: Dict[str, Type[MigrationRepository]] = {
            AlembicRepository.PROVIDER_NAME: AlembicRepository,
        }

    def register(
        self, name: str, repo_class: Type[MigrationRepository]
    ) -> "MigrationProviderFactory":
        """Register a new provider.

        Args:
            name: Provider identifier (e.g., "alembic", "django")
            repo_class: Repository class implementing MigrationRepository

        Returns:
            Self for method chaining.
        """
        self._providers[name] = repo_class
        return self

    def get_repository(self, provider_name: str | None = None) -> MigrationRepository:
        """Get a repository instance for the given provider.

        Args:
            provider_name: Provider name. If None, auto-detects.

        Returns:
            Configured MigrationRepository instance.

        Raises:
            ValueError: If provider is not registered.
        """
        if provider_name is None:
            provider_name = self.detect_provider()
            if provider_name is None:
                raise ValueError(
                    "Could not auto-detect migration provider. "
                    "Ensure you're in a project with a recognized config file "
                    "(e.g., alembic.ini)."
                )

        if provider_name not in self._providers:
            available = ", ".join(self.list_providers())
            raise ValueError(
                f"Unknown provider: '{provider_name}'. Available providers: {available}"
            )

        return self._providers[provider_name]()

    def detect_provider(self, start_path: str | None = None) -> str | None:
        """Auto-detect the migration provider from the filesystem.

        Args:
            start_path: Directory to start searching from. Defaults to cwd.

        Returns:
            Provider name if detected, None otherwise.
        """
        # Check Alembic
        if AlembicRepository.detect(start_path):
            return AlembicRepository.PROVIDER_NAME

        # Add more providers here in order of preference
        # if DjangoRepository.detect(start_path):
        #     return DjangoRepository.PROVIDER_NAME

        return None

    def list_providers(self) -> List[str]:
        """List available provider names."""
        return list(self._providers.keys())

    def is_registered(self, provider_name: str) -> bool:
        """Check if a provider is registered."""
        return provider_name in self._providers


# Global factory instance for convenience
_default_factory: MigrationProviderFactory | None = None


def get_provider_factory() -> MigrationProviderFactory:
    """Get the default provider factory instance."""
    global _default_factory
    if _default_factory is None:
        _default_factory = MigrationProviderFactory()
    return _default_factory


def get_repository(provider_name: str | None = None) -> MigrationRepository:
    """Convenience function to get a repository from the default factory."""
    return get_provider_factory().get_repository(provider_name)
