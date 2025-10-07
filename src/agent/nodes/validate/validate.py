"""
Validate node for response validation.

This node sends the draft response to a validation endpoint and:
1. Adds validation results as a note to the Intercom conversation
2. Escalates if validation fails (overall_passed = false)
3. Routes to response node if validation passes
"""

import os
import json
import requests
from typing import Dict, Any
from .schemas import ValidationResponse, ValidateData
from src.intercom.client import IntercomClient


def validate_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate the draft response against policy and intent classification.

    Args:
        state: Current state containing the draft response

    Returns:
        Updated state with validation results
    """
    print("🔍 Validate Node: Validating draft response...")
    
    # Initialize validate data (stored at state level, not in hops)
    validate_data = {
        "validation_response": None,
        "overall_passed": False,
        "validation_note_added": False,
        "escalation_reason": None,
        "next_action": "escalate"
    }

    try:
        # Get the draft response
        response_text = state.get("response", "")
        
        if not response_text:
            raise ValueError("No response text found to validate")

        # Get validation endpoint and API key from environment
        validation_endpoint = os.getenv("VALIDATION_ENDPOINT")
        if not validation_endpoint:
            raise ValueError("VALIDATION_ENDPOINT environment variable is required")
        
        validation_api_key = os.getenv("VALIDATION_API_KEY")
        if not validation_api_key:
            raise ValueError("VALIDATION_API_KEY environment variable is required")

        print(f"📤 Sending response to validation endpoint: {validation_endpoint}")
        
        # Send validation request with x-api-key authentication
        validation_payload = {"reply": response_text}
        
        response = requests.post(
            validation_endpoint,
            json=validation_payload,
            timeout=30,
            headers={
                "Content-Type": "application/json",
                "x-api-key": validation_api_key
            }
        )
        
        response.raise_for_status()
        validation_result = response.json()
        
        print(f"✅ Validation response received in {validation_result.get('processing_time_ms', 0):.2f}ms")
        
        # Parse validation response
        validation_response = ValidationResponse(**validation_result)
        
        # Store validation results
        validate_data["validation_response"] = validation_result
        validate_data["overall_passed"] = validation_response.overall_passed
        
        # Add validation results as a note to Intercom conversation
        conversation_id = state.get("conversation_id")
        admin_id = state.get("melvin_admin_id")
        
        if conversation_id and admin_id:
            try:
                intercom_api_key = os.getenv("INTERCOM_API_KEY")
                if not intercom_api_key:
                    raise ValueError("INTERCOM_API_KEY environment variable is required")
                
                intercom_client = IntercomClient(intercom_api_key)
                
                # Format validation note
                note_text = _format_validation_note(validation_response)
                
                # Add note to conversation
                intercom_client.add_note(
                    conversation_id=conversation_id,
                    note_body=note_text,
                    admin_id=admin_id
                )
                
                validate_data["validation_note_added"] = True
                print("✅ Validation results added as note to Intercom conversation")
                
            except Exception as e:
                print(f"⚠️  Failed to add validation note to Intercom: {e}")
                # Continue even if note fails
        
        # Determine next action based on validation result
        if validation_response.overall_passed:
            validate_data["next_action"] = "response"
            state["next_node"] = "response"
            print("✅ Validation passed - routing to response node")
        else:
            validate_data["next_action"] = "escalate"
            state["next_node"] = "escalate"
            
            # Build escalation reason
            escalation_reason = "Validation failed: "
            
            if not validation_response.policy_validation.passed:
                violations = validation_response.policy_validation.violations
                blocked_intents = validation_response.policy_validation.blocked_intents
                escalation_reason += f"Policy violations: {', '.join(violations)}. "
                if blocked_intents:
                    escalation_reason += f"Blocked intents: {', '.join(blocked_intents)}. "
            else:
                escalation_reason += "Overall validation check failed."
            
            validate_data["escalation_reason"] = escalation_reason
            state["escalation_reason"] = escalation_reason
            
            print(f"❌ Validation failed - escalating: {escalation_reason}")

    except Exception as e:
        print(f"❌ Validation error: {e}")
        validate_data["escalation_reason"] = f"Validation error: {str(e)}"
        validate_data["next_action"] = "escalate"
        state["next_node"] = "escalate"
        state["escalation_reason"] = f"Validation error: {str(e)}"

    # Store validate data at state level (not in hops)
    state["validate"] = validate_data
    
    print(f"🎯 Validate node completed - next action: {validate_data['next_action']}")
    
    return state


def _format_validation_note(validation_response: ValidationResponse) -> str:
    """
    Format validation results as a note for Intercom.

    Args:
        validation_response: Validation response from endpoint

    Returns:
        Formatted note text
    """
    note_lines = [
        "🔍 Response Validation Results",
        "",
        f"**Overall Status**: {'✅ PASSED' if validation_response.overall_passed else '❌ FAILED'}",
        f"**Processing Time**: {validation_response.processing_time_ms:.2f}ms",
        ""
    ]
    
    # Add classification results
    if validation_response.classification.hits:
        note_lines.append("**Intent Classification**:")
        for hit in validation_response.classification.hits:
            status = "✅" if hit.confirmed else "⚠️"
            note_lines.append(
                f"- {status} {hit.intent_id} (confidence: {hit.confidence:.2f}) - \"{hit.evidence}\""
            )
        note_lines.append("")
    
    # Add policy validation results
    note_lines.append(
        f"**Policy Validation**: {'✅ PASSED' if validation_response.policy_validation.passed else '❌ FAILED'}"
    )
    
    if validation_response.policy_validation.violations:
        note_lines.append("**Violations**:")
        for violation in validation_response.policy_validation.violations:
            note_lines.append(f"- {violation}")
        note_lines.append("")
    
    if validation_response.policy_validation.blocked_intents:
        note_lines.append("**Blocked Intents**:")
        for intent in validation_response.policy_validation.blocked_intents:
            note_lines.append(f"- {intent}")
        note_lines.append("")
    
    # Add response text
    note_lines.append("**Response Text**:")
    note_lines.append(validation_response.response_text)
    
    return "\n".join(note_lines)
