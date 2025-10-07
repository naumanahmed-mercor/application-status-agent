"""
Schemas for the Response node.
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class ResponseData(BaseModel):
    """Data structure for response node."""
    response: str
    user_id: Optional[str] = None
    conversation_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class IntercomMessage(BaseModel):
    """Intercom message structure."""
    user_id: str
    conversation_id: Optional[str] = None
    response: str
    metadata: Optional[Dict[str, Any]] = None
    timestamp: str
    agent_version: str = "1.0.0"


class Response(BaseModel):
    """Response node output."""
    success: bool
    intercom_delivered: bool
    error: Optional[str] = None
    delivery_time_ms: Optional[float] = None
