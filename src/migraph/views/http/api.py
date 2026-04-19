"""API endpoint business logic for the migration viewer.

These functions contain the business logic for handling API requests.
They operate on a HandlerContext and are separate from HTTP protocol handling.
"""

from migraph.domain.exceptions import ConflictError
from migraph.domain.exceptions import ValidationError as DomainValidationError
from migraph.domain.models import GraphState
from migraph.views.http.context import HandlerContext
from migraph.views.http.state import save_graph_state
from migraph.views.view_model import preview_graph_state


def handle_preview(context: HandlerContext, proposed: GraphState) -> dict:
    """Handle /api/preview - update context and return preview.

    Args:
        context: The handler context to update.
        proposed: The proposed new graph state.

    Returns:
        Response dictionary with preview data.
    """
    context.current_graph = proposed
    return preview_graph_state(context.current_graph)


def handle_save(context: HandlerContext, proposed: GraphState) -> dict:
    """Handle /api/save - save graph to output path.

    Args:
        context: The handler context to update.
        proposed: The proposed new graph state.

    Returns:
        Response dictionary with save result.
    """
    context.current_graph = proposed
    saved_output = save_graph_state(context.current_graph, context.output_path)
    return {
        "status": "success",
        "output_file": saved_output,
        "migrations_count": len(context.current_graph.migrations),
    }


def handle_apply(context: HandlerContext, proposed: GraphState) -> dict:
    """Handle /api/apply - write changes back to migration files.

    Args:
        context: The handler context to update.
        proposed: The proposed new graph state.

    Returns:
        Response dictionary with apply result or error.
    """
    context.current_graph = proposed
    target_directory = context.apply_directory or context.current_graph.source_directory

    try:
        result = context.writer_service.apply_graph(
            graph=context.current_graph, directory=target_directory, provider="alembic"
        )
        return result
    except DomainValidationError as exc:
        return {"status": "error", "message": str(exc)}
    except ConflictError as exc:
        return {"status": "error", "message": str(exc)}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}
