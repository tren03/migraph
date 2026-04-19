# Usage (Development)

This document is for **development** of migraph itself.

For **installing and using** the tool, see [README.md](./README.md).

## Prerequisites

From this repository root:

```bash
# First-time setup: install the package in editable mode
uv sync

# Or with pip
pip install -e .
```

## Sample Repo Assumptions

These examples assume your migrations live at `~/myproject/alembic/versions` with an `alembic.ini` file at `~/myproject/alembic.ini`.

Replace these paths with your actual locations.

## CLI Commands

### View in Browser

```bash
# Auto-detect provider and config
uv run migraph

# Explicitly specify Alembic
uv run migraph --provider alembic

# Specify config file
uv run migraph --config ~/myproject/alembic.ini

# Combine options
uv run migraph --provider alembic --config ~/myproject/alembic.ini
```

### Alternative: Using Python module

```bash
python -m migraph --config ~/myproject/alembic.ini
```

## Help

```bash
uv run migraph --help
```

## Development Commands

```bash
# Format code
uv run ruff format src/

# Check linting
uv run ruff check src/

# Build package
uv build
```

## Adding a New Provider

To add support for a new migration provider (e.g., Django, Flyway):

1. Create `src/migraph/repositories/{provider}_repo.py`
2. Implement `MigrationRepository` interface
3. Add `PROVIDER_NAME` class attribute
4. Implement `detect()` classmethod for auto-detection
5. Register in `provider_factory.py`
6. Add tests

See `alembic_repo.py` as a reference implementation.
