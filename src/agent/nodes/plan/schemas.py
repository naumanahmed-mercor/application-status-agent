"""
Schemas for the Plan node.
"""

from typing import Dict, Any, List, Optional, TypedDict
from pydantic import BaseModel, Field, validator


class PlanData(TypedDict, total=False):
    """Data structure for plan node (stored in hop)."""
    plan: Optional[Dict[str, Any]]
    tool_calls: Optional[List[Dict[str, Any]]]
    reasoning: Optional[str]


class Plan(BaseModel):
    """Schema for the agent's execution plan."""
    reasoning: str = Field(..., description="Why this plan was created")
    tool_calls: List[Dict[str, Any]] = Field(..., description="List of tool calls to execute")


class PlanRequest(BaseModel):
    """Schema for plan node input."""
    conversation_history: List[Dict[str, Any]] = Field(..., description="Full conversation history")
    user_email: Optional[str] = Field(None, description="User email if available")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context from previous hops")
