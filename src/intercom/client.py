"""
Intercom API client for the application status agent.
"""

import re
import requests
import time
import random
import logging
from enum import Enum
from typing import Dict, Any, Optional, List, Union

# Configure logging
logger = logging.getLogger(__name__)


class MelvinResponseStatus(Enum):
    """Statuses for Melvin response processing, stored in Intercom custom attributes."""

    SUCCESS = "success"
    RESPONSE_FAILED = "response_failed"
    VALIDATION_FAILED = "validation_failed"
    MESSAGE_FAILED = "message_failed"
    ROUTE_TO_TEAM = "route_to_team"
    ERROR = "error"


class IntercomClient:
    """
    Client for Intercom API operations.
    
    Provides methods to interact with Intercom conversations:
    - get_conversation: Retrieve conversation details
    - add_note: Add an internal note to a conversation
    - send_message: Send a message to a conversation
    - snooze_conversation: Snooze a conversation
    """

    # API Configuration
    BASE_URL = "https://api.intercom.io"
    API_VERSION = "2.14"
    TIMEOUT_SECONDS = 30

    def __init__(self, api_key: str):
        """
        Initialize the Intercom client.

        Args:
            api_key: Intercom API key for authentication
        """
        self.api_key = api_key
        
        if not self.api_key:
            logger.warning("IntercomClient: No API key provided")

    def _get_headers(self, api_version: Optional[str] = None) -> Dict[str, str]:
        """Get headers for API requests."""
        return {
            "Intercom-Version": api_version or self.API_VERSION,
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        api_version: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Make a request to the Intercom API with retry logic for 429 rate limit errors.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (without base URL)
            params: Query parameters
            json_data: JSON payload for POST requests
            api_version: Override API version
            timeout_seconds: Override timeout

        Returns:
            Response JSON data or None if request failed
        """
        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"
        headers = self._get_headers(api_version)

        max_retries = 3
        base_delay = 1.0  # Base delay in seconds

        for attempt in range(max_retries + 1):
            try:
                response = requests.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    json=json_data,
                    timeout=timeout_seconds or self.TIMEOUT_SECONDS,
                )
                response.raise_for_status()
                return response.json()

            except requests.exceptions.RequestException as e:
                status_code = None
                if hasattr(e, "response") and e.response:
                    status_code = getattr(e.response, "status_code", None)

                # Check for 429 rate limit error
                is_429_error = status_code == 429 or "429" in str(e) or "Too Many Requests" in str(e)

                # Retry on 429 (Too Many Requests)
                if is_429_error and attempt < max_retries:
                    # Exponential backoff with jitter
                    delay = base_delay * (2**attempt) + random.uniform(0, 1)
                    logger.warning(
                        f"IntercomClient: Rate limit error on attempt {attempt + 1}/{max_retries + 1} "
                        f"for {method} {endpoint}. Retrying in {delay:.2f} seconds..."
                    )
                    time.sleep(delay)
                    continue

                # Log error
                try:
                    error_body = e.response.json() if hasattr(e, "response") and e.response else "No response body"
                    logger.error(
                        f"IntercomClient: API request failed - {method} {endpoint}: {str(e)}. "
                        f"Status: {status_code}. Response: {error_body}"
                    )
                except Exception:
                    logger.error(
                        f"IntercomClient: API request failed - {method} {endpoint}: {str(e)}. "
                        f"Status: {status_code}"
                    )
                return None

        return None

    def get_conversation(self, conversation_id: str, display_as: str = "plaintext") -> Optional[Dict[str, Any]]:
        """
        Get a conversation by ID.

        Args:
            conversation_id: The conversation ID
            display_as: How to display the conversation (default: "plaintext")

        Returns:
            Conversation data or None if not found
        """
        params = {"display_as": display_as} if display_as else None
        return self._make_request("GET", f"conversations/{conversation_id}", params=params)

    def get_conversation_data_for_agent(self, conversation_id: str) -> Dict[str, Any]:
        """
        Retrieve all necessary conversation data for the agent in a single call.
        
        This method fetches the conversation once and extracts both the messages
        and user email, optimizing for performance.

        Args:
            conversation_id: The ID of the conversation

        Returns:
            Dictionary containing:
            - messages: List of messages in agent format [{"role": "user|assistant", "content": "..."}]
            - user_email: User's email address (or None if not found)
            - conversation_id: The conversation ID (for reference)
            
        Example:
            {
                "messages": [
                    {"role": "user", "content": "I want to withdraw my application"},
                    {"role": "assistant", "content": "I can help with that..."}
                ],
                "user_email": "user@example.com",
                "conversation_id": "12345"
            }
        """
        result = {
            "messages": [],
            "user_email": None,
            "conversation_id": conversation_id
        }

        # Fetch the conversation details (single API call)
        conversation = self.get_conversation(conversation_id)
        
        if not conversation:
            logger.error(f"Failed to retrieve conversation {conversation_id}")
            return result

        # Extract messages
        messages = []

        # Extract the initial message (source) of the conversation
        source = conversation.get("source", {})
        if source and source.get("body"):
            # Determine role based on author type
            author = source.get("author", {})
            author_type = author.get("type", "user")
            
            # Map Intercom author types to our agent roles
            role = "assistant" if author_type == "admin" else "user"
            
            messages.append({
                "role": role,
                "content": source.get("body", "")
            })

        # Extract conversation parts (subsequent messages)
        conversation_parts = conversation.get("conversation_parts", {}).get("conversation_parts", [])
        for part in conversation_parts:
            body = part.get("body")
            part_type = part.get("part_type", "")
            
            # Only include actual messages (comment), skip notes and system events
            # Notes are internal and should not be part of the conversation
            if body and part_type == "comment":
                # Determine role based on author type
                author = part.get("author", {})
                author_type = author.get("type", "user")
                
                # Map Intercom author types to our agent roles
                role = "assistant" if author_type == "admin" else "user"
                
                messages.append({
                    "role": role,
                    "content": body
                })

        result["messages"] = messages

        # Extract user email
        contacts = conversation.get("contacts", {}).get("contacts", [])
        
        if contacts:
            contact_id = contacts[0].get("id")
            
            if contact_id:
                # Fetch the contact details to get the email
                contact = self._make_request("GET", f"contacts/{contact_id}")
                
                if contact:
                    email = contact.get("email")
                    if email:
                        result["user_email"] = email
                    else:
                        logger.warning(f"No email found for contact {contact_id} in conversation {conversation_id}")
                else:
                    logger.error(f"Failed to retrieve contact {contact_id}")
            else:
                logger.error(f"No contact ID found in conversation {conversation_id}")
        else:
            logger.error(f"No contacts found in conversation {conversation_id}")

        return result

    def add_note(
        self,
        conversation_id: str,
        note_body: str,
        admin_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Add an internal note to a conversation.
        
        Notes are only visible to admins/team members, not to the user.

        Args:
            conversation_id: The ID of the conversation
            note_body: The note content (supports Unicode and newlines)
            admin_id: Admin ID performing the action (required)

        Returns:
            Response data from Intercom API or None if request failed
        """
        payload = {
            "message_type": "note",
            "type": "admin",
            "body": note_body,
            "admin_id": admin_id,
        }

        return self._make_request(
            "POST",
            f"conversations/{conversation_id}/reply",
            json_data=payload,
        )

    def send_message(
        self,
        conversation_id: str,
        message_body: str,
        admin_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Send a message to a conversation (visible to the user).

        This method properly handles Unicode characters and newline characters.

        Args:
            conversation_id: The ID of the conversation
            message_body: The message content (supports Unicode and newlines)
            admin_id: Admin ID performing the action (required)

        Returns:
            Response data from Intercom API or None if request failed

        Example:
            client.send_message(
                "12345",
                "Hello,\\n\\nThanks for reaching out!\\n\\nBest regards",
                "admin_123"
            )
        """
        payload = {
            "message_type": "comment",
            "type": "admin",
            "body": message_body,
            "admin_id": admin_id,
        }

        return self._make_request(
            "POST",
            f"conversations/{conversation_id}/reply",
            json_data=payload,
        )

    def snooze_conversation(
        self,
        conversation_id: str,
        snooze_until: int,
        admin_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Snooze a conversation until a specific time.

        Args:
            conversation_id: The ID of the conversation
            snooze_until: Unix timestamp for when to unsnooze
            admin_id: Admin ID performing the action (required)

        Returns:
            Response data from Intercom API or None if request failed

        Example:
            import time
            # Snooze for 1 hour
            snooze_until = int(time.time()) + 3600
            client.snooze_conversation("12345", snooze_until, "admin_123")
        """
        payload = {
            "message_type": "snoozed",
            "type": "admin",
            "snoozed_until": snooze_until,
            "admin_id": admin_id,
        }

        return self._make_request(
            "POST",
            f"conversations/{conversation_id}/parts",
            json_data=payload,
        )

    def update_conversation_custom_attribute(
        self,
        conversation_id: str,
        attribute_name: str,
        attribute_value: Union[str, bool, int, float]
    ) -> Optional[Dict[str, Any]]:
        """
        Update a custom attribute on a conversation.

        Args:
            conversation_id: The conversation ID
            attribute_name: Name of the custom attribute
            attribute_value: Value to set for the attribute

        Returns:
            API response or None if failed

        Raises:
            ValueError: If attribute_name is invalid or conversation doesn't exist

        Example:
            client.update_conversation_custom_attribute(
                "12345",
                "agent_status",
                "escalated"
            )
        """
        if not conversation_id:
            raise ValueError("conversation_id is required")

        if not attribute_name:
            raise ValueError("attribute_name is required")

        # Validate attribute name format (allow alphanumeric, underscores, brackets, spaces, and hyphens)
        if not re.match(r"^[a-zA-Z0-9_\[\] -]+$", attribute_name):
            raise ValueError(f"Invalid attribute name '{attribute_name}'. Contains invalid characters.")

        # First, get the conversation to check if it exists and get current custom attributes
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found")

        # Check if conversation is in a state that allows updates
        conversation_state = conversation.get("state", "unknown")
        if conversation_state not in ["open", "closed"]:
            logger.warning(
                f"Conversation {conversation_id} is in state '{conversation_state}', "
                f"may not allow custom attribute updates"
            )

        # Check if the attribute already exists
        current_attributes = conversation.get("custom_attributes", {})
        if attribute_name not in current_attributes:
            logger.info(f"Adding new custom attribute '{attribute_name}' to conversation {conversation_id}")
        else:
            logger.info(f"Updating existing custom attribute '{attribute_name}' on conversation {conversation_id}")

        # Prepare the update payload - only pass the specific attribute we want to update
        payload = {"custom_attributes": {attribute_name: attribute_value}}

        # Make the update request
        result = self._make_request("PUT", f"conversations/{conversation_id}", json_data=payload)

        if result:
            logger.info(
                f"Successfully updated custom attribute '{attribute_name}' on conversation {conversation_id}"
            )
        else:
            logger.error(
                f"Failed to update custom attribute '{attribute_name}' on conversation {conversation_id}"
            )

        return result
