"""
Schemas for the Finalize node.
"""

from typing import Optional
from pydantic import BaseModel


class FinalizeData(BaseModel):
    """Data structure for finalize node."""
    melvin_status: str
    status_updated: bool = False
    conversation_snoozed: bool = False
    snooze_duration_seconds: int = 300  # 5 minutes
    error: Optional[str] = None
