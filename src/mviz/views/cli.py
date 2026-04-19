"""CLI controller for mviz."""

from typing import Optional

import typer
from typing_extensions import Annotated

from mviz.domain.models import GraphState
from mviz.repositories.provider_factory import get_provider_factory
from mviz.services.scanner_service import ScannerService
from mviz.views.cli_utils import error_and_exit
from mviz.views.http import serve_graph

app = typer.Typer(help="mviz - Migration visualizer", add_completion=False)


@app.callback(invoke_without_command=True)
def view(
    ctx: typer.Context,
    provider: Annotated[
        Optional[str],
        typer.Option(
            "--provider",
            "-p",
            help="Migration provider (alembic, etc.). Auto-detected if not specified.",
        ),
    ] = None,
    config: Annotated[
        Optional[str],
        typer.Option(
            "--config",
            "-c",
            help="Path to provider-specific config file (e.g., alembic.ini).",
        ),
    ] = None,
) -> None:
    """Open migrations in a local browser viewer."""
    if ctx.invoked_subcommand is not None:
        return

    # Validate provider if specified
    if provider is not None:
        factory = get_provider_factory()
        if not factory.is_registered(provider):
            available = ", ".join(factory.list_providers())
            error_and_exit(
                "config_error",
                f"Unknown provider: '{provider}'",
                suggestion=f"Available providers: {available}",
            )

    # Scan migrations
    scanner = ScannerService()
    try:
        graph: GraphState = scanner.scan(
            config_path=config,
            provider=provider,
        )
        apply_dir = graph.source_directory
    except FileNotFoundError as exc:
        error_and_exit(
            "io_error",
            str(exc),
            suggestion="Ensure config file is discoverable from current directory "
            "or specify --config explicitly.",
        )
    except ValueError as exc:
        error_and_exit(
            "config_error",
            str(exc),
            suggestion="Specify --provider explicitly or run from a project root.",
        )
    except Exception as exc:
        error_and_exit(
            "parse_error",
            str(exc),
            suggestion="Check that migration files are readable and valid.",
        )

    serve_graph(
        graph=graph,
        host="127.0.0.1",
        port=0,
        open_browser=True,
        output_path=None,
        apply_directory=apply_dir,
        scan_config_path=config,
        scan_provider=provider,
    )


def main() -> None:
    """Entry point for the mviz CLI."""
    app()


if __name__ == "__main__":
    main()
