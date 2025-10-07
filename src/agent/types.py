"""Types and state definitions for the agent."""

from typing import Dict, Any, List, Optional, TYPE_CHECKING
from typing_extensions import TypedDict

if TYPE_CHECKING:
    from agent.nodes.plan.schemas import PlanData
    from agent.nodes.gather.schemas import GatherData
    from agent.nodes.coverage.schemas import CoverageData


class HopData(TypedDict, total=False):
    """Data for a single hop with nested structure."""
    hop_number: int
    plan: Optional[Dict[str, Any]]
    gather: Optional[Dict[str, Any]]
    coverage: Optional[Dict[str, Any]]


class Message(TypedDict, total=False):
    """Individual message in a conversation."""
    role: str  # "user" or "assistant"
    content: str


class State(TypedDict, total=False):
    """State for the LangGraph."""
    # Input (Intercom)
    conversation_id: str  # Intercom conversation ID (primary input)
    messages: List[Message]  # Array of conversation messages (fetched from Intercom)
    user_email: Optional[str]  # User email (fetched from Intercom)
    melvin_admin_id: Optional[str]  # Melvin bot admin ID for Intercom actions
    timestamp: Optional[str]
    
    # MCP Integration
    mcp_client: Optional[Any]  # MCP client instance
    available_tools: Optional[List[Dict[str, Any]]]  # Available tools from MCP server
    
    # Data Storage (Independent of hops)
    tool_data: Optional[Dict[str, Any]]  # Individual tool results by tool name
    docs_data: Optional[Dict[str, Any]]  # Individual docs results by query/topic
    
    # Loop Management (Plan → Gather → Coverage)
    hops: List[HopData]  # Array of hop data
    max_hops: Optional[int]  # Maximum allowed hops (default: 2)
    
    # Post-Loop Nodes (Draft, Validate, Escalate, Response)
    draft: Optional[Dict[str, Any]]  # Draft node data
    validate: Optional[Dict[str, Any]]  # Validate node data
    escalate: Optional[Dict[str, Any]]  # Escalate node data
    response_delivery: Optional[Dict[str, Any]]  # Response node delivery data
    finalize: Optional[Dict[str, Any]]  # Finalize node data
    
    # Routing
    next_node: Optional[str]  # "plan", "respond", "end", "escalate"
    escalation_reason: Optional[str]
    
    # Output
    response: str
    error: Optional[str]
    
    # Intercom Configuration
    metadata: Optional[Dict[str, Any]]  # Additional metadata for Intercom
