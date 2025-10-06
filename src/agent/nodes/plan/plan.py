"""Plan node implementation for intelligent tool selection and planning."""

import re
from typing import Dict, Any, List
from agent.types import State
from .schemas import Plan, PlanRequest, PlanResponse
from agent.llm import planner_llm
from agent.prompts import get_prompt, PROMPT_NAMES


def plan_node(state: State) -> State:
    """
    Plan which tools to execute based on user query.
    
    This node analyzes the user's query and creates a plan for which MCP tools
    to execute to best answer their question.
    """
    # Extract conversation context and user email from state
    messages = state.get("messages", [])
    user_email = state.get("user_email")
    
    # Get the latest user message as the primary query
    latest_user_message = ""
    for message in reversed(messages):
        if message["role"] == "user":
            latest_user_message = message["content"]
            break
    
    if not latest_user_message:
        state["error"] = "No user message provided"
        return state
    
    # Get hops array and current hop number
    hops_array = state.get("hops", [])
    current_hop = len(hops_array)  # Current hop is the next one to be added
    
    # Create new hop data structure with nested fields
    hop_data = {
        "hop_number": current_hop + 1,
        "plan": None,
        "gather": None,
        "coverage": None
    }
    
    # Create plan request with available context from previous hops
    context = _build_context_from_hops(hops_array, state)
    
    # Add docs data to context
    docs_data = state.get("docs_data", {})
    if docs_data:
        context["available_docs"] = list(docs_data.keys())
    
    # Add conversation history to context
    context["conversation_history"] = messages
    
    plan_request = PlanRequest(
        user_query=latest_user_message,  # Keep latest message as primary query
        user_email=user_email,
        context=context  # Full conversation history is now in context["conversation_history"]
    )
    
    try:
        # Get available tools from state
        available_tools = state.get("available_tools", [])
        
        # Generate plan using LLM
        plan = _generate_plan(plan_request, available_tools)
        
        # Store plan in nested structure
        hop_data["plan"] = {
            "plan": plan.model_dump(),
            "tool_calls": plan.tool_calls,
            "reasoning": plan.reasoning,
        }
        
        print(f"📋 Plan generated (Hop {current_hop + 1}): {len(plan.tool_calls)} tools to execute")
        for i, tool_call in enumerate(plan.tool_calls, 1):
            print(f"   {i}. {tool_call.get('tool_name', 'Unknown')} - {tool_call.get('reasoning', 'N/A')}")
        
    except Exception as e:
        state["error"] = f"Plan generation failed: {str(e)}"
        print(f"❌ Plan generation error: {e}")
        return state
    
    # Add hop data to hops array
    state["hops"].append(hop_data)
    
    return state


def _generate_plan(request: PlanRequest, available_tools: List[Dict[str, Any]]) -> Plan:
    """
    Generate an execution plan using LLM.
    
    Args:
        request: Plan request with user query and context
        available_tools: List of available tools from MCP server
        
    Returns:
        Generated execution plan
    """
    
    # Create context-aware prompt for LLM
    context_info = _format_context_for_prompt(request.context)
    
    # Format conversation history for the prompt
    conversation_context = _format_conversation_history(request.context.get("conversation_history", []))
    
    # Get prompt from LangSmith
    prompt_template = get_prompt(PROMPT_NAMES["PLAN_NODE"])
    
    # Format the prompt with variables
    prompt = prompt_template.format(
        user_query=request.user_query,
        user_email=request.user_email or "Not provided",
        context_info=context_info,
        conversation_context=conversation_context,
        available_tools=_format_tools_for_prompt(available_tools)
    )
    
    # Get LLM response
    llm = planner_llm()
    response = llm.invoke(prompt)
    
    # Parse JSON response
    try:
        import json
        plan_data = json.loads(response.content)
        
        # Create tool calls as simple dictionaries
        tool_calls = plan_data.get("tool_calls", [])
        
        # Create Plan object
        plan = Plan(
            user_query=plan_data.get("user_query", request.user_query),
            user_email=plan_data.get("user_email"),
            reasoning=plan_data.get("reasoning", "Generated plan"),
            tool_calls=tool_calls
        )
        
        return plan
        
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse LLM response as JSON: {e}")
    except Exception as e:
        raise ValueError(f"Failed to create plan: {e}")


