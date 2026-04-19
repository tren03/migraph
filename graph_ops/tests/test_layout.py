import pytest

from alembic_viz_contracts.models import GraphState, MigrationNode

from alembic_viz_graph_ops import calculate_layers, topological_sort


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


def test_topological_sort_orders_parents_before_children():
    graph = make_graph(
        make_node("base"),
        make_node("feature", "base"),
        make_node("reporting", "feature", depends_on="base"),
    )

    assert topological_sort(graph) == ["base", "feature", "reporting"]


def test_calculate_layers_uses_deepest_ancestor():
    graph = make_graph(
        make_node("base"),
        make_node("main", "base"),
        make_node("feature", "base"),
        make_node("merge", ["main", "feature"]),
    )

    assert calculate_layers(graph) == {
        "base": 0,
        "feature": 1,
        "main": 1,
        "merge": 2,
    }


def test_topological_sort_rejects_cycles():
    graph = make_graph(
        make_node("a", "b"),
        make_node("b", "a"),
    )

    with pytest.raises(ValueError, match="Cannot topologically sort cyclic graph"):
        topological_sort(graph)
