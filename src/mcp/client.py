"""MCP client for communicating with the talent success MCP server."""

import json
import logging
from typing import Dict, Any, Optional, List
import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class MCPRequest(BaseModel):
    """JSON-RPC request model."""
    jsonrpc: str = "2.0"
    id: str | int | None
    method: str
    params: Optional[Dict[str, Any]] = None


class MCPResponse(BaseModel):
    """JSON-RPC response model."""
    jsonrpc: str = "2.0"
    id: str | int | None
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None


class MCPClient:
    """Client for communicating with the talent success MCP server."""
    
    def __init__(self, base_url: str, auth_token: str):
        """
        Initialize MCP client.
        
        Args:
            base_url: Base URL of the MCP server
            auth_token: Bearer token for authentication
        """
        self.base_url = base_url.rstrip('/')
        self.auth_token = auth_token
        self.client = httpx.Client(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {auth_token}",
                "Content-Type": "application/json"
            }
            # No client-level timeout - each request sets its own timeout
        )
    
    def _make_request(self, method: str, params: Optional[Dict[str, Any]] = None, request_id: str | int = 1, timeout: float = 30.0) -> MCPResponse:
        """
        Make a JSON-RPC request to the MCP server.
        
        Args:
            method: JSON-RPC method name
            params: Method parameters
            request_id: Request identifier
            timeout: Request timeout in seconds (defaults to 30s)
            
        Returns:
            MCPResponse object
            
        Raises:
            Exception: If request fails or returns an error
        """
        request_data = MCPRequest(
            id=request_id,
            method=method,
            params=params
        )
        
        try:
            response = self.client.post(
                "/webhook/talent-success/mcp",
                json=request_data.model_dump(),
                timeout=timeout
            )
            response.raise_for_status()
            
            response_data = response.json()
            mcp_response = MCPResponse(**response_data)
            
            if mcp_response.error:
                error_msg = f"MCP Error {mcp_response.error.get('code', 'unknown')}: {mcp_response.error.get('message', 'Unknown error')}"
                logger.error(f"MCP request failed: {error_msg}")
                raise Exception(error_msg)
            
            return mcp_response
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error in MCP request: {e}")
            raise Exception(f"HTTP error: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in MCP response: {e}")
            raise Exception(f"Invalid JSON response: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in MCP request: {e}")
            raise
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """
        List available tools from the MCP server.
        
        Returns:
            List of available tools
        """
        response = self._make_request("tools/list")
        return response.result.get("tools", [])
    
    def get_tool(self, tool_name: str) -> Dict[str, Any]:
        """
        Get details for a specific tool.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Tool details
        """
        response = self._make_request("tools/get", {"name": tool_name})
        return response.result.get("tool", {})
    
    def call_tool(self, tool_name: str, arguments: Dict[str, Any], timeout: float = 30.0) -> List[Dict[str, Any]]:
        """
        Call a tool with the given arguments.
        
        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments
            timeout: Request timeout in seconds (defaults to 30s)
            
        Returns:
            Tool execution result
        """
        response = self._make_request("tools/call", {
            "name": tool_name,
            "arguments": arguments
        }, timeout=timeout)
        return response.result.get("content", [])
    
    def close(self):
        """Close the HTTP client."""
        self.client.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
