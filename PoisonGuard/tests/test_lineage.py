import pytest
from poisonguard.data.schemas import LineageNode, NodeType
from poisonguard.methods.lineage import LineageGraph


def test_descendants_ancestors_and_cycle_rejection() -> None:
    graph = LineageGraph()
    for index, kind in enumerate([NodeType.EVENT, NodeType.MEMORY, NodeType.WINDOW]):
        graph.add_node(LineageNode(str(index), kind, index))
    graph.add_edge("0", "1")
    graph.add_edge("1", "2")
    assert graph.descendants({"0"}) == {"0", "1", "2"}
    assert graph.source_closure("2") == {"0"}
    with pytest.raises(ValueError):
        graph.add_edge("2", "0")
