from langgraph.pregel import Pregel

from agent.graph import graph


def test_graph_compilation() -> None:
    """Test that the graph compiles correctly."""
    assert isinstance(graph, Pregel)
