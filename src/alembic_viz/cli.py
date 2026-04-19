"""Typer-based CLI for the migration editing UI."""

import json
import sys
from pathlib import Path
from typing import Any, Optional

import typer
from typing_extensions import Annotated

from alembic_viz.models import ErrorResult, GraphState
from alembic_viz.scanner import find_versions_directory, scan_directory
from alembic_viz.viewer import serve_graph

app = typer.Typer(help="Main CLI for alembic-viz", add_completion=False)


@app.callback()
def cli() -> None:
    """Expose the browser editor as an explicit subcommand."""


def _format_json(data: Any) -> str:
    return json.dumps(data, indent=2, default=str)


def _error_and_exit(
    error_type: str, message: str, suggestion: Optional[str] = None, exit_code: int = 1
) -> None:
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
        _error_and_exit(
            "io_error", str(exc), suggestion="Check that the input path exists."
        )
    except json.JSONDecodeError as exc:
        _error_and_exit(
            "parse_error",
            f"Invalid JSON input: {exc}",
            suggestion="Provide valid GraphState JSON.",
        )
    except Exception as exc:
        _error_and_exit(
            "schema_error",
            f"Invalid GraphState input: {exc}",
            suggestion="Provide JSON matching the GraphState schema.",
        )

    raise AssertionError("unreachable")


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
        typer.Option(
            "--port",
            help="Port for the local viewer server. Uses a random port when 0.",
        ),
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
            versions_dir = find_versions_directory(
                explicit_path=directory, alembic_ini_path=alembic_ini
            )
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


def main() -> None:
    """Entry point for the alembic-viz CLI."""
    app()


if __name__ == "__main__":
    main()
