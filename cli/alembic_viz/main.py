"""Typer-based orchestration CLI for alembic-viz."""

import json
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Optional

import typer
from alembic_viz_contracts.models import ErrorResult, GraphState, ValidationError
from alembic_viz_graph_ops import calculate_layers, detect_cycles, detect_heads, detect_orphans, diff, topological_sort, validate
from alembic_viz_scanner import find_versions_directory, scan_directory
from alembic_viz_viewer import serve_graph
from alembic_viz_writer.rewriter import ConflictFailure, ValidationFailure, WriterError, apply_graph_state
from typing_extensions import Annotated

app = typer.Typer(help="Main CLI for alembic-viz", add_completion=False)


def _format_json(data: Any) -> str:
    return json.dumps(data, indent=2, default=str)


def _write_output(data: Any, output: Optional[str]) -> None:
    rendered = _format_json(data)
    if output:
        Path(output).write_text(rendered, encoding="utf-8")
        return
    print(rendered)


def _error_and_exit(error_type: str, message: str, suggestion: Optional[str] = None, exit_code: int = 1) -> None:
    error = ErrorResult(error_type=error_type, message=message, suggestion=suggestion)
    print(_format_json(error.model_dump()), file=sys.stderr)
    raise typer.Exit(exit_code)


def _load_input_text(input_path: Optional[str]) -> str:
    if input_path:
        return Path(input_path).read_text(encoding="utf-8")

    if sys.stdin.isatty():
        _error_and_exit(
            "io_error",
            "No input provided.",
            suggestion="Pass an input file path or pipe GraphState JSON on stdin.",
        )

    return sys.stdin.read()


def _load_graph_state(input_path: Optional[str]) -> GraphState:
    try:
        payload = json.loads(_load_input_text(input_path))
        return GraphState.model_validate(payload)
    except FileNotFoundError as exc:
        _error_and_exit("io_error", str(exc), suggestion="Check that the input path exists.")
    except json.JSONDecodeError as exc:
        _error_and_exit("parse_error", f"Invalid JSON input: {exc}", suggestion="Provide valid GraphState JSON.")
    except Exception as exc:
        _error_and_exit(
            "schema_error",
            f"Invalid GraphState input: {exc}",
            suggestion="Provide JSON matching the GraphState schema.",
        )

    raise AssertionError("unreachable")


def _merge_validation_errors(graph: GraphState) -> GraphState:
    merged_errors = [*graph.validation_errors, *validate(graph)]
    return graph.model_copy(update={"validation_errors": merged_errors})


def _serialize_operations(operations: list[Any]) -> list[dict[str, Any]]:
    serialized = []
    for operation in operations:
        if is_dataclass(operation):
            data = asdict(operation)
        else:
            data = dict(operation)
        data["type"] = operation.__class__.__name__
        serialized.append(data)
    return serialized


@app.command()
def scan(
    directory: Annotated[
        Optional[str],
        typer.Option("--directory", "-d", help="Path to Alembic versions directory"),
    ] = None,
    alembic_ini: Annotated[
        Optional[str],
        typer.Option("--alembic-ini", "-c", help="Path to alembic.ini config file"),
    ] = None,
    output: Annotated[
        Optional[str],
        typer.Option("--output", "-o", help="Write GraphState JSON to a file"),
    ] = None,
    include_validation: Annotated[
        bool,
        typer.Option("--validate/--no-validate", help="Include graph validation errors in output"),
    ] = True,
) -> None:
    """Scan migrations into GraphState JSON."""
    try:
        versions_dir = find_versions_directory(explicit_path=directory, alembic_ini_path=alembic_ini)
        graph = scan_directory(versions_dir)
        if include_validation:
            graph = _merge_validation_errors(graph)
        _write_output(graph.model_dump(), output)
    except FileNotFoundError as exc:
        _error_and_exit(
            "io_error",
            str(exc),
            suggestion="Provide explicit --directory or ensure alembic.ini is discoverable.",
        )
    except Exception as exc:
        _error_and_exit(
            "parse_error",
            str(exc),
            suggestion="Check that the Alembic files are readable and valid Python.",
        )


@app.command()
def validate_graph(
    input_path: Annotated[
        Optional[str],
        typer.Argument(help="Input GraphState JSON file. Reads stdin when omitted."),
    ] = None,
    output: Annotated[
        Optional[str],
        typer.Option("--output", "-o", help="Write validated GraphState JSON to a file"),
    ] = None,
) -> None:
    """Validate a GraphState JSON document."""
    graph = _merge_validation_errors(_load_graph_state(input_path))
    _write_output(graph.model_dump(), output)
    if graph.validation_errors:
        raise typer.Exit(1)


