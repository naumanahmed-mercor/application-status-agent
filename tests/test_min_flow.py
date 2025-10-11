"""Smoke tests for the minimal agent flow."""

import pytest
from src.ts_agent.runner import run_agent


def test_basic_agent_flow():
    """Test basic agent flow with user input."""
    message = "Hello, how can you help me?"
    result = run_agent(message)
    
    # Should have a response
    assert isinstance(result, str)
    assert len(result) > 0


def test_agent_returns_string():
    """Test that agent returns a string response."""
    message = "What can you do?"
    result = run_agent(message)
    
    # Should return a string
    assert isinstance(result, str)


if __name__ == "__main__":
    # Run tests if called directly
    test_basic_agent_flow()
    test_agent_returns_string()
    print("✅ All tests passed!")
