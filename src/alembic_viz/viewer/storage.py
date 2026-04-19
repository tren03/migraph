"""Storage operations for graph state."""

import json
from pathlib import Path
from typing import Any, Dict, Optional

from alembic_viz.models import GraphState
from alembic_viz.writer.rewriter import apply_graph_state


def save_graph_state(graph: GraphState, output_path: Optional[str]) -> Optional[str]:
    """Persist an edited graph state when an output path is provided."""
    if not output_path:
        return None

    output = Path(output_path)
    output.write_text(
        json.dumps(graph.model_dump(mode="json"), indent=2), encoding="utf-8"
    )
    return str(output)


def apply_graph_to_repo(
    graph: GraphState, directory: Optional[str], dry_run: bool = False
) -> Dict[str, Any]:
    """Apply the current graph back to a repository directory."""
    target_directory = directory or graph.source_directory
    return apply_graph_state(graph=graph, directory=target_directory, dry_run=dry_run)
