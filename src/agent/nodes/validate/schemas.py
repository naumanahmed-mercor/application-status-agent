"""
Schemas for the Validate node.
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class IntentHit(BaseModel):
    """Individual intent detection result."""
    intent_id: str
    confidence: float
    evidence: str
    confirmed: bool


class Classification(BaseModel):
    """Classification results from validation."""
    hits: List[IntentHit] = Field(default_factory=list)


class PolicyValidation(BaseModel):
    """Policy validation results."""
    passed: bool
    violations: List[str] = Field(default_factory=list)
    blocked_intents: List[str] = Field(default_factory=list)


class ValidationResponse(BaseModel):
    """Response from validation endpoint."""
    response_text: str
    classification: Classification
    policy_validation: PolicyValidation
    overall_passed: bool
    processing_time_ms: float


class ValidateData(BaseModel):
    """Data structure for validate node (stored in hop)."""
    validation_response: Optional[Dict[str, Any]] = None
    overall_passed: bool
    validation_note_added: bool = False
    escalation_reason: Optional[str] = None
    next_action: str  # "response" or "escalate"
