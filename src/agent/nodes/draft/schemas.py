"""
Schemas for the Draft node.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


class DraftRequest(BaseModel):
    """Schema for draft node input."""
    user_query: str = Field(..., description="The original user query")
    tool_data: Optional[Dict[str, Any]] = Field(None, description="Accumulated tool data")
    docs_data: Optional[Dict[str, Any]] = Field(None, description="Accumulated docs data")
    user_email: Optional[str] = Field(None, description="User email if available")


class DraftResponse(BaseModel):
    """Schema for draft node output."""
    response: str = Field(..., description="Generated response to the user query")
    confidence: float = Field(..., description="Confidence score for the response (0.0-1.0)")
    sources_used: list = Field(default_factory=list, description="List of sources used in the response")
    response_type: str = Field(..., description="Type of response: 'complete', 'partial', 'escalation_needed'")


class DraftData(BaseModel):
    """Schema for draft node data storage."""
    response: str = Field(..., description="Generated response")
    confidence: float = Field(..., description="Confidence score")
    sources_used: list = Field(default_factory=list, description="Sources used")
    response_type: str = Field(..., description="Type of response")
    generation_time_ms: Optional[float] = Field(None, description="Time taken to generate response")
    timestamp: Optional[str] = Field(None, description="Timestamp of generation")
