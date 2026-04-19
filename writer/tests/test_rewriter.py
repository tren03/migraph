import json
import shutil
from pathlib import Path

import pytest
from alembic_viz_contracts.models import GraphState
from alembic_viz_scanner import scan_directory
from alembic_viz_writer.rewriter import ConflictFailure, ValidationFailure, apply_graph_state


FIXTURES = Path(__file__).resolve().parents[2] / "tests" / "fixtures"


def copy_fixture(tmp_path: Path, name: str) -> Path:
    source = FIXTURES / name
    target = tmp_path / name
    shutil.copytree(source, target)
    return target


def test_apply_graph_state_dry_run_reports_changes_without_writing(tmp_path: Path):
    fixture_dir = copy_fixture(tmp_path, "simple_linear")
    graph = scan_directory(str(fixture_dir))
    graph.migrations[2].down_revision = "abc123"
    original = (fixture_dir / "003_add_index.py").read_text(encoding="utf-8")

    result = apply_graph_state(graph, str(fixture_dir), dry_run=True)

    assert result["data"]["changed_files_count"] == 1
    assert result["data"]["changes"][0]["applied"] is False
    assert (fixture_dir / "003_add_index.py").read_text(encoding="utf-8") == original


def test_apply_graph_state_rewrites_down_revision(tmp_path: Path):
    fixture_dir = copy_fixture(tmp_path, "simple_linear")
    graph = scan_directory(str(fixture_dir))
    graph.migrations[2].down_revision = "abc123"

    result = apply_graph_state(graph, str(fixture_dir), dry_run=False)
    updated = scan_directory(str(fixture_dir))
    by_revision = {migration.revision: migration for migration in updated.migrations}

    assert result["data"]["changed_files_count"] == 1
    assert by_revision["ghi789"].down_revision == "abc123"


def test_apply_graph_state_rejects_invalid_target_graph(tmp_path: Path):
    fixture_dir = copy_fixture(tmp_path, "simple_linear")
    graph = scan_directory(str(fixture_dir))
    graph.migrations[0].down_revision = "ghi789"

    with pytest.raises(ValidationFailure):
        apply_graph_state(graph, str(fixture_dir), dry_run=True)


def test_apply_graph_state_detects_content_hash_conflict(tmp_path: Path):
    fixture_dir = copy_fixture(tmp_path, "simple_linear")
    graph = scan_directory(str(fixture_dir))
    graph.migrations[2].down_revision = "abc123"

    file_path = fixture_dir / "003_add_index.py"
    file_path.write_text(file_path.read_text(encoding="utf-8") + "\n# changed\n", encoding="utf-8")

    with pytest.raises(ConflictFailure):
        apply_graph_state(graph, str(fixture_dir), dry_run=False)
