import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mviz.domain.models import GraphState, MigrationMetadata, MigrationNode
from mviz.views.view_model import build_view_model


class BuildViewModelTests(unittest.TestCase):
    def test_layout_keeps_heads_above_ancestors_when_input_is_reordered(self) -> None:
        graph = GraphState(
            source_directory="/tmp/migrations",
            migrations=[
                MigrationNode(
                    revision="child",
                    down_revision="parent",
                    path="child.py",
                    metadata=MigrationMetadata(description="child"),
                ),
                MigrationNode(
                    revision="root",
                    down_revision=None,
                    path="root.py",
                    metadata=MigrationMetadata(description="root"),
                ),
                MigrationNode(
                    revision="parent",
                    down_revision="root",
                    path="parent.py",
                    metadata=MigrationMetadata(description="parent"),
                ),
            ],
        )

        payload = build_view_model(graph)
        nodes = {node["revision"]: node for node in payload["layout"]["nodes"]}
        edges = payload["layout"]["edges"]

        self.assertLess(nodes["child"]["y"], nodes["parent"]["y"])
        self.assertLess(nodes["parent"]["y"], nodes["root"]["y"])
        self.assertEqual(
            edges,
            [
                {"from": "parent", "to": "child"},
                {"from": "root", "to": "parent"},
            ],
        )

    def test_valid_graph_ignores_stale_saved_positions_and_reflows(self) -> None:
        graph = GraphState.model_validate(
            {
                "source_directory": "/tmp/migrations",
                "migrations": [
                    {
                        "revision": "branch_a",
                        "down_revision": "root",
                        "path": "branch_a.py",
                    },
                    {
                        "revision": "branch_b",
                        "down_revision": "root",
                        "path": "branch_b.py",
                    },
                    {
                        "revision": "root",
                        "down_revision": None,
                        "path": "root.py",
                    },
                ],
                "ui_state": {
                    "positions": {
                        "root": {"x": 9999, "y": 9999},
                        "branch_a": {"x": 8888, "y": 8888},
                        "branch_b": {"x": 7777, "y": 7777},
                    },
                    "pinned": [],
                },
            }
        )

        payload = build_view_model(graph)
        nodes = {node["revision"]: node for node in payload["layout"]["nodes"]}

        self.assertEqual(nodes["root"]["x"], 80)
        self.assertEqual(nodes["root"]["y"], 210)
        self.assertEqual(nodes["branch_a"]["y"], 80)
        self.assertEqual(nodes["branch_b"]["y"], 80)
        self.assertNotEqual(nodes["branch_a"]["x"], nodes["branch_b"]["x"])

    def test_cyclic_graph_uses_cycle_tolerant_layout(self) -> None:
        graph = GraphState.model_validate(
            {
                "source_directory": "/tmp/migrations",
                "migrations": [
                    {
                        "revision": "a",
                        "down_revision": "b",
                        "path": "a.py",
                    },
                    {
                        "revision": "b",
                        "down_revision": "a",
                        "path": "b.py",
                    },
                ],
            }
        )

        payload = build_view_model(graph)
        nodes = {node["revision"]: node for node in payload["layout"]["nodes"]}

        self.assertEqual(nodes["a"]["y"], 80)
        self.assertEqual(nodes["b"]["y"], 80)
        self.assertNotEqual(nodes["a"]["x"], nodes["b"]["x"])

    def test_detached_root_uses_saved_position(self) -> None:
        graph = GraphState.model_validate(
            {
                "source_directory": "/tmp/migrations",
                "migrations": [
                    {
                        "revision": "leaf",
                        "down_revision": None,
                        "path": "leaf.py",
                    },
                    {
                        "revision": "child",
                        "down_revision": "root",
                        "path": "child.py",
                    },
                    {
                        "revision": "root",
                        "down_revision": None,
                        "path": "root.py",
                    },
                ],
                "ui_state": {
                    "positions": {
                        "leaf": {"x": 640, "y": 320},
                    },
                    "pinned": ["leaf"],
                },
            }
        )

        payload = build_view_model(graph)
        nodes = {node["revision"]: node for node in payload["layout"]["nodes"]}

        self.assertEqual(nodes["leaf"]["x"], 640)
        self.assertEqual(nodes["leaf"]["y"], 320)


if __name__ == "__main__":
    unittest.main()
