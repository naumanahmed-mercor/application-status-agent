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
    # Input
    messages: List[Message]  # Array of conversation messages
    user_email: Optional[str]
    timestamp: Optional[str]
    
    # MCP Integration
    mcp_client: Optional[Any]  # MCP client instance
    available_tools: Optional[List[Dict[str, Any]]]  # Available tools from MCP server
    
    # Data Storage (Independent of hops)
    tool_data: Optional[Dict[str, Any]]  # Individual tool results by tool name
    docs_data: Optional[Dict[str, Any]]  # Individual docs results by query/topic
    
    # Loop Management
    hops: List[HopData]  # Array of hop data
    max_hops: Optional[int]  # Maximum allowed hops (default: 2)
    
    # Routing
    next_node: Optional[str]  # "plan", "respond", "end", "escalate"
    escalation_reason: Optional[str]
    
    # Output
    response: str
    error: Optional[str]
