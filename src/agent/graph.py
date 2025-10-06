"""LangGraph for the agent."""

import time
from langgraph.graph import StateGraph, START, END
from agent.types import State
from agent.nodes.plan.plan import plan_node
from agent.nodes.gather.gather import gather_node
from agent.nodes.coverage.coverage import coverage_node
from agent.nodes.draft.draft import draft_node
from src.mcp.factory import create_mcp_client


def initialize_state(state: State) -> State:
    """Initialize the state with available tools (without storing MCP client)."""
    # Only initialize if not already done
    if "available_tools" not in state or state["available_tools"] is None:
        try:
            print("🔌 Initializing MCP client...")
            mcp_client = create_mcp_client()
            
            # Fetch available tools from MCP server
            print("🔧 Fetching available tools from MCP server...")
            available_tools = mcp_client.list_tools()
            print(f"✅ Found {len(available_tools)} available tools")
            
            # Initialize state with proper values (NO MCP client in state)
            state["available_tools"] = available_tools
            state["tool_data"] = state.get("tool_data", {})
            state["docs_data"] = state.get("docs_data", {})
            state["hops"] = state.get("hops", [])
            state["max_hops"] = state.get("max_hops", 2)
            state["response"] = state.get("response", "")
            state["error"] = state.get("error", None)
            state["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%SZ")
            
        except Exception as e:
            print(f"❌ Failed to initialize MCP client: {e}")
            state["error"] = f"MCP initialization failed: {str(e)}"
            state["response"] = "Sorry, I'm unable to connect to the required services right now."
    
    return state


def build_graph():
    """Build the agent graph."""
    g = StateGraph(State)
    
    # Add nodes
    g.add_node("initialize", initialize_state)
    g.add_node("plan", plan_node)
    g.add_node("gather", gather_node)
    g.add_node("coverage", coverage_node)
    g.add_node("draft", draft_node)
    
    # Add edges
    g.add_edge(START, "initialize")
    g.add_edge("plan", "gather")
    g.add_edge("gather", "coverage")
    
    # Add conditional routing from coverage
    def route_from_coverage(state: State) -> str:
        """Route from coverage node based on analysis."""
        next_node = state.get("next_node", "end")
        
        if next_node == "plan":
            return "plan"
        elif next_node == "respond":
            return "draft"  # Route to draft node for response generation
        elif next_node == "escalate":
            return "end"  # Escalate by ending with error
        else:
            return "end"
    
    # Add conditional routing from initialize
    def route_from_initialize(state: State) -> str:
        """Route from initialize node based on success/failure."""
        if state.get("error"):
            return "end"  # If initialization failed, end with error
        else:
            return "plan"  # If successful, proceed to plan
    
    g.add_conditional_edges(
        "initialize",
        route_from_initialize,
        {
            "plan": "plan",
            "end": END
        }
    )
    
    g.add_conditional_edges(
        "coverage",
        route_from_coverage,
        {
            "plan": "plan",
            "draft": "draft",
            "end": END
        }
    )
    
    # Draft node always ends
    g.add_edge("draft", END)
    
    return g.compile()


# Export the graph for LangGraph CLI
graph = build_graph()