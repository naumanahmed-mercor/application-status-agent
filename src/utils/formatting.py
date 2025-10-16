"""Formatting utilities for structured data display."""

import json
from typing import Any, Dict, List


def format_nested_data(data: Any, indent: int = 0, max_depth: int = 10) -> str:
    """
    Recursively format nested data structures (dicts, lists, etc.) into readable text.
    
    This is useful for creating human-readable audit trails, notes, or reports
    from structured data like JSON responses from tools.
    
    Args:
        data: The data to format (can be dict, list, str, int, bool, etc.)
        indent: Current indentation level (internal use for recursion)
        max_depth: Maximum recursion depth to prevent infinite loops
        
    Returns:
        Formatted string with proper indentation and line breaks
        
    Examples:
        >>> data = {"status": "success", "ticket": {"id": "ABC-123", "url": "..."}}
        >>> print(format_nested_data(data))
        Status: success
        Ticket:
          ID: ABC-123
          URL: ...
    """
    if max_depth <= 0:
        return "... (max depth reached)"
    
    indent_str = "  " * indent
    
    # Handle None
    if data is None:
        return "None"
    
    # Handle booleans
    if isinstance(data, bool):
        return "✅ Yes" if data else "❌ No"
    
    # Handle numbers
    if isinstance(data, (int, float)):
        return str(data)
    
    # Handle strings
    if isinstance(data, str):
        # Truncate very long strings
        if len(data) > 500:
            return f"{data[:500]}... (truncated)"
        return data
    
    # Handle lists
    if isinstance(data, list):
        if not data:
            return "(empty list)"
        
        lines = []
        for i, item in enumerate(data, 1):
            if isinstance(item, (dict, list)):
                lines.append(f"{indent_str}{i}.")
                formatted_item = format_nested_data(item, indent + 1, max_depth - 1)
                lines.append(formatted_item)
            else:
                formatted_item = format_nested_data(item, 0, max_depth - 1)
                lines.append(f"{indent_str}{i}. {formatted_item}")
        return "\n".join(lines)
    
    # Handle dictionaries
    if isinstance(data, dict):
        if not data:
            return "(empty)"
        
        lines = []
        for key, value in data.items():
            # Format the key (title case, replace underscores)
            formatted_key = key.replace("_", " ").title()
            
            # Handle nested structures
            if isinstance(value, (dict, list)):
                lines.append(f"{indent_str}{formatted_key}:")
                formatted_value = format_nested_data(value, indent + 1, max_depth - 1)
                lines.append(formatted_value)
            else:
                formatted_value = format_nested_data(value, 0, max_depth - 1)
                lines.append(f"{indent_str}{formatted_key}: {formatted_value}")
        
        return "\n".join(lines)
    
    # Fallback for other types
    return str(data)


def format_action_audit_note(
    action_name: str,
    parameters: Dict[str, Any],
    result: Any,
    execution_time_ms: float,
    success: bool,
    error: str = None
) -> str:
    """
    Format an action tool execution into a clean audit note for Intercom.
    
    Args:
        action_name: Name of the action tool
        parameters: Parameters used for the action
        result: Result data from the action
        execution_time_ms: Execution time in milliseconds
        success: Whether the action succeeded
        error: Error message if failed
        
    Returns:
        Formatted audit note string ready for posting
    """
    lines = []
    
    # Header
    status_emoji = "✅" if success else "❌"
    lines.append(f"🤖 **Melvin Action Executed**")
    lines.append("")
    lines.append(f"{status_emoji} **Status:** {'SUCCESS' if success else 'FAILED'}")
    lines.append(f"**Action:** `{action_name}`")
    lines.append(f"**Execution Time:** {execution_time_ms:.1f}ms")
    lines.append("")
    
    # Parameters
    if parameters:
        lines.append("**Parameters:**")
        formatted_params = format_nested_data(parameters, indent=1)
        lines.append(formatted_params)
        lines.append("")
    
    # Error (if failed)
    if not success and error:
        lines.append("**Error:**")
        lines.append(f"  {error}")
        lines.append("")
    
    # Result (if succeeded)
    if success and result:
        lines.append("**Result:**")
        
        # Try to parse result if it's JSON text
        result_data = result
        if isinstance(result, list) and len(result) > 0:
            # MCP tools return results as [{'type': 'text', 'text': '...'}]
            if isinstance(result[0], dict) and 'text' in result[0]:
                try:
                    result_data = json.loads(result[0]['text'])
                except (json.JSONDecodeError, KeyError):
                    result_data = result[0].get('text', result)
        
        formatted_result = format_nested_data(result_data, indent=1)
        lines.append(formatted_result)
        lines.append("")
    
    # Footer
    lines.append("---")
    lines.append("_This action was executed automatically by Melvin and logged for audit purposes._")
    
    return "\n".join(lines)

