#!/usr/bin/env python3
"""Test script to run the agent with action node support on a specific conversation."""

import os
import sys
from pathlib import Path

# Add both project root and src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from ts_agent.runner import run_agent_with_conversation_id
import json


def main():
    """Test the agent on a specific conversation."""
    
    # Don't force dry run - respect .env value
    # os.environ["DRY_RUN"] = "true"  # Commented out
    
    # Enable local coverage prompt
    os.environ["USE_LOCAL_COVERAGE_PROMPT"] = "true"
    
    conversation_id = sys.argv[1] if len(sys.argv) > 1 else "215471305660057"
    
    print("=" * 80)
    print(f"🧪 TESTING ACTION NODE ON CONVERSATION: {conversation_id}")
    print("=" * 80)
    print(f"📝 DRY_RUN: {os.getenv('DRY_RUN')}")
    print(f"📝 USE_LOCAL_COVERAGE_PROMPT: {os.getenv('USE_LOCAL_COVERAGE_PROMPT')}")
    print("=" * 80)
    print()
    
    try:
        result = run_agent_with_conversation_id(conversation_id)
        
        print("\n" + "=" * 80)
        print("📊 RESULTS")
        print("=" * 80)
        print(f"\n✅ Response: {result.get('response', 'No response')}")
        print(f"\n❌ Error: {result.get('error', 'None')}")
        print(f"\n🔢 Hops: {len(result.get('hops', []))}")
        
        # Show actions taken
        actions = result.get("actions", [])
        if actions:
            print(f"\n⚡ ACTIONS TAKEN: {len(actions)}")
            for i, action in enumerate(actions, 1):
                print(f"\n  Action {i}:")
                print(f"    Tool: {action.get('tool_name')}")
                print(f"    Success: {action.get('success')}")
                print(f"    Hop: {action.get('hop_number')}")
                print(f"    Audit Notes: {action.get('audit_notes')}")
        else:
            print(f"\n⚡ ACTIONS TAKEN: 0")
        
        # Show hop breakdown
        print(f"\n📋 HOP BREAKDOWN:")
        for i, hop in enumerate(result.get("hops", []), 1):
            print(f"\n  Hop {i}:")
            plan = hop.get("plan", {})
            gather = hop.get("gather", {})
            coverage = hop.get("coverage", {})
            
            gather_tools = plan.get("gather_tool_calls", [])
            action_tools = plan.get("action_tool_calls", [])
            
            print(f"    Plan: {len(gather_tools)} gather tools, {len(action_tools)} action tools")
            print(f"    Gather: {len(gather.get('tool_results', []))} executed")
            print(f"    Coverage: next_node = {coverage.get('next_node', 'N/A')}")
            
            # Show if action was decided
            coverage_response = coverage.get("coverage_response", {})
            if coverage_response:
                # coverage_response is a Pydantic model stored as dict
                next_action = coverage_response.get("next_action") if isinstance(coverage_response, dict) else None
                action_tool_call = coverage_response.get("action_tool_call") if isinstance(coverage_response, dict) else None
                if next_action == "execute_action" and action_tool_call:
                    print(f"    🎯 Action Decided: {action_tool_call.get('tool_name') if isinstance(action_tool_call, dict) else 'N/A'}")
        
        # Show escalation info
        if result.get("escalate"):
            print(f"\n🚨 ESCALATED:")
            escalate_data = result.get("escalate", {})
            print(f"    Reason: {escalate_data.get('escalation_reason')}")
            print(f"    Note Added: {escalate_data.get('note_added')}")
        
        print("\n" + "=" * 80)
        print("💾 Full result saved to: test_result.json")
        print("=" * 80)
        
        # Save full result to file
        with open("test_result.json", "w") as f:
            json.dump(result, f, indent=2, default=str)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

