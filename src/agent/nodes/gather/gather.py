"""Gather node implementation for executing tool calls."""

import time
from typing import Dict, Any, List
from agent.types import State
from .schemas import GatherData, ToolCall, ToolResult, GatherRequest
from src.mcp.factory import create_mcp_client


def gather_node(state: State) -> State:
    """
    Execute all planned tool calls and gather results.

    This node takes the tool calls from the plan node and executes them
    using the MCP client, storing the results in the state.
    """
    # Get current hop data
    hops_array = state.get("hops", [])
    current_hop_index = len(hops_array) - 1
    
    if current_hop_index < 0:
        state["error"] = "No current hop data found"
        return state
    
    current_hop_data = hops_array[current_hop_index]
    plan_data = current_hop_data.get("plan", {})
    tool_calls_data = plan_data.get("tool_calls", [])
    user_email = state.get("user_email")
    
    if not tool_calls_data:
        # No tools needed - this is normal for simple queries like "Hi"
        print("ℹ️  No tools needed for this query")
        
        # Store empty gather results using GatherData TypedDict
        gather_data: GatherData = {
            "tool_results": [],
            "total_execution_time_ms": 0.0,
            "success_rate": 1.0,  # 100% success since no tools failed
            "execution_status": "completed"
        }
        current_hop_data["gather"] = gather_data
        
        print("✅ No tool execution needed - proceeding to coverage analysis")
        return state
    
    try:
        # Create MCP client (don't store in state due to serialization issues)
        mcp_client = create_mcp_client()
        
        # Execute all tool calls
        results = []
        successful_tools = []
        failed_tools = []
        total_start_time = time.time()
        
        print(f"🔧 Executing {len(tool_calls_data)} tool calls...")
        
        for i, tool_call_data in enumerate(tool_calls_data, 1):
            start_time = time.time()  # Move start_time outside try block
            tool_call = None  # Initialize tool_call variable
            try:
                # Create ToolCall object for validation
                tool_call = ToolCall(**tool_call_data)
                
                print(f"   {i}. Executing {tool_call.tool_name}...")
                
                # Execute the tool
                result_data = _execute_tool(mcp_client, tool_call)
                
                execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds
                
                # Create successful result
                result = ToolResult(
                    tool_name=tool_call.tool_name,
                    success=True,
                    data=result_data,
                    execution_time_ms=execution_time,
                    timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ")
                )
                
                results.append(result)
                successful_tools.append(tool_call.tool_name)
                print(f"      ✅ Success ({execution_time:.1f}ms)")
                
            except Exception as e:
                execution_time = (time.time() - start_time) * 1000
                
                # Create failed result
                result = ToolResult(
                    tool_name=tool_call.tool_name if tool_call else "unknown",
                    success=False,
                    error=str(e),
                    execution_time_ms=execution_time,
                    timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ")
                )
                
                results.append(result)
                failed_tools.append(tool_call.tool_name if tool_call else "unknown")
                print(f"      ❌ Failed: {e}")
        
        total_execution_time = (time.time() - total_start_time) * 1000
        success_rate = len(successful_tools) / len(tool_calls_data) if tool_calls_data else 0
        
        # Store results in nested gather structure using GatherData TypedDict
        gather_data: GatherData = {
            "tool_results": [result.model_dump() for result in results],
            "total_execution_time_ms": total_execution_time,
            "success_rate": success_rate,
            "execution_status": "completed"
        }
        current_hop_data["gather"] = gather_data
        
        # Store individual tool results at state level (independent of hops)
        # Initialize data storage if it doesn't exist
        if "tool_data" not in state:
            state["tool_data"] = {}
        if "docs_data" not in state:
            state["docs_data"] = {}
        
        for result in results:
            if result.success and result.data:
                # Check if this is a docs tool (search_talent_docs)
                if result.tool_name == "search_talent_docs":
                    # Store docs data separately with unique key (query + hop)
                    # Extract query from the result data structure
                    query = "unknown_query"
                    if result.data and len(result.data) > 0:
                        first_item = result.data[0]
                        if isinstance(first_item, dict) and "text" in first_item:
                            text_data = first_item["text"]
                            if isinstance(text_data, dict) and "query" in text_data:
                                query = text_data["query"]
                            elif isinstance(text_data, str):
                                # Try to parse JSON string
                                try:
                                    import json
                                    parsed = json.loads(text_data)
                                    query = parsed.get("query", "unknown_query")
                                except:
                                    query = "unknown_query"
                    
                    # Create unique key with hop number to avoid overwriting
                    current_hop = len(state.get("hops", []))
                    unique_key = f"{query} (hop {current_hop})"
                    state["docs_data"][unique_key] = result.data
                else:
                    # Store regular tool data
                    state["tool_data"][result.tool_name] = result.data
        
        print(f"🎉 Tool execution complete!")
        print(f"   ✅ Successful: {len(successful_tools)}")
        print(f"   ❌ Failed: {len(failed_tools)}")
        print(f"   ⏱️  Total time: {total_execution_time:.1f}ms")
        print(f"   📊 Success rate: {success_rate:.1%}")
        
    except Exception as e:
        error_msg = f"Gather node error: {str(e)}"
        state["error"] = error_msg
        state["escalation_reason"] = error_msg
        state["next_node"] = "escalate"
        print(f"❌ Gather node error: {e}")
    
    return state


def _execute_tool(mcp_client, tool_call: ToolCall) -> Dict[str, Any]:
    """
    Execute a single tool call using MCP client.
    
    Args:
        mcp_client: MCP client instance
        tool_call: Tool call to execute
        
    Returns:
        Tool execution result data
    """
    tool_name = tool_call.tool_name
    parameters = tool_call.parameters
    
    # Execute tool using MCP client
    try:
        result = mcp_client.call_tool(tool_name, parameters)
        return result
    except Exception as e:
        raise Exception(f"Tool execution failed: {str(e)}")
