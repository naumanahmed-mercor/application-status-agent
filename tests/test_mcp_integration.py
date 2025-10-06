"""Tests for MCP integration."""

import pytest
from unittest.mock import Mock, patch
from src.mcp.factory import create_mcp_tools
from src.mcp.schemas import BackgroundStatusResponse


def test_mcp_tools_creation():
    """Test that MCP tools can be created with environment variables."""
    with patch.dict('os.environ', {
        'MCP_BASE_URL': 'https://aws.api.mercor.com',
        'MCP_AUTH_TOKEN': 'test-token'
    }):
        # This should not raise an exception
        tools = create_mcp_tools()
        assert tools is not None


def test_mcp_tools_missing_config():
    """Test that MCP tools creation fails with missing configuration."""
    with patch.dict('os.environ', {}, clear=True):
        with pytest.raises(ValueError, match="MCP_BASE_URL environment variable is required"):
            create_mcp_tools()


def test_mcp_tools_missing_auth():
    """Test that MCP tools creation fails with missing auth token."""
    with patch.dict('os.environ', {
        'MCP_BASE_URL': 'https://aws.api.mercor.com'
    }, clear=True):
        with pytest.raises(ValueError, match="MCP_AUTH_TOKEN environment variable is required"):
            create_mcp_tools()


@patch('src.mcp.tools.MCPClient')
def test_get_user_background_status(mock_client_class):
    """Test getting user background status."""
    # Mock the client and its methods
    mock_client = Mock()
    mock_client_class.return_value = mock_client
    
    # Mock the call_tool response
    mock_content = [{
        "type": "text",
        "text": '{"user_email": "test@example.com", "background_status": "Standard Package: Passed", "user_id": "user123"}'
    }]
    mock_client.call_tool.return_value = mock_content
    
    # Create tools instance
    tools = create_mcp_tools("https://test.com", "test-token")
    
    # Call the method
    result = tools.get_user_background_status("test@example.com")
    
    # Verify the result
    assert isinstance(result, BackgroundStatusResponse)
    assert result.user_email == "test@example.com"
    assert result.background_status == "Standard Package: Passed"
    assert result.user_id == "user123"
    
    # Verify the client was called correctly
    mock_client.call_tool.assert_called_once_with("get_user_background_status", {"user_email": "test@example.com"})


if __name__ == "__main__":
    # Run tests if called directly
    test_mcp_tools_creation()
    test_mcp_tools_missing_config()
    test_mcp_tools_missing_auth()
    print("✅ All MCP integration tests passed!")
