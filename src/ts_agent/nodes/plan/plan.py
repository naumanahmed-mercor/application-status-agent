"""Plan node implementation for intelligent tool selection and planning."""

import re
import os
from typing import Dict, Any, List
from ts_agent.types import State, ToolType
from .schemas import PlanData, Plan, PlanRequest
from ts_agent.llm import planner_llm
from src.clients.prompts import get_prompt, PROMPT_NAMES
from src.utils.prompts import build_conversation_and_user_context, format_procedure_for_prompt
from jsonschema import validate, ValidationError
import logging

logger = logging.getLogger(__name__)


def _validate_and_sanitize_plan(
    plan: Plan, 
    available_tools: List[Dict[str, Any]], 
    verified_email: str,
    conversation_id: str
) -> Plan:
    """
    Validate tool calls against tool schemas and sanitize parameters.
    
    Injects verified values from state:
    - user_email: Replaces any email parameter with verified email from Intercom
    - conversation_id: Injects conversation_id for action tools that need it
    
    Invalid tool calls are skipped with a warning instead of failing the entire plan.
    
    Args:
        plan: Generated plan from LLM
        available_tools: List of available tools with schemas
        verified_email: Verified user email from Intercom (source of truth)
        conversation_id: Conversation ID from state
        
    Returns:
        Validated and sanitized plan (with invalid tool calls removed)
    """
    # Create a lookup map for tools
    tools_map = {tool["name"]: tool for tool in available_tools}
    
    validated_tool_calls = []
    skipped_count = 0
    
    for i, tool_call in enumerate(plan.tool_calls, 1):
        tool_name = tool_call.tool_name
        
        # 1. Validate tool exists
        if tool_name not in tools_map:
            available_names = ", ".join(tools_map.keys())
            logger.warning(
                f"⚠️  Tool call {i}: Tool '{tool_name}' not found. Skipping. "
                f"Available tools: {available_names}"
            )
            print(f"   ⚠️  Skipping invalid tool: {tool_name} (not found)")
            skipped_count += 1
            continue
        
        tool_schema = tools_map[tool_name]
        input_schema = tool_schema.get("inputSchema", {})
        
        # 2. Sanitize parameters (inject verified email, conversation_id, etc.)
        # Build injection map with trusted values
        import os
        injection_map = {
            "user_email": verified_email,
            "conversation_id": conversation_id,
            "dry_run": lambda: os.getenv("DRY_RUN", "false").lower() == "true",
        }
        
        try:
            sanitized_params = _sanitize_tool_params(
                tool_call.parameters,
                input_schema,
                tool_name,
                injection_map
            )
        except Exception as e:
            logger.warning(f"   ⚠️  Skipping tool {tool_name}: Parameter sanitization failed: {e}")
            print(f"   ⚠️  Skipping tool {tool_name}: {e}")
            skipped_count += 1
            continue
        
        # 3. Validate parameters against tool's input schema
        if input_schema and input_schema.get("properties"):
            try:
                validate(instance=sanitized_params, schema=input_schema)
            except ValidationError as e:
                logger.warning(
                    f"⚠️  Tool call {i} ({tool_name}): Parameter validation failed - {e.message}. Skipping."
                )
                print(f"   ⚠️  Skipping tool {tool_name}: Invalid parameters ({e.message})")
                skipped_count += 1
                continue
        
        # Create validated tool call with sanitized params
        from .schemas import ToolCall
        validated_tool_call = ToolCall(
            tool_name=tool_name,
            parameters=sanitized_params,
            reasoning=tool_call.reasoning
        )
        validated_tool_calls.append(validated_tool_call)
    
    # Log summary if any tools were skipped
    if skipped_count > 0:
        logger.info(f"Validation complete: {len(validated_tool_calls)} valid, {skipped_count} skipped")
    
    # Return new plan with validated tool calls
    return Plan(
        reasoning=plan.reasoning,
        tool_calls=validated_tool_calls
    )


