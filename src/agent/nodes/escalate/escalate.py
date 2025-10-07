"""
Escalate node for handling escalations.

This node is called when the agent needs to escalate to a human.
It creates a comprehensive note on the Intercom conversation summarizing:
- The escalation reason
- The source of escalation (coverage, validate, draft, etc.)
- All context gathered during the conversation
- Tools executed and data collected
"""

import os
import time
from typing import Dict, Any, List
from .schemas import EscalateData
from src.intercom import IntercomClient


def escalate_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle escalation by creating a comprehensive note for the team.

    Args:
        state: Current state containing escalation reason and context

    Returns:
        Updated state with escalation data
    """
    print("🚨 Escalate Node: Handling escalation...")

    # Initialize escalate data
    escalate_data = {
        "escalation_reason": state.get("escalation_reason", "Unknown escalation reason"),
        "escalation_source": _determine_escalation_source(state),
        "note_added": False,
        "note_content": None,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "context": {}
    }

    try:
        # Get Intercom configuration
        conversation_id = state.get("conversation_id")
        admin_id = state.get("melvin_admin_id")

        if not conversation_id or not admin_id:
            print("⚠️  Missing conversation_id or melvin_admin_id, skipping Intercom note")
            state["escalate"] = escalate_data
            state["next_node"] = "end"
            return state

        # Initialize Intercom client
        intercom_api_key = os.getenv("INTERCOM_API_KEY")
        if not intercom_api_key:
            raise ValueError("INTERCOM_API_KEY environment variable is required")

        intercom_client = IntercomClient(intercom_api_key)

        # Build escalation note
        note_content = _build_escalation_note(state, escalate_data)
        escalate_data["note_content"] = note_content

        # Add note to Intercom conversation
        print(f"📝 Adding escalation note to conversation {conversation_id}")
        intercom_client.add_note(
            conversation_id=conversation_id,
            note_body=note_content,
            admin_id=admin_id
        )

        escalate_data["note_added"] = True
        print("✅ Escalation note added successfully")

    except Exception as e:
        print(f"❌ Failed to add escalation note: {e}")
        escalate_data["note_added"] = False

    # Store escalate data at state level
    state["escalate"] = escalate_data
    state["next_node"] = "finalize"

    print(f"🎯 Escalation handled - reason: {escalate_data['escalation_reason']}")

    return state


def _determine_escalation_source(state: Dict[str, Any]) -> str:
    """
    Determine which node triggered the escalation.

    Args:
        state: Current state

    Returns:
        Source of escalation
    """
    # Check if validate node failed
    validate_data = state.get("validate", {})
    if validate_data and not validate_data.get("overall_passed", True):
        return "validate"

    # Check if coverage node escalated
    hops = state.get("hops", [])
    if hops:
        last_hop = hops[-1]
        coverage_data = last_hop.get("coverage")
        if coverage_data and coverage_data.get("next_action") == "escalate":
            return "coverage"

    # Check if draft node failed
    draft_data = state.get("draft", {})
    if draft_data and draft_data.get("error"):
        return "draft"

    # Check if initialization failed
    if state.get("error") and not hops:
        return "initialization"

    return "unknown"


def _build_escalation_note(state: Dict[str, Any], escalate_data: Dict[str, Any]) -> str:
    """
    Build a simple escalation note with the reason.

    Args:
        state: Current state with all context
        escalate_data: Escalation data

    Returns:
        Formatted note content
    """
    return f"🚨 Escalation: {escalate_data['escalation_reason']}"
