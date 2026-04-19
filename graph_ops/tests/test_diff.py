from alembic_viz_contracts.models import GraphState, MigrationNode

from alembic_viz_graph_ops import AddEdge, AddedMigration, ChangeParent, RemoveEdge, RemovedMigration, diff


def make_node(revision, down_revision=None):
    return MigrationNode(
        revision=revision,
        down_revision=down_revision,
        path=f"{revision}.py",
        content_hash=f"md5:{revision}",
    )


def make_graph(*nodes):
    return GraphState(source_directory="/tmp/versions", migrations=list(nodes))


def test_diff_reports_added_removed_and_reparented_nodes():
    old = make_graph(
        make_node("base"),
        make_node("child", "base"),
        make_node("obsolete", "child"),
    )
    new = make_graph(
        make_node("base"),
        make_node("child", None),
        make_node("new_leaf", "child"),
    )

    assert diff(old, new) == [
        RemovedMigration(revision="obsolete"),
        AddedMigration(revision="new_leaf"),
        ChangeParent(revision="child", old_parents=("base",), new_parents=()),
        RemoveEdge(parent_revision="base", child_revision="child"),
    ]
