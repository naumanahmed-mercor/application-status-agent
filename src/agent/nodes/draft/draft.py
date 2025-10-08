"""
Draft node implementation.
Generates a response based on accumulated tool data and docs data.
"""

import time
import json
from typing import Dict, Any, List
from agent.llm import drafter_llm
from src.clients.prompts import get_prompt, PROMPT_NAMES
from src.utils.prompts import build_conversation_and_user_context
from .schemas import DraftData, ResponseType


def draft_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a response based on accumulated data.
    
    Args:
        state: Current state containing user query, tool data, and docs data
        
    Returns:
        Updated state with generated response
    """
    print("📝 Draft Node: Generating response...")
    
    # Extract data from state
    tool_data = state.get("tool_data", {})
    docs_data = state.get("docs_data", {})
    
    start_time = time.time()
    
    try:
        # Build formatted conversation history and user details (with validation)
        formatted_context = build_conversation_and_user_context(state)
    except ValueError as e:
        state["error"] = str(e)
        state["next_node"] = "escalate"
        state["escalation_reason"] = str(e)
        return state
    
    try:
        
        # Generate response using LLM
        response = _generate_response(
            formatted_context["conversation_history"],
            formatted_context["user_details"],
            tool_data,
            docs_data
        )
        
        generation_time = (time.time() - start_time) * 1000
        
        # Store draft data at state level using Pydantic model
        draft_data = DraftData(
            response=response["response"],
            response_type=ResponseType(response["response_type"]),
            generation_time_ms=generation_time,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ")
        )
        state["draft"] = draft_data.model_dump()
        
        # Update state with response
        state["response"] = response["response"]
        
        # Route based on response type
        if response["response_type"] == "ROUTE_TO_TEAM":
            state["next_node"] = "escalate"
            state["escalation_reason"] = "User requested to talk to a human"
            print(f"🔀 Response type: ROUTE_TO_TEAM - routing to escalate")
        else:
            state["next_node"] = "validate"
            print(f"✅ Response generated ({generation_time:.1f}ms)")
            print(f"📝 Response: {response['response'][:100]}...")
        
    except Exception as e:
        error_msg = f"Draft generation failed: {str(e)}"
        print(f"❌ {error_msg}")
        
        # Store error in draft data at state level using Pydantic model
        draft_data = DraftData(
            response="",
            response_type=ResponseType.REPLY,
            generation_time_ms=(time.time() - start_time) * 1000,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ")
        )
        state["draft"] = draft_data.model_dump()
        
        state["error"] = error_msg
        state["next_node"] = "escalate"
        state["escalation_reason"] = f"Draft generation error: {str(e)}"
    
    return state


def _generate_response(
    conversation_history: str,
    user_details: str,
    tool_data: Dict[str, Any],
    docs_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generate a response using LLM based on accumulated data.
    
    Args:
        conversation_history: Formatted conversation history string
        user_details: Formatted user details string
        tool_data: Accumulated tool data
        docs_data: Accumulated docs data
        
    Returns:
        Generated response with metadata
    """
    llm = drafter_llm()
    
    # Prepare context data
    context_data = _prepare_context_data(tool_data, docs_data)
    
    # Create system prompt with conversation context and user details
    system_prompt = _create_system_prompt(conversation_history, user_details, context_data)
    
    # Generate response
    response = llm.invoke(system_prompt)
    
    # Extract text content from response
    response_text = response.content if hasattr(response, 'content') else str(response)
    
    # Parse and structure the response
    return _parse_response(response_text, context_data)


