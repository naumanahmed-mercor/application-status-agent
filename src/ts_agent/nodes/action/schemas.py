"""
Schemas for the Action node.
"""

from typing import Dict, Any, Optional, TypedDict
from pydantic import BaseModel, Field


class ActionData(TypedDict, total=False):
    """Data structure for action execution (stored at state level)."""
    hop_number: Optional[int]  # Which hop triggered this action
    tool_name: Optional[str]
    tool_result: Optional[Dict[str, Any]]
    execution_time_ms: Optional[float]
    execution_status: Optional[str]
    audit_notes: Optional[str]
    timestamp: Optional[str]
    success: Optional[bool]
    error: Optional[str]


class ActionToolCall(BaseModel):
    """Schema for an action tool call."""
    tool_name: str = Field(..., description="Name of the action tool to call")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Parameters for the action tool call")
    reasoning: str = Field(..., description="Why this action tool needs to be executed")


class ActionResult(BaseModel):
    """Schema for an action tool execution result."""
    tool_name: str = Field(..., description="Name of the action tool that was executed")
    success: bool = Field(..., description="Whether the action tool execution was successful")
    data: Optional[Any] = Field(None, description="Action tool execution result data")
    error: Optional[str] = Field(None, description="Error message if execution failed")
    execution_time_ms: float = Field(..., description="Action tool execution time in milliseconds")
    timestamp: str = Field(..., description="When the action tool was executed")
    audit_notes: str = Field(..., description="Audit notes about the action execution and its effects")
    
    class Config:
        arbitrary_types_allowed = True

