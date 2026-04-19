import json
import shutil
from pathlib import Path
from unittest.mock import patch

from alembic_viz_scanner import scan_directory
from typer.testing import CliRunner

from alembic_viz.main import app

runner = CliRunner()
FIXTURES = Path(__file__).resolve().parents[2] / "tests" / "fixtures"


def test_scan_outputs_graphstate_for_fixture_directory():
    result = runner.invoke(app, ["scan", "--directory", "tests/fixtures/simple_linear"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["source_directory"].endswith("tests/fixtures/simple_linear")
    assert [migration["revision"] for migration in payload["migrations"]] == ["abc123", "def456", "ghi789"]
    assert payload["validation_errors"] == []


def test_validate_exits_nonzero_for_invalid_graph(tmp_path: Path):
    input_path = tmp_path / "invalid.json"
    input_path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "source_directory": "/tmp/versions",
                "migrations": [
                    {
                        "revision": "a",
                        "down_revision": "b",
                        "branch_labels": None,
                        "depends_on": None,
                        "path": "a.py",
                        "content_hash": "md5:a",
                        "line_number": 1,
                        "timestamp": None,
                        "metadata": {},
                    },
                    {
                        "revision": "b",
                        "down_revision": "a",
                        "branch_labels": None,
                        "depends_on": None,
                        "path": "b.py",
                        "content_hash": "md5:b",
                        "line_number": 1,
                        "timestamp": None,
                        "metadata": {},
                    },
                ],
                "validation_errors": [],
                "ui_state": {
                    "positions": {},
                    "zoom": 1.0,
                    "pan": {"x": 0.0, "y": 0.0},
                    "selected": [],
                },
            }
        ),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["validate-graph", str(input_path)])

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["validation_errors"][0]["type"] == "cycle"


def test_inspect_reports_heads_and_order(tmp_path: Path):
    scan_output = runner.invoke(app, ["scan", "--directory", "tests/fixtures/branched"])
    input_path = tmp_path / "branched.json"
    input_path.write_text(scan_output.stdout, encoding="utf-8")

    result = runner.invoke(app, ["inspect", str(input_path)])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["migrations_count"] == 4
    assert payload["heads"] == ["featA003", "main002"]
    assert payload["topological_order"] == ["base001", "featA002", "featA003", "main002"]


def test_diff_reports_reparenting(tmp_path: Path):
    old_path = tmp_path / "old.json"
    new_path = tmp_path / "new.json"

    old_path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "source_directory": "/tmp/versions",
                "migrations": [
                    {"revision": "base", "down_revision": None, "branch_labels": None, "depends_on": None, "path": "base.py", "content_hash": "md5:base", "line_number": 1, "timestamp": None, "metadata": {}},
                    {"revision": "child", "down_revision": "base", "branch_labels": None, "depends_on": None, "path": "child.py", "content_hash": "md5:child", "line_number": 1, "timestamp": None, "metadata": {}},
                ],
                "validation_errors": [],
                "ui_state": {"positions": {}, "zoom": 1.0, "pan": {"x": 0.0, "y": 0.0}, "selected": []},
            }
        ),
        encoding="utf-8",
    )
    new_path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "source_directory": "/tmp/versions",
                "migrations": [
                    {"revision": "base", "down_revision": None, "branch_labels": None, "depends_on": None, "path": "base.py", "content_hash": "md5:base", "line_number": 1, "timestamp": None, "metadata": {}},
                    {"revision": "child", "down_revision": None, "branch_labels": None, "depends_on": None, "path": "child.py", "content_hash": "md5:child", "line_number": 1, "timestamp": None, "metadata": {}},
                ],
                "validation_errors": [],
                "ui_state": {"positions": {}, "zoom": 1.0, "pan": {"x": 0.0, "y": 0.0}, "selected": []},
            }
        ),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["diff-graph", str(old_path), str(new_path)])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload == [
        {"revision": "child", "old_parents": ["base"], "new_parents": [], "type": "ChangeParent"},
        {"parent_revision": "base", "child_revision": "child", "type": "RemoveEdge"},
    ]


def test_view_help_lists_directory_option():
    result = runner.invoke(app, ["view", "--help"])

    assert result.exit_code == 0
    assert "--directory" in result.stdout
    assert "--port" in result.stdout
    assert "--output" in result.stdout


def test_view_passes_output_path_to_viewer(tmp_path: Path):
    output_path = tmp_path / "edited.json"

    with patch("alembic_viz.main.serve_graph") as mocked_serve_graph:
        result = runner.invoke(
            app,
            [
                "view",
                "--directory",
                "tests/fixtures/simple_linear",
                "--output",
                str(output_path),
                "--no-open",
            ],
        )

    assert result.exit_code == 0
    mocked_serve_graph.assert_called_once()
    assert mocked_serve_graph.call_args.kwargs["output_path"] == str(output_path)


def test_apply_dry_run_reports_pending_change(tmp_path: Path):
    fixture_dir = tmp_path / "simple_linear"
    shutil.copytree(FIXTURES / "simple_linear", fixture_dir)

    scan_result = runner.invoke(app, ["scan", "--directory", str(fixture_dir)])
    payload = json.loads(scan_result.stdout)
    payload["migrations"][2]["down_revision"] = "abc123"
    graph_path = tmp_path / "graph.json"
    graph_path.write_text(json.dumps(payload), encoding="utf-8")

    result = runner.invoke(app, ["apply", str(graph_path), "--directory", str(fixture_dir), "--dry-run"])

    assert result.exit_code == 0
    apply_payload = json.loads(result.stdout)
    assert apply_payload["data"]["changed_files_count"] == 1
    assert apply_payload["data"]["changes"][0]["applied"] is False


def test_apply_rewrites_migration_file(tmp_path: Path):
    fixture_dir = tmp_path / "simple_linear"
    shutil.copytree(FIXTURES / "simple_linear", fixture_dir)

    scan_result = runner.invoke(app, ["scan", "--directory", str(fixture_dir)])
    payload = json.loads(scan_result.stdout)
    payload["migrations"][2]["down_revision"] = "abc123"
    graph_path = tmp_path / "graph.json"
    graph_path.write_text(json.dumps(payload), encoding="utf-8")

    result = runner.invoke(app, ["apply", str(graph_path), "--directory", str(fixture_dir)])

    assert result.exit_code == 0
    updated = scan_directory(str(fixture_dir))
    by_revision = {migration.revision: migration for migration in updated.migrations}
    assert by_revision["ghi789"].down_revision == "abc123"
