"""Domain exceptions."""


class DomainError(Exception):
    """Base exception for domain errors."""

    pass


class ValidationError(DomainError):
    """Raised when validation fails."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ConflictError(DomainError):
    """Raised when target graph no longer matches filesystem."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class MigrationNotFoundError(DomainError):
    """Raised when a migration cannot be found."""

    def __init__(self, revision: str) -> None:
        super().__init__(f"Migration not found: {revision}")
        self.revision = revision


class FileParseError(DomainError):
    """Raised when parsing a migration file fails."""

    def __init__(self, file_path: str, message: str) -> None:
        super().__init__(f"Failed to parse {file_path}: {message}")
        self.file_path = file_path
        self.message = message
