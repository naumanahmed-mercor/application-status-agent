"""
Schemas for the Draft node.
"""

from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


class ResponseType(str, Enum):
    """Type of response from draft node."""
    REPLY = "REPLY"  # Normal response to be sent to user
    ROUTE_TO_TEAM = "ROUTE_TO_TEAM"  # User requested to talk to a human


class DraftRequest(BaseModel):
    """Schema for draft node input."""
    user_query: str = Field(..., description="The original user query")
    tool_data: Optional[Dict[str, Any]] = Field(None, description="Accumulated tool data")
    docs_data: Optional[Dict[str, Any]] = Field(None, description="Accumulated docs data")
    user_email: Optional[str] = Field(None, description="User email if available")


class DraftResponse(BaseModel):
    """Schema for draft node output."""
    response: str = Field(..., description="Generated response text")
    response_type: ResponseType = Field(..., description="Type of response: REPLY or ROUTE_TO_TEAM")


class DraftData(BaseModel):
    """Schema for draft node data storage."""
    response: str = Field(..., description="Generated response text")
    response_type: ResponseType = Field(..., description="Type of response")
    generation_time_ms: Optional[float] = Field(None, description="Time taken to generate response")
    timestamp: Optional[str] = Field(None, description="Timestamp of generation")
