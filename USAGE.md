# Usage

This file shows how to run the `alembic-viz` CLI against an Alembic migrations repository.

## Prerequisites

From this repository root:

```bash
# First-time setup: install the package
uv sync

# Or with pip
pip install -e .
```

> **Note:** You must run `uv sync` (or `pip install -e .`) once after cloning to make the `alembic-viz` command available.

## Sample Repo Assumptions

These examples assume your Alembic migrations live at `~/myproject/alembic/versions` with an `alembic.ini` file at `~/myproject/alembic.ini`.

Replace these paths with your actual locations.

## CLI Commands

### View in Browser

Open migrations in the interactive browser editor:

```bash
# Using explicit directory
uv run alembic-viz view --directory ~/myproject/alembic/versions

# Using alembic.ini discovery
uv run alembic-viz view --alembic-ini ~/myproject/alembic.ini

# From a saved GraphState JSON file
uv run alembic-viz view /tmp/graph-state.json

# Fixed port
uv run alembic-viz view --directory ~/myproject/alembic/versions --port 8765

# Export to file after editing
uv run alembic-viz view \
  --directory ~/myproject/alembic/versions \
  --output /tmp/exported-graph.json

# Don't open browser automatically
uv run alembic-viz view --directory ~/myproject/alembic/versions --no-open
```
~/work/mpower-lms 

### Alternative: Using Python module

```bash
python -m alembic_viz view --directory ~/myproject/alembic/versions
```

## Interactive Viewer Features

Once the browser opens:

- **Drag nodes** to reposition them
- **Drag the gold handle** at the bottom of a node onto another node to reparent
- **Click a node** to see details and detach its parent
- **Export Graph** button - save the current graph state to JSON
- **Apply To Repo** button - write parent changes back to migration files
- **Reset Layout** button - restore auto-positioned layout

Press `Ctrl+C` in the terminal to stop the server.

## Help

```bash
uv run alembic-viz --help
uv run alembic-viz view --help
```
