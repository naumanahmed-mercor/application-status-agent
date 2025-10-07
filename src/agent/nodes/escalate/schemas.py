"""
Schemas for the Escalate node.
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class EscalateData(BaseModel):
    """Data structure for escalate node."""
    escalation_reason: str
    escalation_source: str  # "coverage", "validate", "draft", "other"
    note_added: bool = False
    note_content: Optional[str] = None
    timestamp: str
    context: Optional[Dict[str, Any]] = None  # Additional context for escalation
