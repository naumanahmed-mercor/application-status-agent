"""
Initialize node for setting up conversation data and available tools.
"""

import os
import time
from typing import Dict, Any
from ts_agent.types import State, ToolType
from src.clients.intercom import IntercomClient
from src.mcp.factory import create_mcp_client
from .schemas import InitializeData


def initialize_node(state: State) -> State:
    """
    Initialize the state by fetching conversation data from Intercom and MCP tools.
    
    Args:
        state: Current state with conversation_id
        
    Returns:
        Updated state with conversation data and available tools
    """
    # Get conversation ID and Melvin admin ID FIRST (before any potential failures)
    conversation_id = state.get("conversation_id")
    if not conversation_id:
        state["error"] = "conversation_id is required"
        initialize_data = InitializeData(
            conversation_id="",
            messages_count=0,
            user_name=None,
            user_email=None,
            subject=None,
            tools_count=0,
            melvin_admin_id="",
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            success=False,
            error="conversation_id is required"
        )
        state["initialize"] = initialize_data.model_dump()
        return state
    
    # Set conversation_id in state immediately
    state["conversation_id"] = conversation_id
    
    # Get Melvin admin ID and set it in state immediately
    melvin_admin_id = os.getenv("MELVIN_ADMIN_ID")
    if melvin_admin_id:
        state["melvin_admin_id"] = melvin_admin_id
    
    # Only initialize if not already done
    if "available_tools" not in state or state["available_tools"] is None:
        try:
            
            print(f"📞 Fetching conversation data from Intercom: {conversation_id}")
            
            # Initialize Intercom client
            intercom_api_key = os.getenv("INTERCOM_API_KEY")
            if not intercom_api_key:
                raise ValueError("INTERCOM_API_KEY environment variable is required")
            
            intercom_client = IntercomClient(intercom_api_key)
            
            # Fetch conversation data (messages + email)
            conversation_data = intercom_client.get_conversation_data_for_agent(conversation_id)
            
            # Validate: Either messages or subject must be present
            has_messages = conversation_data.get("messages") and len(conversation_data["messages"]) > 0
            has_subject = conversation_data.get("subject") and conversation_data["subject"].strip()
            
            if not has_messages and not has_subject:
                raise ValueError(f"No messages or subject found in conversation {conversation_id}")
            
            # Update state with conversation data
            state["messages"] = conversation_data.get("messages", [])
            state["user_details"] = {
                "name": conversation_data.get("user_name"),
                "email": conversation_data.get("user_email")
            }
            state["subject"] = conversation_data.get("subject") or ""  # Default to empty string if None
            
            print(f"✅ Using {len(state['messages'])} message(s) from Intercom")
            print(f"✅ User name: {conversation_data.get('user_name', 'Not found')}")
            print(f"✅ User email: {conversation_data.get('user_email', 'Not found')}")
            print(f"✅ Subject: {conversation_data.get('subject', 'None')}")
            print(f"✅ Melvin admin ID: {melvin_admin_id}")
            
            # Initialize MCP client
            print("🔌 Initializing MCP client...")
            mcp_client = create_mcp_client()
            
            # Fetch available tools from MCP server
            print("🔧 Fetching available tools from MCP server...")
            available_tools = mcp_client.list_tools()
            print(f"✅ Found {len(available_tools)} available tools")
            
            # Assign tool types to each tool
            # Currently, the MCP server doesn't return tool types yet, so we assign them manually
            for tool in available_tools:
                tool_name = tool.get("name", "")
                if tool_name == "match_and_link_conversation_to_ticket":
                    tool["tool_type"] = ToolType.INTERNAL_ACTION.value
                else:
                    tool["tool_type"] = ToolType.GATHER.value
            
            print(f"🏷️  Assigned tool types:")
            for tool in available_tools:
                print(f"   {tool.get('name')}: {tool.get('tool_type')}")
            
            # Initialize state with proper values (NO MCP client in state)
            state["available_tools"] = available_tools
            state["tool_data"] = state.get("tool_data", {})
            state["docs_data"] = state.get("docs_data", {})
            state["hops"] = state.get("hops", [])
            state["max_hops"] = state.get("max_hops", 3)
            state["actions"] = state.get("actions", [])
            state["max_actions"] = state.get("max_actions", 1)
            state["actions_taken"] = state.get("actions_taken", 0)
            state["response"] = state.get("response", "")
            state["error"] = state.get("error", None)
            state["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%SZ")
            
            # Store initialize data using Pydantic model
            initialize_data = InitializeData(
                conversation_id=conversation_id,
                messages_count=len(state["messages"]),
                user_name=conversation_data.get("user_name"),
                user_email=conversation_data.get("user_email"),
                subject=conversation_data.get("subject"),
                tools_count=len(available_tools),
                melvin_admin_id=melvin_admin_id,
                timestamp=state["timestamp"],
                success=True,
                error=None
            )
            state["initialize"] = initialize_data.model_dump()
            
        except Exception as e:
            print(f"❌ Failed to initialize: {e}")
            error_msg = f"Initialization failed: {str(e)}"
            state["error"] = error_msg
            state["escalation_reason"] = error_msg
            state["response"] = "Sorry, I'm unable to connect to the required services right now."
            
            # Store error in initialize data
            initialize_data = InitializeData(
                conversation_id=state.get("conversation_id", ""),
                messages_count=0,
                user_name=None,
                user_email=None,
                subject=None,
                tools_count=0,
                melvin_admin_id="",
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                success=False,
                error=error_msg
            )
            state["initialize"] = initialize_data.model_dump()
    
    return state

