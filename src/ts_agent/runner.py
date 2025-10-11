"""Runner for code-first usage of the agent."""

import time
from typing import Dict, Any, Optional
from ts_agent.graph import build_graph

_app = build_graph()


def run_agent_with_conversation_id(conversation_id: str) -> dict:
    """
    Run the agent with an Intercom conversation ID.
    
    The agent will:
    1. Fetch conversation messages and user email from Intercom
    2. Initialize MCP tools
    3. Process the conversation through the agent workflow
    4. Send the response back to Intercom
    
    Args:
        conversation_id: Intercom conversation ID
        
    Returns:
        Dictionary with response and metadata
    """
    # Prepare initial state with conversation ID
    initial_state = {
        "conversation_id": conversation_id,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    
    # Run the graph (initialize node will fetch Intercom data)
    final_state = _app.invoke(initial_state)
    
    # Extract response
    response = final_state.get("response", "No response generated")
    error = final_state.get("error")
    
    # Extract data from hops array
    hops_array = final_state.get("hops", [])
    
    # Extract data from state level (independent of hops)
    tool_data = final_state.get("tool_data", {})
    docs_data = final_state.get("docs_data", {})
    
    # Extract user email from user_details
    user_details = final_state.get("user_details", {})
    user_email = user_details.get("email") if user_details else None
    
    return {
        "response": response,
        "error": error,
        "conversation_id": conversation_id,
        "user_email": user_email,
        "messages": final_state.get("messages", []),
        # Data (independent of hops)
        "tool_data": tool_data,  # Individual tool results by tool name
        "docs_data": docs_data,  # Individual docs results by query/topic
        # Loop management
        "hops": hops_array,
        "max_hops": final_state.get("max_hops", 3),
        # Node execution data (state level)
        "draft": final_state.get("draft"),
        "validate": final_state.get("validate"),
        "response_delivery": final_state.get("response_delivery"),
        "escalate": final_state.get("escalate"),
        "finalize": final_state.get("finalize"),
        # Routing
        "next_node": final_state.get("next_node"),
        "escalation_reason": final_state.get("escalation_reason")
    }
