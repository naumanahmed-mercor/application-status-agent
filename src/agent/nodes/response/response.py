"""
Response node for delivering agent responses via Intercom API.
"""

import os
import time
from typing import Dict, Any
from .schemas import ResponseData
from src.clients.intercom import IntercomClient


def response_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Response node that delivers the agent's response via Intercom API.
    
    Args:
        state: Current state containing response and Intercom configuration
        
    Returns:
        Updated state with delivery status
    """
    print("📤 Response Node: Delivering response via Intercom...")
    
    start_time = time.time()
    
    # Initialize response data using Pydantic model
    response_data = ResponseData(
        success=False,
        intercom_delivered=False,
        error=None,
        delivery_time_ms=None
    )
    
    try:
        # Extract response from state
        response_text = state.get("response", "")
        conversation_id = state.get("conversation_id")
        admin_id = state.get("melvin_admin_id")
        
        if not response_text:
            raise ValueError("No response text to send")
        
        if not conversation_id or not admin_id:
            raise ValueError("Missing conversation_id or melvin_admin_id")
        
        # Initialize Intercom client
        intercom_api_key = os.getenv("INTERCOM_API_KEY")
        if not intercom_api_key:
            raise ValueError("INTERCOM_API_KEY environment variable is required")
        
        intercom_client = IntercomClient(intercom_api_key)
        
        # Send message to conversation
        print(f"📨 Sending message to conversation {conversation_id}")
        
        result = intercom_client.send_message(
            conversation_id=conversation_id,
            message_body=response_text,
            admin_id=admin_id
        )
        
        if result:
            response_data.success = True
            response_data.intercom_delivered = True
            response_data.delivery_time_ms = (time.time() - start_time) * 1000
            print(f"✅ Message sent successfully ({response_data.delivery_time_ms:.1f}ms)")
        else:
            raise ValueError("Failed to send message (no result returned)")
    
    except Exception as e:
        error_msg = f"Failed to deliver response: {str(e)}"
        print(f"❌ {error_msg}")
        response_data.success = False
        response_data.intercom_delivered = False
        response_data.error = error_msg
        response_data.delivery_time_ms = (time.time() - start_time) * 1000
        
        # Set escalation fields
        state["error"] = error_msg
        state["escalation_reason"] = error_msg
        state["next_node"] = "escalate"
    
    # Store response data at state level (convert to dict for state)
    state["response_delivery"] = response_data.model_dump()
    
    # Check if draft requested escalation after response (e.g., ROUTE_TO_TEAM)
    draft_data = state.get("draft", {})
    should_escalate = draft_data.get("response_type") == "ROUTE_TO_TEAM"
    
    # Determine routing
    if "next_node" in state and state["next_node"] == "escalate":
        # Already set to escalate (e.g., from an error)
        pass
    elif should_escalate and response_data.intercom_delivered:
        # Successfully sent message, now escalate as planned (ROUTE_TO_TEAM)
        state["next_node"] = "escalate"
        print(f"🔀 Message sent successfully, now routing to escalate")
    elif not response_data.intercom_delivered:
        # Failed to send - escalate with error
        state["next_node"] = "escalate"
    else:
        # Normal flow - go to finalize
        state["next_node"] = "finalize"
    
    print(f"🎯 Response node completed - delivery: {'✅ success' if response_data.intercom_delivered else '❌ failed'}")
    
    return state
