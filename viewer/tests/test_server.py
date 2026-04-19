import json
import shutil
from pathlib import Path

from alembic_viz_contracts.models import GraphState, MigrationMetadata, MigrationNode, Position, UIState

from alembic_viz_viewer import build_view_model, preview_graph_state, save_graph_state
from alembic_viz_viewer.server import apply_graph_to_repo


FIXTURES = Path(__file__).resolve().parents[2] / "tests" / "fixtures"


def make_node(revision, down_revision=None, description=None):
    return MigrationNode(
        revision=revision,
        down_revision=down_revision,
        path=f"{revision}.py",
        content_hash=f"md5:{revision}",
        metadata=MigrationMetadata(description=description),
    )


def test_build_view_model_assigns_layout_and_summary():
    graph = GraphState(
        source_directory="/tmp/versions",
        migrations=[
            make_node("base", description="Base migration"),
            make_node("feature", "base", description="Feature migration"),
            make_node("head", "feature", description="Head migration"),
        ],
    )

    payload = build_view_model(graph)

    assert payload["summary"] == {
        "migrations_count": 3,
        "heads": ["head"],
        "orphans": [],
        "cycles": [],
    }
    assert [node["revision"] for node in payload["layout"]["nodes"]] == ["base", "feature", "head"]
    assert payload["layout"]["edges"] == [
        {"from": "base", "to": "feature"},
        {"from": "feature", "to": "head"},
    ]


def test_build_view_model_marks_orphans_and_cycles():
    graph = GraphState(
        source_directory="/tmp/versions",
        migrations=[
            make_node("a", "c"),
            make_node("b", "a"),
            make_node("c", "b"),
            make_node("orphan", "missing"),
        ],
    )

    payload = build_view_model(graph)
    nodes = {node["revision"]: node for node in payload["layout"]["nodes"]}

    assert payload["summary"]["orphans"] == ["orphan"]
    assert payload["summary"]["cycles"] == [["a", "b", "c", "a"]]
    assert nodes["orphan"]["is_orphan"] is True
    assert nodes["a"]["in_cycle"] is True
    assert nodes["b"]["in_cycle"] is True
    assert nodes["c"]["in_cycle"] is True


def test_build_view_model_honors_saved_ui_positions():
    graph = GraphState(
        source_directory="/tmp/versions",
        migrations=[
            make_node("base"),
            make_node("child", "base"),
        ],
        ui_state=UIState(positions={"child": Position(x=420, y=360)}),
    )

    payload = build_view_model(graph)
    nodes = {node["revision"]: node for node in payload["layout"]["nodes"]}

    assert nodes["child"]["x"] == 420
    assert nodes["child"]["y"] == 360


def test_save_graph_state_writes_output_file(tmp_path):
    graph = GraphState(source_directory="/tmp/versions", migrations=[make_node("base")])
    output_path = tmp_path / "graph.json"

    saved = save_graph_state(graph, str(output_path))

    assert saved == str(output_path)
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["migrations"][0]["revision"] == "base"


def test_preview_graph_state_updates_summary_after_reparent():
    graph = GraphState(
        source_directory="/tmp/versions",
        migrations=[
            make_node("base"),
            make_node("child", "base"),
            make_node("leaf", "child"),
        ],
    )
    graph.migrations[2].down_revision = "base"

    payload = preview_graph_state(graph)
    nodes = {node["revision"]: node for node in payload["layout"]["nodes"]}

    assert payload["summary"]["heads"] == ["child", "leaf"]
    assert nodes["leaf"]["down_revision"] == "base"


def test_apply_graph_to_repo_rewrites_fixture_directory(tmp_path):
    fixture_dir = tmp_path / "simple_linear"
    shutil.copytree(FIXTURES / "simple_linear", fixture_dir)
    graph = GraphState.model_validate(scan_fixture_graph(fixture_dir))
    graph.migrations[2].down_revision = "abc123"

    result = apply_graph_to_repo(graph, str(fixture_dir))
    updated = GraphState.model_validate(scan_fixture_graph(fixture_dir))
    by_revision = {migration.revision: migration for migration in updated.migrations}

    assert result["data"]["changed_files_count"] == 1
    assert by_revision["ghi789"].down_revision == "abc123"


def scan_fixture_graph(directory: Path):
    from alembic_viz_scanner import scan_directory

    return scan_directory(str(directory)).model_dump(mode="json")
