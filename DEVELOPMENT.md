# Development

## Setup

```bash
git clone <repo>
cd mviz
uv sync
```

## Run

```bash
uv run mviz --config path/to/alembic.ini
```

## Lint & Format

```bash
uv run ruff check src/
uv run ruff format src/
```

## Adding a Provider

1. Create `src/mviz/repositories/{provider}/repo.py` implementing `MigrationRepository`
2. Add `PROVIDER_NAME` and `detect()` classmethod
3. Register in `provider_factory.py`

See `src/mviz/repositories/alembic/` as reference.
