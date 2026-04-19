# mviz

Interactive browser UI for visualizing and rewiring Alembic migration graphs.

## Install

```bash
pip install mviz
# or
uv tool install mviz
```

## Usage

```bash
# Auto-detect alembic.ini from current directory
mviz

# Explicit config or provider
mviz --config path/to/alembic.ini
mviz --provider alembic --config path/to/alembic.ini
```

## Browser UI

| Action | How |
|---|---|
| Select node | Click |
| Rewire parent | Click node A, then click node B → B becomes A's parent |
| Detach parent | Select node → **Detach Parent** |
| Restore from disk | **Refresh from Disk** |
| Write changes to files | **Apply to Repo** |
| Re-run auto layout | **Auto Format** |
| Discard all edits | **Reset Layout** |

Press `Ctrl+C` to stop the server.

## Requirements

Python 3.9+, Alembic project with `alembic.ini`

---

[Development →](DEVELOPMENT.md)