def _format_tools_for_prompt(tools: List[Dict[str, Any]]) -> str:
    """Format tools for LLM prompt."""
    formatted = []
    for tool in tools:
        name = tool.get("name", "unknown")
        description = tool.get("description", "No description available")
        formatted.append(f"- {name}: {description}")
    return "\n".join(formatted)


def _build_context_from_hops(hops_array: List[Dict[str, Any]], state: State) -> Dict[str, Any]:
    """Build context from previous hops for planning."""
    context = {
        "timestamp": state.get("timestamp"),
        "current_hop": state.get("current_hop", 0),
        "max_hops": state.get("max_hops", 2),
        "previous_tools": [],
        "failed_tools": [],
        "coverage_analysis": None,
        "missing_data": [],
        "needs_more_data": False
    }
    
    # Aggregate data from all previous hops
    for hop in hops_array:
        # Get gather data
        gather_data = hop.get("gather", {})
        if gather_data:
            tool_results = gather_data.get("tool_results", [])
            for result in tool_results:
                if result.get("success"):
                    context["previous_tools"].append(result.get("tool_name", "unknown"))
                else:
                    context["failed_tools"].append(result.get("tool_name", "unknown"))
        
        # Get coverage data
        coverage_data = hop.get("coverage", {})
        if coverage_data:
            # Get coverage analysis from the most recent hop
            if coverage_data.get("coverage_analysis"):
                context["coverage_analysis"] = coverage_data["coverage_analysis"]
            
            # Collect missing data
            if coverage_data.get("missing_data"):
                context["missing_data"].extend(coverage_data["missing_data"])
            
            # Check if more data is needed
            if coverage_data.get("needs_more_data"):
                context["needs_more_data"] = True
    
    # Remove duplicates
    context["previous_tools"] = list(set(context["previous_tools"]))
    context["failed_tools"] = list(set(context["failed_tools"]))
    
    return context


def _format_conversation_history(conversation_history: List[Dict[str, Any]]) -> str:
    """
    Format conversation history for LLM context.
    
    Args:
        conversation_history: List of conversation messages
        
    Returns:
        Formatted conversation context string
    """
    if not conversation_history:
        return "No conversation history available."
    
    formatted_messages = []
    for i, message in enumerate(conversation_history):
        role = message.get("role", "unknown")
        content = message.get("content", "")
        formatted_messages.append(f"{i+1}. {role.title()}: {content}")
    
    return "\n".join(formatted_messages)


def _format_context_for_prompt(context: Dict[str, Any]) -> str:
    """Format context information for the LLM prompt."""
    if not context:
        return "No previous context available"
    
    context_parts = []
    
    # Hop information
    current_hop = context.get("current_hop", 0)
    max_hops = context.get("max_hops", 2)
    context_parts.append(f"- Current hop: {current_hop + 1}/{max_hops}")
    
    # Previous execution results
    previous_tools = context.get("previous_tools", [])
    failed_tools = context.get("failed_tools", [])
    
    if previous_tools:
        context_parts.append(f"- Previously executed tools: {', '.join(previous_tools)}")
    if failed_tools:
        context_parts.append(f"- Previously failed tools: {', '.join(failed_tools)}")
    
    # Coverage analysis results
    coverage_analysis = context.get("coverage_analysis")
    if coverage_analysis:
        context_parts.append(f"- Previous coverage score: {coverage_analysis.get('coverage_score', 0):.1%}")
        context_parts.append(f"- Data sufficient: {coverage_analysis.get('data_sufficient', False)}")
    
    # Missing data gaps
    missing_data = context.get("missing_data", [])
    if missing_data:
        context_parts.append("- Identified data gaps:")
        for gap in missing_data:
            if isinstance(gap, dict):
                gap_type = gap.get("gap_type", "Unknown")
                description = gap.get("description", "No description")
                context_parts.append(f"  * {gap_type}: {description}")
    
    # Available docs
    available_docs = context.get("available_docs", [])
    if available_docs:
        context_parts.append(f"- Available docs: {', '.join(available_docs)}")
    
    # Needs more data flag
    needs_more_data = context.get("needs_more_data", False)
    if needs_more_data:
        context_parts.append("- This is a follow-up planning cycle to gather more data")
    
    return "\n".join(context_parts) if context_parts else "No relevant context available"


def _extract_email_from_query(query: str) -> str:
    """Extract email from user query if present."""
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    match = re.search(email_pattern, query)
    return match.group() if match else None
