"""
Draft node implementation.
Generates a response based on accumulated tool data and docs data.
"""

import time
import json
from typing import Dict, Any, List
from agent.llm import drafter_llm
from agent.prompts import get_prompt, PROMPT_NAMES


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
    # Get conversation context
    messages = state.get("messages", [])
    
    # Get the latest user message as the primary query
    latest_user_message = ""
    for message in reversed(messages):
        if message["role"] == "user":
            latest_user_message = message["content"]
            break
    user_email = state.get("user_email")
    tool_data = state.get("tool_data", {})
    docs_data = state.get("docs_data", {})
    
    start_time = time.time()
    
    try:
        # Generate response using LLM
        response = _generate_response(latest_user_message, tool_data, docs_data, user_email, messages)
        
        generation_time = (time.time() - start_time) * 1000
        
        # Store draft data at state level (not in hops)
        state["draft"] = {
            "response": response["text"],
            "generation_time_ms": generation_time,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ")
        }
        
        # Update state with response
        state["response"] = response["text"]
        state["next_node"] = "validate"  # Draft goes to validate node
        
        print(f"✅ Response generated ({generation_time:.1f}ms)")
        print(f"📝 Response: {response['text'][:100]}...")
        
    except Exception as e:
        error_msg = f"Draft generation failed: {str(e)}"
        print(f"❌ {error_msg}")
        
        # Store error in draft data at state level
        state["draft"] = {
            "response": "",
            "generation_time_ms": (time.time() - start_time) * 1000,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "error": error_msg
        }
        
        state["error"] = error_msg
        state["next_node"] = "end"
    
    return state


def _generate_response(user_query: str, tool_data: Dict[str, Any], docs_data: Dict[str, Any], user_email: str = None, conversation_history: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Generate a response using LLM based on accumulated data.
    
    Args:
        user_query: Original user query
        tool_data: Accumulated tool data
        docs_data: Accumulated docs data
        user_email: User email if available
        
    Returns:
        Generated response with metadata
    """
    llm = drafter_llm()
    
    # Prepare context data
    context_data = _prepare_context_data(tool_data, docs_data)
    
    # Create system prompt with conversation context
    system_prompt = _create_system_prompt(user_query, context_data, user_email, conversation_history)
    
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
        if isinstance(results, list) and len(results) > 0:
            for result in results:
                if isinstance(result, dict) and "text" in result:
                    try:
                        text_content = result["text"]
                        if isinstance(text_content, str):
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
        if isinstance(results, list) and len(results) > 0:
            for result in results:
                if isinstance(result, dict) and "text" in result:
                    try:
                        text_content = result["text"]
                        if isinstance(text_content, str):
                            # Try to parse as JSON
                            try:
                                parsed = json.loads(text_content)
                                if "results" in parsed:
                                    for doc_result in parsed["results"]:
                                        if isinstance(doc_result, dict):
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


def _create_system_prompt(user_query: str, context_data: Dict[str, Any], user_email: str = None, conversation_history: List[Dict[str, Any]] = None) -> str:
    """
    Create system prompt for response generation.
    
    Args:
        user_query: Original user query
        context_data: Prepared context data
        user_email: User email if available
        
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
    
    # Format conversation history for context
    conversation_context = ""
    if conversation_history:
        conversation_context = "\n\nCONVERSATION HISTORY:\n"
        for i, message in enumerate(conversation_history):
            role = message.get("role", "unknown")
            content = message.get("content", "")
            conversation_context += f"{i+1}. {role.title()}: {content}\n"
    
    # Create the prompt
    # Get prompt from LangSmith
    prompt_template = get_prompt(PROMPT_NAMES["DRAFT_NODE"])
    
    # Format the prompt with variables using direct string replacement
    data_summary_text = ', '.join(data_summary) if data_summary else 'No specific data available'
    full_data_summary = data_summary_text + docs_content + conversation_context
    
    # Replace variables directly to avoid issues with JSON examples
    prompt = prompt_template.replace('{{user_query}}', user_query).replace('{{data_summary}}', full_data_summary)

    return prompt


def _parse_response(response_text: str, context_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse and structure the LLM response.
    Returns response in format: {"text": str}
    
    Args:
        response_text: Raw LLM response
        context_data: Context data used for generation
        
    Returns:
        Response in format {"text": str}
    """
    # Try to parse as JSON first, then fall back to plain text
    try:
        import json
        parsed = json.loads(response_text)
        if isinstance(parsed, dict) and "text" in parsed:
            return parsed
        else:
            # If it's JSON but not in expected format, wrap it
            return {"text": response_text}
    except (json.JSONDecodeError, TypeError):
        # If it's not JSON, treat as plain text
        return {"text": response_text}
