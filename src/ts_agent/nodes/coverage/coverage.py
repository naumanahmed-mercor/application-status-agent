"""Coverage node implementation for analyzing data sufficiency."""

import re
from typing import Dict, Any, List, Optional
from ts_agent.types import State
from .schemas import CoverageData, CoverageResponse, CoverageAnalysis, DataGap
from ts_agent.llm import planner_llm
from src.clients.prompts import get_prompt, PROMPT_NAMES
from src.utils.prompts import build_conversation_and_user_context


def coverage_node(state: State) -> State:
    """
    Analyze data coverage and determine next action.
    
    This node analyzes whether we have sufficient data to answer the user's query
    and decides whether to continue, gather more data, or escalate.
    """
    # Get current hop data - access state["hops"] directly to ensure mutations persist
    if "hops" not in state or not state["hops"]:
        state["error"] = "No current hop data found"
        return state
    
    current_hop_index = len(state["hops"]) - 1
    current_hop_data = state["hops"][current_hop_index]
    hop_number = current_hop_data.get("hop_number", current_hop_index + 1)
    max_hops = state.get("max_hops", 3)
    
    print(f"🔍 Coverage Analysis (Hop {hop_number}/{max_hops})")
    print("=" * 50)
    
    # Note: Hop limit check will be done at the end after coverage analysis
    
    # Extract data from state level (accumulated across all hops)
    tool_data = state.get("tool_data", {})  # All accumulated tool data
    docs_data = state.get("docs_data", {})  # All accumulated docs data
    
    # Show accumulated data
    if tool_data:
        print(f"📊 Accumulated Tool Data ({len(tool_data)} tools):")
        for tool_name, data in tool_data.items():
            print(f"   📋 {tool_name}: {type(data).__name__}")
    else:
        print("📊 No accumulated tool data available")
    
    if docs_data:
        print(f"📚 Accumulated Docs Data ({len(docs_data)} queries):")
        for query, data in docs_data.items():
            print(f"   📖 {query}: {type(data).__name__}")
    else:
        print("📚 No accumulated docs data available")
    
    try:
        # Build formatted conversation history and user details (with validation)
        formatted_context = build_conversation_and_user_context(state)
    except ValueError as e:
        state["error"] = str(e)
        return state
    
    try:
        # Get plan reasoning from current hop (if available)
        plan_reasoning = None
        if current_hop_data.get("plan"):
            plan_reasoning = current_hop_data["plan"].get("reasoning")
        
        # Perform coverage analysis with full conversation history
        coverage_response = _analyze_coverage(
            formatted_context["conversation_history"],
            formatted_context["user_details"],
            tool_data,
            docs_data,
            hop_number,
            max_hops,
            plan_reasoning
        )
        
        # Update routing state - convert next_action to next_node
        if coverage_response.next_action == "gather_more":
            state["next_node"] = "plan"  # Route back to plan for more data gathering
        elif coverage_response.next_action == "continue":
            state["next_node"] = "respond"  # Route to response generation
        elif coverage_response.next_action == "escalate":
            state["next_node"] = "escalate"  # Route to escalation
        else:
            state["next_node"] = "end"  # Default to end
        
        state["escalation_reason"] = coverage_response.escalation_reason
        
        # Store coverage analysis in nested structure using CoverageData TypedDict
        coverage_data: CoverageData = {
            "coverage_analysis": coverage_response.model_dump(),
            "data_sufficient": coverage_response.data_sufficient,
            "next_node": state["next_node"],  # Use the converted next_node
            "escalation_reason": coverage_response.escalation_reason
        }
        current_hop_data["coverage"] = coverage_data
        
        # Print analysis results
        print(f"✅ Data Sufficient: {coverage_response.data_sufficient}")
        print(f"💭 Reasoning: {coverage_response.reasoning}")
        
        if coverage_response.missing_data:
            print(f"❌ Missing Data:")
            for gap in coverage_response.missing_data:
                print(f"   - {gap.gap_type}: {gap.description}")
        
        print(f"🎯 Next Action: {coverage_response.next_action}")
        
        # Check hop limit after coverage analysis
        if coverage_response.next_action == "gather_more":
            # Check if we've exceeded max hops before redirecting to plan
            if hop_number >= max_hops:
                print(f"⚠️  Maximum hops ({max_hops}) reached - escalating instead of gathering more")
                current_hop_data["coverage"]["next_node"] = "escalate"
                current_hop_data["coverage"]["escalation_reason"] = f"Exceeded maximum hops ({max_hops}). Unable to gather sufficient data."
                state["next_node"] = "escalate"
                state["escalation_reason"] = current_hop_data["coverage"]["escalation_reason"]
            else:
                print(f"🔄 Redirecting to plan node for more data gathering...")
        elif coverage_response.next_action == "continue":
            print(f"✅ Proceeding to response generation...")
        elif coverage_response.next_action == "escalate":
            print(f"🚨 Escalating to human team: {coverage_response.escalation_reason}")
        
    except Exception as e:
        state["error"] = f"Coverage analysis failed: {str(e)}"
        state["next_node"] = "escalate"
        state["escalation_reason"] = f"Coverage analysis failed: {str(e)}"
        print(f"❌ Coverage analysis error: {e}")
    
    return state




