"""Factory for creating MCP client and tools."""

import os
from typing import Optional
from .client import MCPClient
from .tools import MCPTools


def create_mcp_client(
    base_url: Optional[str] = None,
    auth_token: Optional[str] = None
) -> MCPClient:
    """
    Create MCP client with configuration from environment variables.
    
    Args:
        base_url: MCP server base URL (defaults to MCP_BASE_URL env var)
        auth_token: Authentication token (defaults to MCP_AUTH_TOKEN env var)
        
    Returns:
        Configured MCPClient instance
        
    Raises:
        ValueError: If required configuration is missing
    """
    base_url = base_url or os.getenv("MCP_BASE_URL")
    auth_token = auth_token or os.getenv("MCP_AUTH_TOKEN")
    
    if not base_url:
        raise ValueError("MCP_BASE_URL environment variable is required")
    if not auth_token:
        raise ValueError("MCP_AUTH_TOKEN environment variable is required")
    
    return MCPClient(base_url=base_url, auth_token=auth_token)


def create_mcp_tools(
    base_url: Optional[str] = None,
    auth_token: Optional[str] = None
) -> MCPTools:
    """
    Create MCP tools wrapper with configuration from environment variables.
    
    Args:
        base_url: MCP server base URL (defaults to MCP_BASE_URL env var)
        auth_token: Authentication token (defaults to MCP_AUTH_TOKEN env var)
        
    Returns:
        Configured MCPTools instance
    """
    client = create_mcp_client(base_url, auth_token)
    return MCPTools(client)
