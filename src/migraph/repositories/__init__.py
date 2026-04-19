"""Repository layer - data access abstractions for migration providers."""

from migraph.repositories.alembic import AlembicRepository
from migraph.repositories.interfaces import MigrationRepository, ProviderRegistry
from migraph.repositories.provider_factory import (
    MigrationProviderFactory,
    get_provider_factory,
    get_repository,
)

__all__ = [
    # Interfaces
    "MigrationRepository",
    "ProviderRegistry",
    # Factory
    "MigrationProviderFactory",
    "get_provider_factory",
    "get_repository",
    # Provider implementations
    "AlembicRepository",
]
