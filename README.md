# migraph

Interactive browser UI for visualizing and rewiring Alembic migration graphs.

## Demo


https://github.com/user-attachments/assets/4d41197a-58cd-497c-bfa6-8ea2446151bf



## Install

```bash
pip install migraph
# or
uv tool install migraph
```

## Usage

```bash
# Auto-detect alembic.ini from current directory
migraph

# Explicit config or provider
migraph --config path/to/alembic.ini
migraph --provider alembic --config path/to/alembic.ini
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