def _analyze_coverage(
    conversation_history: str,
    user_details: str,
    tool_data: Dict[str, Any],
    docs_data: Dict[str, Any],
    hop_number: int,
    max_hops: int,
    plan_reasoning: Optional[str] = None
) -> CoverageResponse:
    """
    Analyze data coverage using LLM.
    
    Args:
        conversation_history: Formatted conversation history string
        user_details: Formatted user details string
        tool_data: Accumulated tool data
        docs_data: Accumulated docs data
        hop_number: Current hop number
        max_hops: Maximum allowed hops
        plan_reasoning: Reasoning from plan node explaining why tools were/weren't chosen
        
    Returns:
        Coverage analysis response
    """
    # Create detailed prompt for LLM with actual data content
    # Get prompt from LangSmith
    prompt_template = get_prompt(PROMPT_NAMES["COVERAGE_NODE"])
    
    # Format available data summary
    available_data_summary = _summarize_accumulated_data_with_content(tool_data, docs_data, plan_reasoning)
    
    # Format the prompt with variables
    prompt = prompt_template.format(
        conversation_history=conversation_history,
        user_details=user_details,
        available_data=available_data_summary
    )
    
    # Get LLM response with structured output
    llm = planner_llm()
    llm_with_structure = llm.with_structured_output(CoverageResponse, method="function_calling")
    
    try:
        coverage_response = llm_with_structure.invoke(prompt)
        
        # Check if we've hit max hops - override to escalate if needed
        if not coverage_response.data_sufficient and hop_number >= max_hops:
            print(f"⚠️  Maximum hops ({max_hops}) reached - escalating instead of gathering more")
            coverage_response.next_action = "escalate"
            coverage_response.escalation_reason = f"Exceeded maximum hops ({max_hops}). Unable to gather sufficient data."
        
        return coverage_response
        
    except Exception as e:
        raise ValueError(f"Failed to get coverage analysis: {e}")




def _summarize_accumulated_data_with_content(
    tool_data: Dict[str, Any], 
    docs_data: Dict[str, Any],
    plan_reasoning: Optional[str] = None
) -> str:
    """Summarize accumulated tool and docs data with actual content for LLM prompt."""
    summary = []
    
    # Plan reasoning section (helps explain why tools were/weren't chosen)
    if plan_reasoning:
        summary.append("PLAN REASONING:")
        summary.append(f"  {plan_reasoning}")
        summary.append("")  # blank line
    
    # Tool data section
    if tool_data:
        summary.append("TOOL DATA:")
        for tool_name, data in tool_data.items():
            summary.append(f"\n{tool_name}:")
            summary.extend(_format_data_content(data))
    else:
        summary.append("TOOL DATA: None available")
    
    # Docs data section
    if docs_data:
        summary.append("\nDOCS DATA:")
        for query, data in docs_data.items():
            summary.append(f"\nQuery: '{query}'")
            summary.extend(_format_data_content(data))
    else:
        summary.append("\nDOCS DATA: None available")
    
    return "\n".join(summary)


def _format_data_content(data: Any) -> List[str]:
    """Format data content for display - show complete data without truncation."""
    import json
    content = []
    
    if isinstance(data, list) and len(data) > 0:
        # Show all list items with complete content
        for i, item in enumerate(data):
            if isinstance(item, dict) and 'text' in item:
                # Show complete text content
                text_content = item['text']
                content.append(f"  Item {i+1}: {text_content}")
            elif isinstance(item, dict):
                # Show complete dict content
                content.append(f"  Item {i+1}: {json.dumps(item, indent=2)}")
            else:
                content.append(f"  Item {i+1}: {str(item)}")
    elif isinstance(data, dict):
        # Show complete dict content
        content.append(f"  {json.dumps(data, indent=2)}")
    else:
        content.append(f"  {str(data)}")
    
    return content
