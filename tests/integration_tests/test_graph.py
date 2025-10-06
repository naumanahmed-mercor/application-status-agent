import pytest

from agent import graph

pytestmark = pytest.mark.anyio


@pytest.mark.langsmith
async def test_agent_simple_passthrough() -> None:
    """Test basic agent invocation."""
    inputs = {"message": "Hello, how can you help me?"}
    res = await graph.ainvoke(inputs)
    assert res is not None