@app.command()
def inspect(
    input_path: Annotated[
        Optional[str],
        typer.Argument(help="Input GraphState JSON file. Reads stdin when omitted."),
    ] = None,
    output: Annotated[
        Optional[str],
        typer.Option("--output", "-o", help="Write summary JSON to a file"),
    ] = None,
) -> None:
    """Summarize graph structure from GraphState JSON."""
    graph = _load_graph_state(input_path)
    cycles = detect_cycles(graph)
    summary = {
        "migrations_count": len(graph.migrations),
        "heads": detect_heads(graph),
        "orphans": detect_orphans(graph),
        "cycles": cycles,
        "layers": None if cycles else calculate_layers(graph),
        "topological_order": None if cycles else topological_sort(graph),
    }
    _write_output(summary, output)


@app.command()
def diff_graph(
    old_path: Annotated[str, typer.Argument(help="Original GraphState JSON file")],
    new_path: Annotated[str, typer.Argument(help="Updated GraphState JSON file")],
    output: Annotated[
        Optional[str],
        typer.Option("--output", "-o", help="Write diff JSON to a file"),
    ] = None,
) -> None:
    """Diff two GraphState JSON documents."""
    old_graph = _load_graph_state(old_path)
    new_graph = _load_graph_state(new_path)
    operations = diff(old_graph, new_graph)
    _write_output(_serialize_operations(operations), output)


@app.command()
def view(
    input_path: Annotated[
        Optional[str],
        typer.Argument(help="Input GraphState JSON file. Reads stdin when omitted."),
    ] = None,
    directory: Annotated[
        Optional[str],
        typer.Option("--directory", "-d", help="Path to Alembic versions directory"),
    ] = None,
    alembic_ini: Annotated[
        Optional[str],
        typer.Option("--alembic-ini", "-c", help="Path to alembic.ini config file"),
    ] = None,
    host: Annotated[
        str,
        typer.Option("--host", help="Host interface for the local viewer server"),
    ] = "127.0.0.1",
    port: Annotated[
        int,
        typer.Option("--port", help="Port for the local viewer server. Uses a random port when 0."),
    ] = 0,
    output: Annotated[
        Optional[str],
        typer.Option("--output", "-o", help="Write exported GraphState JSON to a file"),
    ] = None,
    open_browser: Annotated[
        bool,
        typer.Option("--open/--no-open", help="Open the viewer in the default browser"),
    ] = True,
) -> None:
    """Open a graph in a local browser viewer."""
    if directory or alembic_ini:
        try:
            versions_dir = find_versions_directory(explicit_path=directory, alembic_ini_path=alembic_ini)
            graph = scan_directory(versions_dir)
        except FileNotFoundError as exc:
            _error_and_exit(
                "io_error",
                str(exc),
                suggestion="Provide explicit --directory or ensure alembic.ini is discoverable.",
            )
        except Exception as exc:
            _error_and_exit(
                "parse_error",
                str(exc),
                suggestion="Check that the Alembic files are readable and valid Python.",
            )
    else:
        graph = _load_graph_state(input_path)

    serve_graph(
        graph=graph,
        host=host,
        port=port,
        open_browser=open_browser,
        output_path=output,
        apply_directory=directory or graph.source_directory,
    )


@app.command()
def apply(
    input_path: Annotated[
        Optional[str],
        typer.Argument(help="Input GraphState JSON file. Reads stdin when omitted."),
    ] = None,
    directory: Annotated[
        Optional[str],
        typer.Option("--directory", "-d", help="Path to Alembic versions directory. Defaults to graph source_directory."),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Preview file changes without writing them"),
    ] = False,
    output: Annotated[
        Optional[str],
        typer.Option("--output", "-o", help="Write apply result JSON to a file"),
    ] = None,
) -> None:
    """Apply GraphState parent changes back to migration files."""
    graph = _load_graph_state(input_path)
    target_directory = directory or graph.source_directory

    try:
        result = apply_graph_state(graph=graph, directory=target_directory, dry_run=dry_run)
    except ValidationFailure as exc:
        _error_and_exit("validation_error", str(exc), suggestion="Fix graph cycles or orphaned references before applying.")
    except ConflictFailure as exc:
        _error_and_exit("conflict_error", str(exc), suggestion="Rescan the repository and reapply your edits to the latest graph.")
    except WriterError as exc:
        _error_and_exit("write_error", str(exc), suggestion="Check that the migration files are writable and contain down_revision assignments.")

    _write_output(result, output)


def main() -> None:
    """Entry point for the alembic-viz CLI."""
    app()


if __name__ == "__main__":
    main()