def _prepare_context_data(tool_data: Dict[str, Any], docs_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Prepare context data for the LLM prompt.
    
    Args:
        tool_data: Tool execution results
        docs_data: Documentation search results
        
    Returns:
        Formatted context data
    """
    context = {
        "tool_data": tool_data,
        "docs_data": docs_data,
        "sources": [],
        "documentation_content": []
    }
    
    # Extract and parse tool data
    for tool_name, results in tool_data.items():
        if not isinstance(results, list) or len(results) == 0:
            continue
            
        for result in results:
            if not isinstance(result, dict) or "text" not in result:
                continue
                
            try:
                text_content = result["text"]
                if not isinstance(text_content, str):
                    continue
                
                # Try to parse as JSON
                try:
                    parsed = json.loads(text_content)
                    if "applications" in parsed:
                        # This is application data - extract key info
                        apps = parsed["applications"]
                        context["documentation_content"].append({
                            "title": f"{tool_name} - {len(apps)} applications found",
                            "text": f"Found {len(apps)} applications with the following details:",
                            "type": "application_data",
                            "applications": apps
                        })
                    else:
                        # Other tool data
                        context["documentation_content"].append({
                            "title": f"{tool_name} data",
                            "text": text_content,
                            "type": "tool_data"
                        })
                except json.JSONDecodeError:
                    # If not JSON, add as raw text
                    context["documentation_content"].append({
                        "title": f"{tool_name} data",
                        "text": text_content,
                        "type": "raw_text"
                    })
            except Exception:
                continue
    
    # Extract and parse documentation content
    for query, results in docs_data.items():
        if not isinstance(results, list) or len(results) == 0:
            continue
            
        for result in results:
            if not isinstance(result, dict) or "text" not in result:
                continue
                
            try:
                text_content = result["text"]
                if not isinstance(text_content, str):
                    continue
                
                # Try to parse as JSON
                try:
                    parsed = json.loads(text_content)
                    if "results" not in parsed:
                        continue
                        
                    for doc_result in parsed["results"]:
                        if not isinstance(doc_result, dict):
                            continue
                            
                        # Extract the actual content
                        doc_content = {
                            "title": doc_result.get("title", "Unknown"),
                            "heading": doc_result.get("heading", ""),
                            "text": doc_result.get("text", ""),
                            "url": doc_result.get("url", ""),
                            "similarity": doc_result.get("similarity", 0.0)
                        }
                        context["documentation_content"].append(doc_content)
                        
                        # Also add to sources for reference
                        context["sources"].append({
                            "title": doc_content["title"],
                            "url": doc_content["url"],
                            "heading": doc_content["heading"],
                            "similarity": doc_content["similarity"]
                        })
                except json.JSONDecodeError:
                    # If not JSON, add as raw text
                    context["documentation_content"].append({
                        "title": "Raw Content",
                        "text": text_content,
                        "type": "raw_text"
                    })
            except Exception:
                continue
    
    return context


def _create_system_prompt(conversation_history: str, user_details: str, context_data: Dict[str, Any]) -> str:
    """
    Create system prompt for response generation.
    
    Args:
        conversation_history: Formatted conversation history string
        user_details: Formatted user details string
        context_data: Prepared context data
        
    Returns:
        System prompt string
    """
    # Build available data summary
    data_summary = []
    
    if context_data["tool_data"]:
        data_summary.append(f"Tool Data: {len(context_data['tool_data'])} tools executed")
    
    if context_data["docs_data"]:
        data_summary.append(f"Documentation: {len(context_data['docs_data'])} searches performed")
    
    if context_data["sources"]:
        data_summary.append(f"Sources: {len(context_data['sources'])} documents found")
    
    # Format documentation content for the prompt
    docs_content = ""
    if context_data["documentation_content"]:
        docs_content = "\n\nRELEVANT DATA:\n"
        for i, doc in enumerate(context_data["documentation_content"], 1):
            docs_content += f"\n{i}. {doc.get('title', 'Unknown')}"
            if doc.get('heading'):
                docs_content += f" - {doc['heading']}"
            
            # Handle application data specially
            if doc.get('type') == 'application_data' and 'applications' in doc:
                docs_content += f"\n   {doc.get('text', '')}\n"
                for j, app in enumerate(doc['applications'], 1):
                    title = app.get('listing_title', 'Unknown')
                    status = app.get('status', 'Unknown')
                    applied_at = app.get('applied_at', 'Unknown')
                    docs_content += f"   Application {j}: {title} - Status: {status} (Applied: {applied_at})\n"
            else:
                docs_content += f"\n   Content: {doc.get('text', '')}\n"
            
            if doc.get('url'):
                docs_content += f"   Source: {doc['url']}\n"
    
    # Create the prompt
    # Get prompt from LangSmith
    prompt_template = get_prompt(PROMPT_NAMES["DRAFT_NODE"])
    
    # Format the prompt with variables using direct string replacement
    data_summary_text = ', '.join(data_summary) if data_summary else 'No specific data available'
    full_data_summary = data_summary_text + docs_content
    
    # Format the prompt with variables
    prompt = prompt_template.format(
        conversation_history=conversation_history,
        user_details=user_details,
        data_summary=full_data_summary
    )

    return prompt


def _parse_response(response_text: str, context_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse and structure the LLM response.
    LLM returns: {"text": str, "response_type": str}
    We convert to: {"response": str, "response_type": str}
    
    Args:
        response_text: Raw LLM response
        context_data: Context data used for generation
        
    Returns:
        Response in format {"response": str, "response_type": "REPLY" or "ROUTE_TO_TEAM"}
    """
    # Try to parse as JSON first, then fall back to plain text
    try:
        import json
        parsed = json.loads(response_text)
        if isinstance(parsed, dict):
            # LLM uses "text", we convert to "response"
            # Also check for "response" for backwards compatibility
            response = parsed.get("text") or parsed.get("response", response_text)
            
            # Default to "REPLY" if response_type not provided (backwards compatibility)
            response_type = parsed.get("response_type", "REPLY")
            
            # Validate response_type
            if response_type not in ["REPLY", "ROUTE_TO_TEAM"]:
                response_type = "REPLY"
            
            return {
                "response": response,
                "response_type": response_type
            }
        else:
            # If it's JSON but not a dict, wrap it
            return {"response": response_text, "response_type": "REPLY"}
    except (json.JSONDecodeError, TypeError):
        # If it's not JSON, treat as plain text with REPLY type (backwards compatibility)
        return {"response": response_text, "response_type": "REPLY"}
