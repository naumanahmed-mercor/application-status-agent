"""
Finalize node for cleanup actions.

This node handles all final actions before ending the workflow:
- Updates Melvin Status custom attribute on Intercom
- Snoozes the conversation for 5 minutes
"""

import os
import time
from typing import Dict, Any
from .schemas import FinalizeData
from clients.intercom import IntercomClient, MelvinResponseStatus


def finalize_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Finalize the workflow by updating status and snoozing conversation.

    Args:
        state: Current state

    Returns:
        Updated state with finalize data
    """
    print("🏁 Finalize Node: Wrapping up...")

    # Determine Melvin Status based on workflow outcome
    melvin_status = _determine_melvin_status(state)
    
    # Initialize finalize data using Pydantic model
    finalize_data = FinalizeData(
        melvin_status=melvin_status.value,
        status_updated=False,
        conversation_snoozed=False,
        snooze_duration_seconds=300,  # 5 minutes
        error=None
    )

    try:
        # Get required data from state
        conversation_id = state.get("conversation_id")
        admin_id = state.get("melvin_admin_id")

        if not conversation_id or not admin_id:
            print("⚠️  Missing conversation_id or melvin_admin_id, skipping finalization")
            state["finalize"] = finalize_data.model_dump()
            state["next_node"] = "end"
            return state

        # Initialize Intercom client
        intercom_api_key = os.getenv("INTERCOM_API_KEY")
        if not intercom_api_key:
            raise ValueError("INTERCOM_API_KEY environment variable is required")

        intercom_client = IntercomClient(intercom_api_key)

        # Update Melvin Status custom attribute
        try:
            print(f"🔄 Updating Melvin Status to '{melvin_status.value}' for conversation {conversation_id}")
            intercom_client.update_conversation_custom_attribute(
                conversation_id=conversation_id,
                attribute_name="Melvin Status",
                attribute_value=melvin_status.value
            )
            finalize_data.status_updated = True
            print("✅ Melvin Status updated successfully")
        except Exception as status_error:
            print(f"⚠️  Failed to update Melvin Status: {status_error}")
            # Continue even if status update fails

        # Snooze conversation for 5 minutes
        try:
            snooze_until = int(time.time()) + finalize_data.snooze_duration_seconds
            print(f"💤 Snoozing conversation {conversation_id} for 5 minutes")
            intercom_client.snooze_conversation(
                conversation_id=conversation_id,
                snooze_until=snooze_until,
                admin_id=admin_id
            )
            finalize_data.conversation_snoozed = True
            print("✅ Conversation snoozed successfully")
        except Exception as snooze_error:
            print(f"⚠️  Failed to snooze conversation: {snooze_error}")
            # Continue even if snooze fails

    except Exception as e:
        error_msg = f"Finalization error: {str(e)}"
        print(f"❌ {error_msg}")
        finalize_data.error = error_msg

    # Store finalize data at state level (convert to dict for state)
    state["finalize"] = finalize_data.model_dump()
    state["next_node"] = "end"

    print(f"🎯 Finalize completed - status: {melvin_status.value}, snoozed: {finalize_data.conversation_snoozed}")

    return state


def _determine_melvin_status(state: Dict[str, Any]) -> MelvinResponseStatus:
    """
    Determine the appropriate Melvin Status based on workflow outcome.

    Args:
        state: Current state

    Returns:
        Appropriate MelvinResponseStatus enum value
    """
    # Check draft response type first (for ROUTE_TO_TEAM)
    draft_data = state.get("draft")
    if draft_data and draft_data.get("response_type") == "ROUTE_TO_TEAM":
        return MelvinResponseStatus.ROUTE_TO_TEAM
    
    # Check if we have escalate data (escalation occurred)
    escalate_data = state.get("escalate")
    if escalate_data:
        # Escalation occurred - determine status from escalation source
        escalation_source = escalate_data.get("escalation_source", "unknown")
        escalation_reason = state.get("escalation_reason", "")
        
        # Check if user requested to talk to a human
        if "requested to talk to a human" in escalation_reason.lower():
            return MelvinResponseStatus.ROUTE_TO_TEAM
        elif escalation_source == "validate":
            return MelvinResponseStatus.VALIDATION_FAILED
        elif escalation_source == "draft":
            return MelvinResponseStatus.RESPONSE_FAILED
        elif escalation_source == "coverage":
            return MelvinResponseStatus.ROUTE_TO_TEAM
        elif escalation_source == "initialization":
            return MelvinResponseStatus.ERROR
        else:
            return MelvinResponseStatus.ERROR
    
    # Check if response was delivered successfully
    response_delivery = state.get("response_delivery")
    if response_delivery:
        if response_delivery.get("intercom_delivered"):
            return MelvinResponseStatus.SUCCESS
        else:
            return MelvinResponseStatus.MESSAGE_FAILED
    
    # Default to error if we can't determine status
    return MelvinResponseStatus.ERROR
