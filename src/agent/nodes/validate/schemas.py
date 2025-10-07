"""
Schemas for the Validate node.
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel


class ValidationResponse(BaseModel):
    """
    Simplified response from validation endpoint.
    We only care about overall_passed for routing logic.
    """
    overall_passed: bool
    
    class Config:
        extra = "allow"  # Allow additional fields, ignore them


class ValidateData(BaseModel):
    """Data structure for validate node (stored in hop)."""
    validation_response: Optional[Dict[str, Any]] = None
    overall_passed: bool
    validation_note_added: bool = False
    escalation_reason: Optional[str] = None
    next_action: str  # "response" or "escalate"
