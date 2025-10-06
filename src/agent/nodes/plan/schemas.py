"""Schemas for plan node."""

from typing import List, Dict, Any, Optional, TypedDict
from pydantic import BaseModel, Field, validator


class PlanData(TypedDict, total=False):
    """Planning data for a hop."""
    plan: Optional[Dict[str, Any]]
    tool_calls: Optional[List[Dict[str, Any]]]
    reasoning: Optional[str]


class Plan(BaseModel):
    """Schema for the agent's execution plan."""
    user_query: str = Field(..., description="Original user query")
    user_email: Optional[str] = Field(None, description="User email if provided")
    reasoning: str = Field(..., description="Why this plan was created")
    tool_calls: List[Dict[str, Any]] = Field(..., description="List of tool calls to execute")
    
    @validator('tool_calls')
    def validate_tool_calls(cls, v):
        """Validate that tool calls are well-formed."""
        # Allow empty tool calls for simple queries like "Hi"
        return v


class PlanRequest(BaseModel):
    """Schema for plan node input."""
    user_query: str = Field(..., description="User's question or request")
    user_email: Optional[str] = Field(None, description="User email if available")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")


class PlanResponse(BaseModel):
    """Schema for plan node output."""
    plan: Plan = Field(..., description="Generated execution plan")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in the plan (0-1)")
    estimated_time_seconds: float = Field(..., description="Estimated execution time")
