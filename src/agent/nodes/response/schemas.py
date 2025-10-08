"""
Schemas for the Response node.
"""

from typing import Optional
from pydantic import BaseModel, Field


class ResponseData(BaseModel):
    """Data structure for response node (stored at state level)."""
    success: bool = Field(..., description="Whether response delivery was successful")
    intercom_delivered: bool = Field(..., description="Whether message was delivered via Intercom")
    error: Optional[str] = Field(None, description="Error message if delivery failed")
    delivery_time_ms: Optional[float] = Field(None, description="Time taken to deliver response in milliseconds")
