from alembic_viz_contracts.models import GraphState, MigrationNode

from alembic_viz_graph_ops import detect_cycles, detect_heads, detect_orphans, validate


def make_node(revision, down_revision=None, depends_on=None):
    return MigrationNode(
        revision=revision,
        down_revision=down_revision,
        depends_on=depends_on,
        path=f"{revision}.py",
        content_hash=f"md5:{revision}",
    )


def make_graph(*nodes):
    return GraphState(source_directory="/tmp/versions", migrations=list(nodes))


def test_detect_heads_for_branched_graph():
    graph = make_graph(
        make_node("base"),
        make_node("main", "base"),
        make_node("feature", "base"),
        make_node("feature_2", "feature"),
    )

    assert detect_heads(graph) == ["feature_2", "main"]


def test_detect_orphans_for_missing_parent_and_dependency():
    graph = make_graph(
        make_node("base"),
        make_node("child", "missing_parent"),
        make_node("depends", depends_on="missing_dependency"),
    )

    assert detect_orphans(graph) == ["child", "depends"]


def test_detect_cycles_returns_closed_path():
    graph = make_graph(
        make_node("a", "c"),
        make_node("b", "a"),
        make_node("c", "b"),
    )

    assert detect_cycles(graph) == [["a", "b", "c", "a"]]


def test_validate_reports_duplicate_orphan_and_cycle_errors():
    graph = make_graph(
        make_node("dup"),
        make_node("dup"),
        make_node("orphan", "missing"),
        make_node("a", "c"),
        make_node("b", "a"),
        make_node("c", "b"),
    )

    error_types = [error.type for error in validate(graph)]

    assert error_types == ["duplicate_revision", "orphan", "cycle"]
