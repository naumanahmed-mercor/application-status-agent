"""
Schemas for the Gather node.
"""

from typing import Dict, Any, List, Optional, TypedDict
from pydantic import BaseModel, Field, validator


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
    
    @validator('tool_name')
    def validate_tool_name(cls, v):
        """Validate that the tool name exists in available tools."""
        available_tools = [
            "get_user_background_status",
            "get_user_applications", 
            "get_user_applications_detailed",
            "get_user_jobs",
            "get_user_interviews",
            "get_user_work_trials",
            "get_user_fraud_reports",
            "get_user_details",
            "search_talent_docs",
            "get_talent_docs_stats"
        ]
        if v not in available_tools:
            raise ValueError(f"Tool '{v}' is not available. Available tools: {available_tools}")
        return v
    
    @validator('parameters')
    def validate_parameters(cls, v, values):
        """Validate parameters based on tool requirements."""
        tool_name = values.get('tool_name')
        if not tool_name:
            return v
            
        # Define required parameters for each tool
        tool_requirements = {
            "get_user_background_status": ["user_email"],
            "get_user_applications": ["user_email"],
            "get_user_applications_detailed": ["user_email"],
            "get_user_jobs": ["user_email"],
            "get_user_interviews": ["user_email"],
            "get_user_work_trials": ["user_email"],
            "get_user_fraud_reports": ["user_email"],
            "get_user_details": ["user_email"],
            "search_talent_docs": ["query"],
            "get_talent_docs_stats": []
        }
        
        required_params = tool_requirements.get(tool_name, [])
        
        # Check if all required parameters are provided
        for param in required_params:
            if param not in v:
                raise ValueError(f"Tool '{tool_name}' requires parameter '{param}'")
        
        # Validate specific parameter types
        if tool_name == "search_talent_docs":
            if "threshold" in v and not isinstance(v["threshold"], (int, float)):
                raise ValueError("threshold must be a number")
            if "limit" in v and not isinstance(v["limit"], int):
                raise ValueError("limit must be an integer")
        
        return v


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