def _sanitize_tool_params(
    params: Dict[str, Any],
    input_schema: Dict[str, Any],
    tool_name: str,
    injection_map: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Sanitize tool parameters by injecting verified values from state.
    
    This function:
    1. Accepts a dict of trusted values to inject/replace
    2. Goes through tool schema and replaces params that match the injection map
    3. Validates all required params are present after injection
    
    Args:
        params: Original parameters from LLM
        input_schema: Tool's input schema
        tool_name: Name of the tool
        injection_map: Dict mapping param names to trusted values (can be callables)
        
    Returns:
        Sanitized parameters with trusted values injected
        
    Raises:
        ValueError: If required parameters are missing after injection
    """
    sanitized = params.copy()
    properties = input_schema.get("properties", {})
    required_params = input_schema.get("required", [])
    
    # Go through each parameter in the tool's schema
    for param_name in properties.keys():
        # Check if this param should be injected/replaced
        if param_name in injection_map:
            value = injection_map[param_name]
            # Handle callable values (like dry_run)
            sanitized[param_name] = value() if callable(value) else value
            
            if param_name not in params or params[param_name] != sanitized[param_name]:
                logger.info(
                    f"💉 Injected {param_name}={sanitized[param_name]} "
                    f"(was: {params.get(param_name, 'missing')})"
                )
    
    # Validate all required parameters are present
    missing_params = []
    for required_param in required_params:
        if required_param not in sanitized or sanitized[required_param] is None:
            missing_params.append(required_param)
    
    if missing_params:
        raise ValueError(
            f"Missing required parameters for {tool_name}: {', '.join(missing_params)}"
        )
    
    return sanitized


def plan_node(state: State) -> State:
    """
    Plan which tools to execute based on conversation history.
    
    This node analyzes the entire conversation history and creates a plan for which MCP tools
    to execute to best respond to the conversation.
    """
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
    
    try:
        # Build formatted conversation history and user details (with validation)
        formatted_context = build_conversation_and_user_context(state)
        context["conversation_history_formatted"] = formatted_context["conversation_history"]
        context["user_details_formatted"] = formatted_context["user_details"]
    except ValueError as e:
        state["error"] = str(e)
        return state
    
    plan_request = PlanRequest(
        conversation_history=state.get("messages", []),
        user_email=None,  # No longer used, kept for schema compatibility
        context=context
    )
    
    try:
        # Get available tools from state
        available_tools = state.get("available_tools", [])
        
        # Get selected procedure from state (if any)
        selected_procedure = state.get("selected_procedure")
        
        # Generate plan using LLM
        plan = _generate_plan(plan_request, available_tools, selected_procedure)
        
        # Get verified email from Intercom (source of truth)
        user_details = state.get("user_details", {})
        verified_email = user_details.get("email", "")
        
        # Get conversation_id from state
        conversation_id = state.get("conversation_id", "")
        
        # Validate and sanitize the plan (check tool schemas, inject verified parameters)
        validated_plan = _validate_and_sanitize_plan(plan, available_tools, verified_email, conversation_id)
        
        # Separate tool calls by type (gather vs action)
        gather_tool_calls = []
        action_tool_calls = []
        
        # Create lookup for tool types
        tools_type_map = {tool["name"]: tool.get("tool_type") for tool in available_tools}
        
        for tool_call in validated_plan.tool_calls:
            tool_type = tools_type_map.get(tool_call.tool_name, ToolType.GATHER.value)
            
            if tool_type in [ToolType.INTERNAL_ACTION.value, ToolType.EXTERNAL_ACTION.value]:
                action_tool_calls.append(tool_call)
            else:
                gather_tool_calls.append(tool_call)
        
        # Store plan in nested structure using PlanData TypedDict
        # Convert ToolCall objects to dictionaries for state storage
        tool_calls_dicts = [tc.model_dump() for tc in validated_plan.tool_calls]
        gather_tool_calls_dicts = [tc.model_dump() for tc in gather_tool_calls]
        action_tool_calls_dicts = [tc.model_dump() for tc in action_tool_calls]
        
        plan_data: PlanData = {
            "plan": validated_plan.model_dump(),
            "tool_calls": tool_calls_dicts,  # All tools (backward compatibility)
            "gather_tool_calls": gather_tool_calls_dicts,  # Only gather tools
            "action_tool_calls": action_tool_calls_dicts,  # Only action tools
            "reasoning": validated_plan.reasoning,
        }
        hop_data["plan"] = plan_data
        
        print(f"📋 Plan generated (Hop {current_hop + 1}):")
        print(f"   📊 Total: {len(validated_plan.tool_calls)} tools")
        print(f"   🔍 Gather tools: {len(gather_tool_calls)}")
        print(f"   ⚡ Action tools: {len(action_tool_calls)}")
        
        if gather_tool_calls:
            print(f"\n   Gather tools:")
            for i, tool_call in enumerate(gather_tool_calls, 1):
                print(f"      {i}. {tool_call.tool_name} - {tool_call.reasoning}")
        
        if action_tool_calls:
            print(f"\n   Action tools (for coverage to consider):")
            for i, tool_call in enumerate(action_tool_calls, 1):
                print(f"      {i}. {tool_call.tool_name} - {tool_call.reasoning}")
        
    except Exception as e:
        error_msg = f"Plan generation failed: {str(e)}"
        state["error"] = error_msg
        state["escalation_reason"] = error_msg
        state["next_node"] = "escalate"
        print(f"❌ Plan generation error: {e}")
        return state
    
    # Add hop data to hops array
    state["hops"].append(hop_data)
    
    return state


def _generate_plan(request: PlanRequest, available_tools: List[Dict[str, Any]], selected_procedure: Dict[str, Any] = None) -> Plan:
    """
    Generate an execution plan using LLM.
    
    Args:
        request: Plan request with conversation history and context
        available_tools: List of available tools from MCP server
        selected_procedure: Optional selected procedure from RAG store
        
    Returns:
        Generated execution plan
    """
    
    # Create context-aware prompt for LLM
    context_info = _format_context_for_prompt(request.context)
    
    # Build conversation history and user details (structured format)
    # Get from context if available (passed from plan_node call)
    conversation_history = request.context.get("conversation_history_formatted", "")
    user_details = request.context.get("user_details_formatted", "")
    
    # Format procedure if available
    procedure_text = format_procedure_for_prompt(selected_procedure)
    
    # Get prompt from LangSmith
    prompt_template_text = get_prompt(PROMPT_NAMES["PLAN_NODE"])
    
    # Format the prompt with variables
    formatted_tools = _format_tools_for_prompt(available_tools)
    prompt = prompt_template_text.format(
        conversation_history=conversation_history,
        user_details=user_details,
        procedure=procedure_text,
        context_info=context_info,
        available_tools=formatted_tools
    )
        
    # Get LLM response with structured output
    # Use function_calling method since Plan schema contains Dict[str, Any] 
    # which is not supported by OpenAI's native structured output
    llm = planner_llm()
    llm_with_structure = llm.with_structured_output(Plan, method="function_calling")
    plan = llm_with_structure.invoke(prompt)
    
    return plan


def _format_tools_for_prompt(tools: List[Dict[str, Any]]) -> str:
    """Format tools for LLM prompt with full schemas."""
    import json
    formatted = []
    
    for tool in tools:
        name = tool.get("name", "unknown")
        description = tool.get("description", "No description available")
        input_schema = tool.get("inputSchema", {})
        tool_type = tool.get("tool_type", "gather")  # Get tool type
        
        # Format tool with full schema and type
        tool_str = f"Tool: {name}\n"
        tool_str += f"Type: {tool_type}\n"  # Add type to prompt
        tool_str += f"Description: {description}\n"
        tool_str += f"Input Schema:\n{json.dumps(input_schema, indent=2)}"
        
        formatted.append(tool_str)
    
    return "\n\n".join(formatted)


def _build_context_from_hops(hops_array: List[Dict[str, Any]], state: State) -> Dict[str, Any]:
    """Build context from previous hops for planning."""
    # Current hop is the next one to plan (len of completed hops + 1)
    current_hop = len(hops_array) + 1
    
    context = {
        "timestamp": state.get("timestamp"),
        "current_hop": current_hop,
        "max_hops": state.get("max_hops", 3),
        "tool_executions": [],  # List of {tool_name, parameters, success, error}
        "doc_searches": [],  # List of {query, result_count, success}
        "coverage_analysis": None
    }
    
    # Aggregate data from all previous hops
    for hop in hops_array:
        # Get plan data to extract tool calls with parameters
        plan_data = hop.get("plan", {})
        tool_calls_from_plan = plan_data.get("tool_calls", [])
        
        # Get gather data to see results
        gather_data = hop.get("gather", {})
        if gather_data:
            tool_results = gather_data.get("tool_results", [])
            
            # Match tool results with their plan by index (order matters)
            for idx, result in enumerate(tool_results):
                tool_name = result.get("tool_name", "unknown")
                success = result.get("success", False)
                error = result.get("error")
                
                # Get parameters from the corresponding tool call by index
                parameters = {}
                if idx < len(tool_calls_from_plan):
                    tool_call = tool_calls_from_plan[idx]
                    # Verify tool names match (sanity check)
                    if tool_call.get("tool_name") == tool_name:
                        parameters = tool_call.get("parameters", {})
                
                # Special handling for doc searches
                if tool_name == "search_talent_docs":
                    query = parameters.get("query", "unknown query")
                    result_count = 0
                    if success and result.get("data"):
                        # Parse result data to get count
                        data_list = result.get("data", [])
                        if data_list and isinstance(data_list, list):
                            for item in data_list:
                                if isinstance(item, dict) and item.get("type") == "text":
                                    try:
                                        import json
                                        parsed = json.loads(item.get("text", "{}"))
                                        result_count = parsed.get("total_results", 0)
                                        break
                                    except:
                                        pass
                    
                    context["doc_searches"].append({
                        "query": query,
                        "result_count": result_count,
                        "success": success
                    })
                else:
                    # Regular tool execution
                    context["tool_executions"].append({
                        "tool_name": tool_name,
                        "parameters": parameters,
                        "success": success,
                        "error": error if not success else None
                    })
        
        # Get coverage data (will be overwritten by latest hop)
        coverage_data = hop.get("coverage", {})
        if coverage_data and coverage_data.get("coverage_response"):
            # Always overwrite with latest hop's coverage analysis (only reasoning will be used)
            context["coverage_analysis"] = coverage_data["coverage_response"]
    
    return context




def _format_context_for_prompt(context: Dict[str, Any]) -> str:
    """Format context information for the LLM prompt."""
    if not context:
        return "No previous context available"
    
    context_parts = []
    
    # Hop information
    current_hop = context.get("current_hop", 1)
    max_hops = context.get("max_hops", 3)
    context_parts.append(f"- Planning for hop: {current_hop}/{max_hops}")
    
    # Previous tool executions with signatures
    tool_executions = context.get("tool_executions", [])
    if tool_executions:
        context_parts.append("\n- Previously executed tools:")
        for execution in tool_executions:
            tool_name = execution.get("tool_name", "unknown")
            params = execution.get("parameters", {})
            success = execution.get("success", False)
            error = execution.get("error")
            
            # Format parameters compactly
            param_str = ", ".join([f"{k}={repr(v)}" for k, v in params.items()])
            status = "✓ SUCCESS" if success else f"✗ FAILED ({error})"
            context_parts.append(f"  * {tool_name}({param_str}) - {status}")
    
    # Previous doc searches with result counts
    doc_searches = context.get("doc_searches", [])
    if doc_searches:
        context_parts.append("\n- Previously searched documentation:")
        for search in doc_searches:
            query = search.get("query", "unknown")
            result_count = search.get("result_count", 0)
            success = search.get("success", False)
            status = f"{result_count} results" if success else "FAILED"
            context_parts.append(f"  * '{query}' - {status}")
    
    # Coverage analysis results (reasoning and missing data from latest hop)
    coverage_analysis = context.get("coverage_analysis")
    if coverage_analysis:
        reasoning = coverage_analysis.get('reasoning', '')
        if reasoning:
            context_parts.append(f"\n- Coverage analysis from previous hop: {reasoning}")
        
        # Include missing data gaps to guide tool selection
        missing_data = coverage_analysis.get('missing_data', [])
        if missing_data:
            context_parts.append(f"\n- Missing data identified by coverage:")
            for gap in missing_data:
                gap_type = gap.get('gap_type', 'unknown')
                description = gap.get('description', '')
                context_parts.append(f"  * {gap_type}: {description}")
    
    # Available docs
    available_docs = context.get("available_docs", [])
    if available_docs:
        context_parts.append(f"\n- Available documentation collected: {len(available_docs)} searches")
    
    return "\n".join(context_parts) if context_parts else "No relevant context available"


def _extract_email_from_query(query: str) -> str:
    """Extract email from user query if present."""
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    match = re.search(email_pattern, query)
    return match.group() if match else None
