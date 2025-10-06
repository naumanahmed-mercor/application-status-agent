"""Runner for code-first usage of the agent."""

import time
import uuid
from typing import List, Dict, Any, Optional
from agent.graph import build_graph
from agent.types import Message
from src.mcp.factory import create_mcp_client

_app = build_graph()


def run_agent_with_messages(messages: List[Message], user_email: str = None) -> dict:
    """
    Run the agent with a conversation history.
    
    Args:
        messages: List of conversation messages with role and content
        user_email: User's email address (optional)
        
    Returns:
        Dictionary with response and metadata
    """
    # Extract the latest user message as the primary query
    latest_user_message = None
    for message in reversed(messages):
        if message["role"] == "user":
            latest_user_message = message["content"]
            break
    
    if not latest_user_message:
        return {
            "response": "No user message found in conversation",
            "error": "No user message provided"
        }
    
    # Initialize MCP client and fetch available tools
    try:
        print("🔌 Initializing MCP client...")
        mcp_client = create_mcp_client()
        
        # Fetch available tools from MCP server
        print("🔧 Fetching available tools from MCP server...")
        available_tools = mcp_client.list_tools()
        print(f"✅ Found {len(available_tools)} available tools")
        
    except Exception as e:
        print(f"❌ Failed to initialize MCP client: {e}")
        return {
            "response": "Sorry, I'm unable to connect to the required services right now.",
            "error": f"MCP initialization failed: {str(e)}"
        }
    
    # Prepare initial state with conversation history
    initial_state = {
        "messages": messages,  # Full conversation history
        "user_email": user_email,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "mcp_client": mcp_client,  # MCP client instance
        "available_tools": available_tools,  # Available tools from MCP server
        "tool_data": {},  # Initialize empty tool data
        "docs_data": {},  # Initialize empty docs data
        "hops": [],  # Initialize empty hops array
        "max_hops": 2,  # Default max hops
        "response": "",  # Initialize response
        "error": None  # Initialize error
    }
    
    # Run the graph
    final_state = _app.invoke(initial_state)
    
    # Extract response
    response = final_state.get("response", "No response generated")
    error = final_state.get("error")
    
    # Extract data from hops array
    hops_array = final_state.get("hops", [])
    current_hop_index = len(hops_array) - 1  # Last hop is current
    
    # Extract data from state level (independent of hops)
    tool_data = final_state.get("tool_data", {})
    docs_data = final_state.get("docs_data", {})
    
    return {
        "response": response,
        "error": error,
        # Data (independent of hops)
        "tool_data": tool_data,  # Individual tool results by tool name
        "docs_data": docs_data,  # Individual docs results by query/topic
        # Loop management
        "hops": hops_array,
        "max_hops": final_state.get("max_hops", 2),
        # Routing
        "next_node": final_state.get("next_node"),
        "escalation_reason": final_state.get("escalation_reason")
    }
