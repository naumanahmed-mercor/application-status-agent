"""
Schemas for the Coverage node.
"""

from typing import Dict, Any, List, Optional, TypedDict
from pydantic import BaseModel, Field


class CoverageData(TypedDict, total=False):
    """Data structure for coverage node (stored in hop)."""
    coverage_analysis: Optional[Dict[str, Any]]
    data_sufficient: Optional[bool]
    next_node: Optional[str]  # "plan", "respond", "end", "escalate"
    escalation_reason: Optional[str]


class DataGap(BaseModel):
    """Schema for identifying missing data."""
    model_config = {"extra": "forbid"}
    
    gap_type: str = Field(..., description="Type of missing data (e.g., 'user_profile', 'application_details')")
    description: str = Field(..., description="Description of what data is missing")


class CoverageAnalysis(BaseModel):
    """Schema for coverage analysis results."""
    model_config = {"extra": "forbid"}
    
    data_sufficient: bool = Field(..., description="Whether we have sufficient data to respond")
    missing_data: List[DataGap] = Field(default_factory=list, description="List of missing data gaps (empty if data is sufficient)")
    reasoning: str = Field(..., description="Detailed reasoning for the coverage assessment")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in the analysis (0.0-1.0)")


class CoverageRequest(BaseModel):
    """Schema for coverage node input."""
    conversation_history: List[Dict[str, Any]] = Field(..., description="Full conversation history")
    tool_results: List[Dict[str, Any]] = Field(..., description="Results from executed tools")
    successful_tools: List[str] = Field(..., description="Names of successfully executed tools")
    failed_tools: List[str] = Field(..., description="Names of failed tools")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")


class CoverageResponse(BaseModel):
    """Schema for coverage node output."""
    model_config = {"extra": "forbid"}
    
    data_sufficient: bool = Field(..., description="Whether we have sufficient data to respond")
    missing_data: List[DataGap] = Field(default_factory=list, description="List of missing data gaps (empty if data is sufficient)")
    reasoning: str = Field(..., description="Detailed reasoning for the coverage assessment")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in the analysis (0.0-1.0)")
    next_action: str = Field(..., description="Next action: 'continue' (sufficient data), 'gather_more' (need more data), 'escalate' (cannot gather data)")
    escalation_reason: Optional[str] = Field(None, description="Reason for escalation (required if next_action is 'escalate')")
