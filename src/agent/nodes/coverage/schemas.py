"""Schemas for coverage node."""

from typing import List, Dict, Any, Optional, TypedDict
from pydantic import BaseModel, Field, validator


class CoverageData(TypedDict, total=False):
    """Coverage analysis data for a hop."""
    coverage_analysis: Optional[Dict[str, Any]]
    data_sufficient: Optional[bool]
    next_node: Optional[str]  # "plan", "respond", "end", "escalate"
    escalation_reason: Optional[str]


class DataGap(BaseModel):
    """Schema for identifying missing data."""
    gap_type: str = Field(..., description="Type of missing data (e.g., 'user_profile', 'application_details')")
    description: str = Field(..., description="Description of what data is missing")


class CoverageAnalysis(BaseModel):
    """Schema for coverage analysis results."""
    user_query: str = Field(..., description="Original user query")
    data_sufficient: bool = Field(..., description="Whether we have sufficient data to respond")
    coverage_score: float = Field(..., ge=0.0, le=1.0, description="Coverage score (0-1)")
    available_data: List[str] = Field(..., description="List of data types we have")
    missing_data: List[DataGap] = Field(..., description="List of missing data gaps")
    reasoning: str = Field(..., description="Reasoning for the coverage assessment")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in the analysis")
    
    # Removed strict validation - LLM can provide missing_data even when data_sufficient is True
    # This allows for more nuanced coverage analysis


class CoverageRequest(BaseModel):
    """Schema for coverage node input."""
    user_query: str = Field(..., description="Original user query")
    tool_results: List[Dict[str, Any]] = Field(..., description="Results from executed tools")
    successful_tools: List[str] = Field(..., description="Names of successfully executed tools")
    failed_tools: List[str] = Field(..., description="Names of failed tools")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")


class CoverageResponse(BaseModel):
    """Schema for coverage node output."""
    analysis: CoverageAnalysis = Field(..., description="Coverage analysis results")
    next_action: str = Field(..., description="Next action: 'continue', 'gather_more', 'escalate'")
    escalation_reason: Optional[str] = Field(None, description="Reason for escalation if needed")
