import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from migraph.domain.models import GraphState, MigrationMetadata, MigrationNode
from migraph.views.view_model import build_view_model


class BuildViewModelTests(unittest.TestCase):
    def test_edges_follow_down_revision(self) -> None:
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
        nodes = {node["revision"]: node for node in payload["nodes"]}
        edges = payload["edges"]

        self.assertIn("child", nodes)
        self.assertIn("parent", nodes)
        self.assertIn("root", nodes)
        self.assertIn({"source": "parent", "target": "child"}, edges)
        self.assertIn({"source": "root", "target": "parent"}, edges)

    def test_head_detection(self) -> None:
        graph = GraphState(
            source_directory="/tmp/migrations",
            migrations=[
                MigrationNode(revision="head", down_revision="root", path="head.py"),
                MigrationNode(revision="root", down_revision=None, path="root.py"),
            ],
        )

        payload = build_view_model(graph)
        nodes = {node["revision"]: node for node in payload["nodes"]}

        self.assertTrue(nodes["head"]["is_head"])
        self.assertFalse(nodes["root"]["is_head"])
        self.assertEqual(payload["summary"]["heads"], ["head"])

    def test_orphan_detection(self) -> None:
        graph = GraphState(
            source_directory="/tmp/migrations",
            migrations=[
                MigrationNode(
                    revision="orphan",
                    down_revision="missing",
                    path="orphan.py",
                ),
            ],
        )

        payload = build_view_model(graph)
        nodes = {node["revision"]: node for node in payload["nodes"]}

        self.assertTrue(nodes["orphan"]["is_orphan"])
        self.assertEqual(payload["summary"]["orphans"], ["orphan"])

    def test_cycle_detection(self) -> None:
        graph = GraphState(
            source_directory="/tmp/migrations",
            migrations=[
                MigrationNode(revision="a", down_revision="b", path="a.py"),
                MigrationNode(revision="b", down_revision="a", path="b.py"),
            ],
        )

        payload = build_view_model(graph)
        nodes = {node["revision"]: node for node in payload["nodes"]}

        self.assertTrue(nodes["a"]["in_cycle"])
        self.assertTrue(nodes["b"]["in_cycle"])
        self.assertTrue(len(payload["summary"]["cycles"]) > 0)

    def test_edges_omit_missing_parents(self) -> None:
        graph = GraphState(
            source_directory="/tmp/migrations",
            migrations=[
                MigrationNode(
                    revision="orphan",
                    down_revision="missing",
                    path="orphan.py",
                ),
            ],
        )

        payload = build_view_model(graph)
        self.assertEqual(payload["edges"], [])

    def test_summary_counts(self) -> None:
        graph = GraphState(
            source_directory="/tmp/migrations",
            migrations=[
                MigrationNode(revision="a", down_revision=None, path="a.py"),
                MigrationNode(revision="b", down_revision="a", path="b.py"),
            ],
        )

        payload = build_view_model(graph)
        self.assertEqual(payload["summary"]["migrations_count"], 2)

    def test_no_layout_key_in_response(self) -> None:
        graph = GraphState(source_directory="/tmp", migrations=[])
        payload = build_view_model(graph)
        self.assertNotIn("layout", payload)
        self.assertIn("nodes", payload)
        self.assertIn("edges", payload)


if __name__ == "__main__":
    unittest.main()
