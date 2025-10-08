"""LangGraph for the agent."""

from langgraph.graph import StateGraph, START, END
from agent.types import State
from agent.nodes.initialize.initialize import initialize_node
from agent.nodes.plan.plan import plan_node
from agent.nodes.gather.gather import gather_node
from agent.nodes.coverage.coverage import coverage_node
from agent.nodes.draft.draft import draft_node
from agent.nodes.validate.validate import validate_node
from agent.nodes.escalate.escalate import escalate_node
from agent.nodes.response.response import response_node
from agent.nodes.finalize.finalize import finalize_node


def build_graph():
    """Build the agent graph."""
    g = StateGraph(State)
    
    # Add nodes
    g.add_node("initialize", initialize_node)
    g.add_node("plan", plan_node)
    g.add_node("gather", gather_node)
    g.add_node("coverage", coverage_node)
    g.add_node("draft", draft_node)
    g.add_node("validate", validate_node)
    g.add_node("escalate", escalate_node)
    g.add_node("response", response_node)
    g.add_node("finalize", finalize_node)
    
    # Add edges
    g.add_edge(START, "initialize")
    
    # Add conditional routing from plan
    def route_from_plan(state: State) -> str:
        """Route from plan node based on success/failure."""
        if state.get("error"):
            return "escalate"  # If plan generation failed, escalate
        else:
            return "gather"  # If successful, proceed to gather
    
    # Add conditional routing from gather
    def route_from_gather(state: State) -> str:
        """Route from gather node based on success/failure."""
        if state.get("error"):
            return "escalate"  # If gather failed, escalate
        else:
            return "coverage"  # If successful, proceed to coverage
    
    # Add conditional routing from coverage
    def route_from_coverage(state: State) -> str:
        """Route from coverage node based on analysis."""
        next_node = state.get("next_node", "end")
        
        if next_node == "plan":
            return "plan"
        elif next_node == "respond":
            return "draft"  # Route to draft node for response generation
        elif next_node == "escalate":
            return "escalate"  # Route to escalate node
        else:
            return "end"
    
    # Add conditional routing from initialize
    def route_from_initialize(state: State) -> str:
        """Route from initialize node based on success/failure."""
        if state.get("error"):
            return "escalate"  # If initialization failed, escalate
        else:
            return "plan"  # If successful, proceed to plan
    
    # Add conditional routing from validate
    def route_from_validate(state: State) -> str:
        """Route from validate node based on validation result."""
        next_node = state.get("next_node", "end")
        
        if next_node == "response":
            return "response"  # Validation passed, send response
        elif next_node == "escalate":
            return "escalate"  # Validation failed, escalate
        else:
            return "end"
    
    # Add conditional routing from draft
    def route_from_draft(state: State) -> str:
        """Route from draft node based on response type or error."""
        next_node = state.get("next_node")
        if next_node == "escalate":
            return "escalate"  # ROUTE_TO_TEAM or error
        else:
            return "validate"  # Normal REPLY, proceed to validation
    
    g.add_conditional_edges(
        "initialize",
        route_from_initialize,
        {
            "plan": "plan",
            "escalate": "escalate"
        }
    )
    
    g.add_conditional_edges(
        "plan",
        route_from_plan,
        {
            "gather": "gather",
            "escalate": "escalate"
        }
    )
    
    g.add_conditional_edges(
        "gather",
        route_from_gather,
        {
            "coverage": "coverage",
            "escalate": "escalate"
        }
    )
    
    g.add_conditional_edges(
        "coverage",
        route_from_coverage,
        {
            "plan": "plan",
            "draft": "draft",
            "escalate": "escalate",
            "end": END
        }
    )
    
    # Draft node routes conditionally
    g.add_conditional_edges(
        "draft",
        route_from_draft,
        {
            "validate": "validate",
            "escalate": "escalate"
        }
    )
    
    # Validate node routes conditionally
    g.add_conditional_edges(
        "validate",
        route_from_validate,
        {
            "response": "response",
            "escalate": "escalate",
            "end": END
        }
    )
    
    # Add conditional routing from response
    def route_from_response(state: State) -> str:
        """Route from response node based on delivery success/failure."""
        if state.get("error"):
            return "escalate"  # If response delivery failed, escalate
        else:
            return "finalize"  # If successful, proceed to finalize
    
    g.add_conditional_edges(
        "response",
        route_from_response,
        {
            "finalize": "finalize",
            "escalate": "escalate"
        }
    )
    
    # Escalate node goes to finalize
    g.add_edge("escalate", "finalize")
    
    # Finalize node always ends
    g.add_edge("finalize", END)
    
    return g.compile()


# Export the graph for LangGraph CLI
graph = build_graph()