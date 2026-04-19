# Development

## Setup

```bash
git clone <repo>
cd migraph
uv sync
```

## Run

```bash
uv run migraph --config path/to/alembic.ini
```

## Lint & Format

```bash
uv run ruff check src/
uv run ruff format src/
```

## Release

```bash
git tag v0.1.0
git push origin v0.1.0
```

Pushing a `v*` tag triggers the GitHub Actions workflow which builds and publishes to PyPI via [trusted publishing](https://docs.pypi.org/trusted-publishers/).

**One-time PyPI setup:** go to PyPI → your project → Publishing → add a trusted publisher with `owner/<repo>`, workflow `publish.yml`, environment `pypi`.

## Adding a Provider

1. Create `src/migraph/repositories/{provider}/repo.py` implementing `MigrationRepository`
2. Add `PROVIDER_NAME` and `detect()` classmethod
3. Register in `provider_factory.py`

See `src/migraph/repositories/alembic/` as reference.
