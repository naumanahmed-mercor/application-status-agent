"""
Schemas for the Initialize node.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class InitializeData(BaseModel):
    """Data structure for initialize node (stored at state level)."""
    conversation_id: str = Field(..., description="Intercom conversation ID")
    messages_count: int = Field(..., description="Number of messages fetched")
    user_name: Optional[str] = Field(None, description="User name from Intercom")
    user_email: Optional[str] = Field(None, description="User email from Intercom")
    subject: Optional[str] = Field(None, description="Conversation subject")
    tools_count: int = Field(..., description="Number of available tools")
    melvin_admin_id: str = Field(..., description="Melvin bot admin ID")
    timestamp: str = Field(..., description="Initialization timestamp")
    success: bool = Field(..., description="Whether initialization was successful")
    error: Optional[str] = Field(None, description="Error message if initialization failed")

