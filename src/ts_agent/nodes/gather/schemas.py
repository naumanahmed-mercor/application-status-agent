"""
Schemas for the Gather node.
"""

from typing import Dict, Any, List, Optional, TypedDict
from pydantic import BaseModel, Field


class GatherData(TypedDict, total=False):
    """Data structure for gather node (stored in hop)."""
    tool_results: Optional[List[Dict[str, Any]]]
    total_execution_time_ms: Optional[float]
    success_rate: Optional[float]
    execution_status: Optional[str]


class MCPTool(BaseModel):
    """Schema for MCP tool definition."""
    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description")
    parameters: Dict[str, Any] = Field(..., description="Tool parameters schema")


class ToolCall(BaseModel):
    """Schema for a planned tool call."""
    tool_name: str = Field(..., description="Name of the tool to call")
    parameters: Dict[str, Any] = Field(..., description="Parameters for the tool call")
    reasoning: str = Field(..., description="Why this tool is needed")
    
    # Note: Tool name and parameter validation is done in the plan node against
    # actual available tools and their schemas from the MCP server


class ToolResult(BaseModel):
    """Schema for a tool execution result."""
    tool_name: str = Field(..., description="Name of the tool that was executed")
    success: bool = Field(..., description="Whether the tool execution was successful")
    data: Optional[Any] = Field(None, description="Tool execution result data")
    error: Optional[str] = Field(None, description="Error message if execution failed")
    execution_time_ms: float = Field(..., description="Tool execution time in milliseconds")
    timestamp: str = Field(..., description="When the tool was executed")
    
    class Config:
        arbitrary_types_allowed = True


class GatherRequest(BaseModel):
    """Schema for gather node input."""
    tool_calls: List[ToolCall] = Field(..., description="List of tools to execute")
    user_email: Optional[str] = Field(None, description="User email for user data tools")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")
