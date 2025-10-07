"""LangGraph for the agent."""

import os
import time
from langgraph.graph import StateGraph, START, END
from agent.types import State
from agent.nodes.plan.plan import plan_node
from agent.nodes.gather.gather import gather_node
from agent.nodes.coverage.coverage import coverage_node
from agent.nodes.draft.draft import draft_node
from agent.nodes.validate.validate import validate_node
from agent.nodes.escalate.escalate import escalate_node
from agent.nodes.response.response import response_node
from agent.nodes.finalize.finalize import finalize_node
from src.mcp.factory import create_mcp_client
from src.intercom.client import IntercomClient


def initialize_state(state: State) -> State:
    """Initialize the state by fetching conversation data from Intercom and MCP tools."""
    # Only initialize if not already done
    if "available_tools" not in state or state["available_tools"] is None:
        try:
            # Get conversation ID from state
            conversation_id = state.get("conversation_id")
            if not conversation_id:
                raise ValueError("conversation_id is required")
            
            print(f"📞 Fetching conversation data from Intercom: {conversation_id}")
            
            # Initialize Intercom client
            intercom_api_key = os.getenv("INTERCOM_API_KEY")
            if not intercom_api_key:
                raise ValueError("INTERCOM_API_KEY environment variable is required")
            
            intercom_client = IntercomClient(intercom_api_key)
            
            # Fetch conversation data (messages + email)
            conversation_data = intercom_client.get_conversation_data_for_agent(conversation_id)
            
            if not conversation_data.get("messages"):
                raise ValueError(f"No messages found in conversation {conversation_id}")
            
            # Update state with conversation data
            state["messages"] = conversation_data["messages"]
            state["user_email"] = conversation_data.get("user_email")
            
            # Get Melvin admin ID from environment
            melvin_admin_id = os.getenv("MELVIN_ADMIN_ID")
            if not melvin_admin_id:
                raise ValueError("MELVIN_ADMIN_ID environment variable is required")
            state["melvin_admin_id"] = melvin_admin_id
            
            print(f"✅ Fetched {len(conversation_data['messages'])} messages from Intercom")
            print(f"✅ User email: {conversation_data.get('user_email', 'Not found')}")
            print(f"✅ Melvin admin ID: {melvin_admin_id}")
            
            # Initialize MCP client
            print("🔌 Initializing MCP client...")
            mcp_client = create_mcp_client()
            
            # Fetch available tools from MCP server
            print("🔧 Fetching available tools from MCP server...")
            available_tools = mcp_client.list_tools()
            print(f"✅ Found {len(available_tools)} available tools")
            
            # Initialize state with proper values (NO MCP client in state)
            state["available_tools"] = available_tools
            state["tool_data"] = state.get("tool_data", {})
            state["docs_data"] = state.get("docs_data", {})
            state["hops"] = state.get("hops", [])
            state["max_hops"] = state.get("max_hops", 2)
            state["response"] = state.get("response", "")
            state["error"] = state.get("error", None)
            state["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%SZ")
            
        except Exception as e:
            print(f"❌ Failed to initialize: {e}")
            state["error"] = f"Initialization failed: {str(e)}"
            state["response"] = "Sorry, I'm unable to connect to the required services right now."
    
    return state


def build_graph():
    """Build the agent graph."""
    g = StateGraph(State)
    
    # Add nodes
    g.add_node("initialize", initialize_state)
    g.add_node("plan", plan_node)
    g.add_node("gather", gather_node)
    g.add_node("coverage", coverage_node)
    g.add_node("draft", draft_node)
    g.add_node("validate", validate_node)
    g.add_node("escalate", escalate_node)
    g.add_node("response", response_node)
    g.add_node("finalize", finalize_node)
    
    # Add edges
    g.add_edge(START, "initialize")
    g.add_edge("plan", "gather")
    g.add_edge("gather", "coverage")
    
    # Add conditional routing from coverage
    def route_from_coverage(state: State) -> str:
        """Route from coverage node based on analysis."""
        next_node = state.get("next_node", "end")
        
        if next_node == "plan":
            return "plan"
        elif next_node == "respond":
            return "draft"  # Route to draft node for response generation
        elif next_node == "escalate":
            return "escalate"  # Route to escalate node
        else:
            return "end"
    
    # Add conditional routing from initialize
    def route_from_initialize(state: State) -> str:
        """Route from initialize node based on success/failure."""
        if state.get("error"):
            return "escalate"  # If initialization failed, escalate
        else:
            return "plan"  # If successful, proceed to plan
    
    # Add conditional routing from validate
    def route_from_validate(state: State) -> str:
        """Route from validate node based on validation result."""
        next_node = state.get("next_node", "end")
        
        if next_node == "response":
            return "response"  # Validation passed, send response
        elif next_node == "escalate":
            return "escalate"  # Validation failed, escalate
        else:
            return "end"
    
    # Add conditional routing from draft
    def route_from_draft(state: State) -> str:
        """Route from draft node based on response type or error."""
        next_node = state.get("next_node")
        if next_node == "escalate":
            return "escalate"  # ROUTE_TO_TEAM or error
        else:
            return "validate"  # Normal REPLY, proceed to validation
    
    g.add_conditional_edges(
        "initialize",
        route_from_initialize,
        {
            "plan": "plan",
            "escalate": "escalate"
        }
    )
    
    g.add_conditional_edges(
        "coverage",
        route_from_coverage,
        {
            "plan": "plan",
            "draft": "draft",
            "escalate": "escalate",
            "end": END
        }
    )
    
    # Draft node routes conditionally
    g.add_conditional_edges(
        "draft",
        route_from_draft,
        {
            "validate": "validate",
            "escalate": "escalate"
        }
    )
    
    # Validate node routes conditionally
    g.add_conditional_edges(
        "validate",
        route_from_validate,
        {
            "response": "response",
            "escalate": "escalate",
            "end": END
        }
    )
    
    # Escalate and Response nodes go to finalize
    g.add_edge("escalate", "finalize")
    g.add_edge("response", "finalize")
    
    # Finalize node always ends
    g.add_edge("finalize", END)
    
    return g.compile()


# Export the graph for LangGraph CLI
graph = build_graph()