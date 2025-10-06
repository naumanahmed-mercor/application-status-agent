"""Flexible Pydantic schemas for MCP tool responses."""

from typing import Dict, Any
from pydantic import BaseModel


class FlexibleResponse(BaseModel):
    """Flexible response schema that accepts any data structure."""
    
    class Config:
        extra = "allow"  # Allow any extra fields
        arbitrary_types_allowed = True  # Allow arbitrary types


# All MCP tool responses use the same flexible schema
BackgroundStatusResponse = FlexibleResponse
ApplicationsResponse = FlexibleResponse
ApplicationsDetailedResponse = FlexibleResponse
JobsResponse = FlexibleResponse
InterviewsResponse = FlexibleResponse
WorkTrialsResponse = FlexibleResponse
FraudReportsResponse = FlexibleResponse
UserDetailsResponse = FlexibleResponse
SearchDocsResponse = FlexibleResponse
DocsStatsResponse = FlexibleResponse
