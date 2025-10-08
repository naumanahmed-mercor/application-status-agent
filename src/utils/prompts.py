"""
Utility functions for formatting prompts with conversation history and user details.
"""

from typing import List, Dict, Any, Optional


def format_conversation_history(messages: List[Dict[str, Any]], subject: Optional[str] = None) -> str:
    """
    Format conversation history for LLM prompts.
    
    Args:
        messages: List of conversation messages with role and content
        subject: Optional conversation subject/title
        
    Returns:
        Formatted conversation history string
    """
    parts = []
    
    # Add subject if available
    if subject:
        parts.append(f"Subject: {subject}\n")
    
    # Add messages
    if messages:
        parts.append("Conversation:")
        for i, message in enumerate(messages, 1):
            role = message.get("role", "unknown").title()
            content = message.get("content", "")
            parts.append(f"{i}. {role}: {content}")
    else:
        parts.append("Conversation: No messages available")
    
    return "\n".join(parts)


def format_user_details(name: Optional[str] = None, email: Optional[str] = None) -> str:
    """
    Format user details for LLM prompts.
    
    Args:
        name: User's name
        email: User's email
        
    Returns:
        Formatted user details string
    """
    parts = []
    
    if name:
        parts.append(f"Name: {name}")
    
    if email:
        parts.append(f"Email: {email}")
    
    if not parts:
        parts.append("User details: Not available")
    
    return "\n".join(parts)


def build_conversation_and_user_context(state: Dict[str, Any]) -> Dict[str, str]:
    """
    Build formatted conversation history and user details from state.
    
    Args:
        state: Agent state containing messages, subject, and user_details
        
    Returns:
        Dictionary with formatted conversation_history and user_details strings
        
    Raises:
        ValueError: If both messages and subject are missing from state
    """
    messages = state.get("messages", [])
    subject = state.get("subject")
    
    # Validate: Either messages or subject must be present
    has_messages = messages and len(messages) > 0
    has_subject = subject and subject.strip()
    
    if not has_messages and not has_subject:
        raise ValueError("No conversation messages or subject found in state")
    
    user_details = state.get("user_details", {})
    user_name = user_details.get("name") if user_details else None
    user_email = user_details.get("email") if user_details else None
    
    return {
        "conversation_history": format_conversation_history(messages, subject),
        "user_details": format_user_details(user_name, user_email)
    }
