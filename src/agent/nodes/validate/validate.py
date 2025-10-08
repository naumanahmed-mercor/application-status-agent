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
from src.clients.intercom import IntercomClient


def validate_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate the draft response against policy and intent classification.

    Args:
        state: Current state containing the draft response

    Returns:
        Updated state with validation results
    """
    print("🔍 Validate Node: Validating draft response...")
    
    # Initialize validate data using Pydantic model (stored at state level, not in hops)
    validate_data = ValidateData(
        validation_response=None,
        overall_passed=False,
        validation_note_added=False,
        escalation_reason=None,
        next_action="escalate"
    )

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
            timeout=120,
            headers={
                "Content-Type": "application/json",
                "x-api-key": validation_api_key
            }
        )
        
        response.raise_for_status()
        validation_result = response.json()
        
        print(f"✅ Validation response received in {validation_result.get('processing_time_ms', 0):.2f}ms")
        
        # Store raw validation results first
        validate_data.validation_response = validation_result
        
        # Add raw validation results as a note to Intercom conversation
        conversation_id = state.get("conversation_id")
        admin_id = state.get("melvin_admin_id")
        
        if conversation_id and admin_id:
            try:
                intercom_api_key = os.getenv("INTERCOM_API_KEY")
                if not intercom_api_key:
                    raise ValueError("INTERCOM_API_KEY environment variable is required")
                
                intercom_client = IntercomClient(intercom_api_key)
                
                # Always use raw JSON format for the note
                overall_status = "✅ PASSED" if validation_result.get("overall_passed") else "❌ FAILED"
                note_text = f"🔍 Response Validation Results\n\n**Status**: {overall_status}\n\n```json\n{json.dumps(validation_result, indent=2)}\n```"
                
                # Add note to conversation
                intercom_client.add_note(
                    conversation_id=conversation_id,
                    note_body=note_text,
                    admin_id=admin_id
                )
                
                validate_data.validation_note_added = True
                print("✅ Validation results added as note to Intercom conversation")
                
            except Exception as e:
                print(f"⚠️  Failed to add validation note to Intercom: {e}")
                # Continue even if note fails
        
        # Parse validation response for routing logic (only care about overall_passed)
        validation_response = ValidationResponse(**validation_result)
        validate_data.overall_passed = validation_response.overall_passed
        
        # Determine next action based on validation result
        if validation_response.overall_passed:
            validate_data.next_action = "response"
            state["next_node"] = "response"
            print("✅ Validation passed - routing to response node")
        else:
            validate_data.next_action = "escalate"
            state["next_node"] = "escalate"
            
            # Simple escalation reason
            escalation_reason = "Validation failed - see validation note for details"
            validate_data.escalation_reason = escalation_reason
            state["escalation_reason"] = escalation_reason
            
            print(f"❌ Validation failed - escalating")

    except Exception as e:
        error_msg = f"Validation error: {str(e)}"
        print(f"❌ {error_msg}")
        validate_data.escalation_reason = error_msg
        validate_data.next_action = "escalate"
        state["error"] = error_msg
        state["next_node"] = "escalate"
        state["escalation_reason"] = error_msg

    # Store validate data at state level (convert to dict for state)
    state["validate"] = validate_data.model_dump()
    
    print(f"🎯 Validate node completed - next action: {validate_data.next_action}")
    
    return state
