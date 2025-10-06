"""MCP tool wrappers for talent success operations."""

import json
import logging
from typing import Optional, Dict, Any, List
from .client import MCPClient
from .schemas import (
    BackgroundStatusResponse,
    ApplicationsResponse,
    ApplicationsDetailedResponse,
    JobsResponse,
    InterviewsResponse,
    WorkTrialsResponse,
    FraudReportsResponse,
    UserDetailsResponse,
    SearchDocsResponse,
    DocsStatsResponse,
    FlexibleResponse
)

logger = logging.getLogger(__name__)


class MCPTools:
    """Wrapper class for MCP talent success tools."""
    
    def __init__(self, client: MCPClient):
        """
        Initialize MCP tools wrapper.
        
        Args:
            client: MCPClient instance
        """
        self.client = client
    
    def _parse_tool_result(self, content: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Parse tool result from MCP response content.
        
        Args:
            content: List of content items from MCP response
            
        Returns:
            Parsed JSON result
        """
        if not content:
            raise ValueError("No content in MCP response")
        
        # Get the first text content item
        text_content = content[0].get("text", "")
        if not text_content:
            raise ValueError("No text content in MCP response")
        
        try:
            return json.loads(text_content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from MCP response: {e}")
            raise ValueError(f"Invalid JSON in MCP response: {e}")
    
    def _create_flexible_response(self, data: Dict[str, Any]) -> FlexibleResponse:
        """
        Create a flexible response from parsed data.
        
        Args:
            data: Parsed JSON data from MCP response
            
        Returns:
            FlexibleResponse with the data
        """
        return FlexibleResponse(**data)
    
    def get_user_background_status(self, user_email: str) -> BackgroundStatusResponse:
        """
        Get background check status for a user.
        
        Args:
            user_email: User's email address
            
        Returns:
            Flexible response with background status data
        """
        content = self.client.call_tool("get_user_background_status", {"user_email": user_email})
        result = self._parse_tool_result(content)
        return self._create_flexible_response(result)
    
    def get_user_applications(self, user_email: str) -> ApplicationsResponse:
        """Get applications for a user."""
        content = self.client.call_tool("get_user_applications", {"user_email": user_email})
        result = self._parse_tool_result(content)
        return self._create_flexible_response(result)
    
    def get_user_applications_detailed(self, user_email: str) -> ApplicationsDetailedResponse:
        """Get detailed applications for a user."""
        content = self.client.call_tool("get_user_applications_detailed", {"user_email": user_email})
        result = self._parse_tool_result(content)
        return self._create_flexible_response(result)
    
    def get_user_jobs(self, user_email: str) -> JobsResponse:
        """Get jobs for a user."""
        content = self.client.call_tool("get_user_jobs", {"user_email": user_email})
        result = self._parse_tool_result(content)
        return self._create_flexible_response(result)
    
    def get_user_interviews(self, user_email: str) -> InterviewsResponse:
        """Get interviews for a user."""
        content = self.client.call_tool("get_user_interviews", {"user_email": user_email})
        result = self._parse_tool_result(content)
        return self._create_flexible_response(result)
    
    def get_user_work_trials(self, user_email: str) -> WorkTrialsResponse:
        """Get work trials for a user."""
        content = self.client.call_tool("get_user_work_trials", {"user_email": user_email})
        result = self._parse_tool_result(content)
        return self._create_flexible_response(result)
    
    def get_user_fraud_reports(self, user_email: str) -> FraudReportsResponse:
        """Get fraud reports for a user."""
        content = self.client.call_tool("get_user_fraud_reports", {"user_email": user_email})
        result = self._parse_tool_result(content)
        return self._create_flexible_response(result)
    
    def get_user_details(self, user_email: str) -> UserDetailsResponse:
        """Get user details."""
        content = self.client.call_tool("get_user_details", {"user_email": user_email})
        result = self._parse_tool_result(content)
        return self._create_flexible_response(result)
    
    def search_talent_docs(self, query: str, threshold: float = 0.3, limit: int = 5) -> SearchDocsResponse:
        """Search talent documentation."""
        content = self.client.call_tool("search_talent_docs", {
            "query": query,
            "threshold": threshold,
            "limit": limit
        })
        result = self._parse_tool_result(content)
        return self._create_flexible_response(result)
    
    def get_talent_docs_stats(self) -> DocsStatsResponse:
        """Get talent documentation statistics."""
        content = self.client.call_tool("get_talent_docs_stats", {})
        result = self._parse_tool_result(content)
        return self._create_flexible_response(result)
