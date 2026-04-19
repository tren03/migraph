"""CLI for the Scanner module."""

import json
import sys
from pathlib import Path
from typing import Optional

import typer
from alembic_viz_contracts.models import ErrorResult, SuccessResult
from typing_extensions import Annotated

from alembic_viz_scanner.discovery import find_versions_directory
from alembic_viz_scanner.parser import scan_directory

app = typer.Typer(
    name="alembic-viz-scan",
    help="Scan Alembic migration files and output GraphState JSON",
    add_completion=False,
)


def format_json_output(data: dict) -> str:
    """Format JSON with consistent indentation."""
    return json.dumps(data, indent=2, default=str)


@app.command()
def scan(
    directory: Annotated[
        Optional[str],
        typer.Option(
            "--directory",
            "-d",
            help="Path to Alembic versions directory (auto-detected if not provided)",
        ),
    ] = None,
    alembic_ini: Annotated[
        Optional[str],
        typer.Option(
            "--alembic-ini",
            "-c",
            help="Path to alembic.ini config file (auto-detected if not provided)",
        ),
    ] = None,
    format: Annotated[
        str,
        typer.Option(
            "--format",
            "-f",
            help="Output format",
        ),
    ] = "json",
    output: Annotated[
        Optional[str],
        typer.Option(
            "--output",
            "-o",
            help="Output file (default: stdout)",
        ),
    ] = None,
):
    """Scan Alembic migration files and output GraphState.

    Examples:
        alembic-viz-scan --directory ./alembic/versions
        alembic-viz-scan --alembic-ini ./alembic.ini
        alembic-viz-scan > graph.json
    """
    try:
        # Find versions directory
        versions_dir = find_versions_directory(
            explicit_path=directory,
            alembic_ini_path=alembic_ini,
        )

        # Scan the directory
        graph_state = scan_directory(versions_dir)

        # Convert to dict and output
        result = graph_state.model_dump()

        json_output = format_json_output(result)

        if output:
            Path(output).write_text(json_output)
            success = SuccessResult(
                operation="scan",
                data={"output_file": output, "migrations_count": len(graph_state.migrations)},
            )
            print(format_json_output(success.model_dump()))
        else:
            print(json_output)

    except FileNotFoundError as e:
        error = ErrorResult(
            error_type="io_error",
            message=str(e),
            suggestion="Provide explicit --directory or ensure alembic.ini is in current or parent directory.",
        )
        print(format_json_output(error.model_dump()), file=sys.stderr)
        raise typer.Exit(1)

    except Exception as e:
        error = ErrorResult(
            error_type="parse_error",
            message=str(e),
            suggestion="Check that migration files are valid Python with libcst-compatible syntax.",
        )
        print(format_json_output(error.model_dump()), file=sys.stderr)
        raise typer.Exit(1)


def main():
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
