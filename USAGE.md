# Usage

This file shows how to run the main `alembic-viz` CLI against a sample Alembic repo at `~/work/mpower-lms`.

## Prerequisites

From this repository root:

```bash
uv sync --all-packages
```

## Sample Repo Assumptions

These examples assume your Alembic migrations live in one of these common locations inside `~/work/mpower-lms`:

```bash
~/work/mpower-lms/alembic/versions
~/work/mpower-lms/alembic.ini
```

If your repo uses a different layout, replace the paths below.

## 1. Scan Migrations

Scan a known versions directory and print `GraphState` JSON to stdout:

```bash
uv run alembic-viz scan --directory ~/work/mpower-lms/alembic/versions
```

Scan using `alembic.ini` discovery instead:

```bash
uv run alembic-viz scan --alembic-ini ~/work/mpower-lms/alembic.ini
```

Write scan output to a file for later steps:

```bash
uv run alembic-viz scan \
  --directory ~/work/mpower-lms/alembic/versions \
  --output /tmp/mpower-graph.json
```

Skip graph validation during scan:

```bash
uv run alembic-viz scan \
  --directory ~/work/mpower-lms/alembic/versions \
  --no-validate
```

## 2. Inspect the Graph

Inspect a saved `GraphState` file:

```bash
uv run alembic-viz inspect /tmp/mpower-graph.json
```

Pipe scan output directly into inspect:

```bash
uv run alembic-viz scan --directory ~/work/mpower-lms/alembic/versions \
  | uv run alembic-viz inspect
```

This prints a summary including:

- migration count
- heads
- orphans
- cycles
- layers
- topological order

## 3. Validate the Graph

Validate a saved `GraphState` file:

```bash
uv run alembic-viz validate-graph /tmp/mpower-graph.json
```

Write validated output to a new file:

```bash
uv run alembic-viz validate-graph /tmp/mpower-graph.json \
  --output /tmp/mpower-graph-validated.json
```

Important:

- exit code `0` means no validation errors
- exit code `1` means validation errors were found

Example check:

```bash
uv run alembic-viz validate-graph /tmp/mpower-graph.json
echo $?
```

## 4. Diff Two GraphState Files

Compare two graph snapshots:

```bash
uv run alembic-viz diff-graph /tmp/mpower-graph-before.json /tmp/mpower-graph-after.json
```

Write the diff to a file:

```bash
uv run alembic-viz diff-graph \
  /tmp/mpower-graph-before.json \
  /tmp/mpower-graph-after.json \
  --output /tmp/mpower-graph-diff.json
```

## 5. View in Browser

Open the sample repo directly in the browser viewer:

```bash
uv run alembic-viz view --directory ~/work/mpower-lms/alembic/versions
```

Open it using `alembic.ini` discovery:

```bash
uv run alembic-viz view --alembic-ini ~/work/mpower-lms/alembic.ini
```

Open a previously saved `GraphState` JSON file:

```bash
uv run alembic-viz view /tmp/mpower-graph.json
```

Run the viewer on a fixed port:

```bash
uv run alembic-viz view \
  --directory ~/work/mpower-lms/alembic/versions \
  --port 8765
```

Useful notes:

- the viewer starts a local HTTP server on `127.0.0.1`
- it opens your default browser automatically
- keep the terminal running while viewing the graph
- press `Ctrl+C` to stop the server

## 6. Useful Test Flow

End-to-end read-only flow for quick testing:

```bash
uv run alembic-viz scan \
  --directory ~/work/mpower-lms/alembic/versions \
  --output /tmp/mpower-graph.json

uv run alembic-viz inspect /tmp/mpower-graph.json

uv run alembic-viz validate-graph /tmp/mpower-graph.json

uv run alembic-viz view /tmp/mpower-graph.json
```

## 7. Running From Outside This Repo

If you are inside `~/work/mpower-lms` instead of this repo, run the CLI via this workspace explicitly:

```bash
uv run --directory /Users/user/Projects/alembic-migrations-checker alembic-viz scan \
  --directory ~/work/mpower-lms/alembic/versions
```

And for inspect via pipe:

```bash
uv run --directory /Users/user/Projects/alembic-migrations-checker alembic-viz scan \
  --directory ~/work/mpower-lms/alembic/versions \
  | uv run --directory /Users/user/Projects/alembic-migrations-checker alembic-viz inspect
```

And to open the browser viewer from inside `~/work/mpower-lms`:

```bash
uv run --directory /Users/user/Projects/alembic-migrations-checker alembic-viz view \
  --directory ~/work/mpower-lms/alembic/versions
```

## Notes

- `inspect`, `validate-graph`, and `diff-graph` work with `GraphState` JSON files or stdin
- `scan` reads Alembic migration files and emits `GraphState` JSON
- `view` opens a read-only browser visualization of the graph
- `apply` and `fix` are not implemented yet in the main CLI package
