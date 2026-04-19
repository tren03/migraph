"""State persistence utilities for the HTTP server."""

import json
from pathlib import Path
from typing import Optional

from mviz.domain.models import GraphState


def load_template(filename: str) -> bytes:
    """Load a template file from the templates directory."""
    template_path = Path(__file__).parent.parent / "templates" / filename
    return template_path.read_bytes()


def save_graph_state(graph: GraphState, output_path: str | None) -> Optional[str]:
    """Persist an edited graph state when an output path is provided.

    Args:
        graph: The graph state to save.
        output_path: Path to save to, or None to skip saving.

    Returns:
        The output path if saved, None otherwise.
    """
    if not output_path:
        return None
    output = Path(output_path)
    output.write_text(
        json.dumps(graph.model_dump(mode="json"), indent=2), encoding="utf-8"
    )
    return str(output)
