"""
Schemas for the Escalate node.
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class EscalateData(BaseModel):
    """Data structure for escalate node (stored at state level)."""
    escalation_reason: str = Field(..., description="Reason for escalation")
    escalation_source: str = Field(..., description="Source of escalation: 'coverage', 'validate', 'draft', etc.")
    note_added: bool = Field(False, description="Whether note was added to Intercom")
    note_content: Optional[str] = Field(None, description="Content of the escalation note")
    timestamp: str = Field(..., description="Timestamp of escalation")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context for escalation")
