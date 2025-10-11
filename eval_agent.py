#!/usr/bin/env python3
"""
Evaluation script for running the agent on specific conversations and collecting results.

Usage:
    python eval_agent.py <conversation_id> [<conversation_id2> ...]
    python eval_agent.py 215471174574005
    python eval_agent.py 215471174574005 215470699049129 215471210499353

Output:
    - Results appended to eval_results.csv
    - Each run adds a row with: conversation_id, messages, tool_calls, response
"""

import sys
import os
import csv
from datetime import datetime
from pathlib import Path
from multiprocessing import Pool

# Add both project root and src to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

# Load environment variables from .env
from dotenv import load_dotenv
load_dotenv(project_root / ".env")

# Set dry-run mode
os.environ["DRY_RUN"] = "true"

# Verify environment setup
langsmith_key = os.getenv("LANGSMITH_API_KEY", "NOT_SET")
if langsmith_key == "NOT_SET":
    print("⚠️  WARNING: LANGSMITH_API_KEY not set\n")
else:
    print(f"✅ LangSmith API Key configured\n")

from ts_agent.runner import run_agent_with_conversation_id


def extract_messages(result: dict) -> str:
    """Extract conversation messages as readable text."""
    messages = []
    
    # Get messages from state
    state_messages = result.get("messages", [])
    if state_messages:
        for msg in state_messages:
            if isinstance(msg, dict):
                role = msg.get("role", "user")
                content = msg.get("content", "")
                # Replace newlines with space for CSV compatibility
                content = content.replace("\n", " ").replace("\r", " ")
                messages.append(f"{role}: {content}")
    
    return " | ".join(messages) if messages else "No messages"


def extract_tool_calls(result: dict) -> str:
    """Extract all tool calls across hops."""
    tool_calls = []
    
    hops = result.get("hops", [])
    for hop_idx, hop in enumerate(hops):
        if "plan" in hop and "tool_calls" in hop["plan"]:
            calls = hop["plan"]["tool_calls"]
            if isinstance(calls, list):
                for call in calls:
                    if isinstance(call, dict):
                        tool_name = call.get("tool_name", "unknown")
                        tool_calls.append(f"[Hop {hop_idx + 1}] {tool_name}")
    
    return ", ".join(tool_calls) if tool_calls else "No tools"


def extract_response(result: dict) -> str:
    """Extract the final response text."""
    draft = result.get("draft")
    if draft and isinstance(draft, dict):
        response = draft.get("response", "")
        response_type = draft.get("response_type", "UNKNOWN")
        # Replace newlines with space for CSV compatibility
        response = response.replace("\n", " ").replace("\r", " ")
        return f"[{response_type}] {response}"
    
    response = result.get("response", "No response")
    response = response.replace("\n", " ").replace("\r", " ")
    return response


def extract_escalation(result: dict) -> str:
    """Extract escalation reason if any."""
    escalation = result.get("escalation_reason")
    if escalation:
        # Replace newlines with space for CSV compatibility
        escalation = escalation.replace("\n", " ").replace("\r", " ")
        return escalation
    return ""


def extract_hops_count(result: dict) -> int:
    """Extract number of hops."""
    hops = result.get("hops", [])
    return len(hops)


def extract_error(result: dict) -> str:
    """Extract error if any."""
    error = result.get("error")
    if error:
        # Replace newlines with space for CSV compatibility
        error = error.replace("\n", " ").replace("\r", " ")
        return error
    return ""


def process_conversation(conv_id: str) -> dict:
    """Process a single conversation. This function can be run in parallel."""
    print(f"\n{'='*80}")
    print(f"🔍 [Worker] Evaluating conversation: {conv_id}")
    print(f"{'='*80}\n")
    
    try:
        # Run agent
        result = run_agent_with_conversation_id(conv_id)
        
        # Extract data
        timestamp = datetime.now().isoformat()
        user_email = result.get("user_email", "")
        messages = extract_messages(result)
        tool_calls = extract_tool_calls(result)
        response = extract_response(result)
        escalation = extract_escalation(result)
        hops = extract_hops_count(result)
        error = extract_error(result)
        
        print(f"✅ [Worker] Successfully evaluated {conv_id}")
        print(f"   User: {user_email if user_email else 'N/A'}")
        print(f"   Hops: {hops}")
        print(f"   Tool Calls: {tool_calls[:150]}{'...' if len(tool_calls) > 150 else ''}")
        draft = result.get('draft') or {}
        print(f"   Response Type: {draft.get('response_type', 'N/A')}")
        
        if escalation:
            print(f"   ⚠️  Escalated: {escalation[:150]}{'...' if len(escalation) > 150 else ''}")
        
        if error:
            print(f"   ❌ Error: {error[:150]}{'...' if len(error) > 150 else ''}")
        
        return {
            "timestamp": timestamp,
            "conversation_id": conv_id,
            "user_email": user_email,
            "messages": messages,
            "tool_calls": tool_calls,
            "response": response,
            "escalation_reason": escalation,
            "hops": hops,
            "error": error,
            "success": True
        }
        
    except Exception as e:
        print(f"❌ [Worker] Failed to evaluate {conv_id}: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "conversation_id": conv_id,
            "user_email": "",
            "messages": "",
            "tool_calls": "",
            "response": "",
            "escalation_reason": "",
            "hops": 0,
            "error": str(e)[:200],
            "success": False
        }


def run_evaluation(conversation_ids: list[str], output_file: str = "eval_results.csv", num_workers: int = 3):
    """Run agent on multiple conversations in parallel and save results to CSV."""
    
    # Check if file exists to determine if we need headers
    file_exists = Path(output_file).exists()
    
    print(f"\n🚀 Starting evaluation with {num_workers} parallel workers\n")
    
    # Process conversations in parallel
    with Pool(processes=num_workers) as pool:
        results = pool.map(process_conversation, conversation_ids)
    
    # Write all results to CSV
    with open(output_file, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Write header if file is new
        if not file_exists:
            writer.writerow([
                "timestamp",
                "conversation_id",
                "user_email",
                "messages",
                "tool_calls",
                "response",
                "escalation_reason",
                "hops",
                "error"
            ])
        
        # Write all results
        for result in results:
            writer.writerow([
                result["timestamp"],
                result["conversation_id"],
                result["user_email"],
                result["messages"],
                result["tool_calls"],
                result["response"],
                result["escalation_reason"],
                result["hops"],
                result["error"]
            ])
    
    print(f"\n{'='*80}")
    print(f"✅ Results saved to: {output_file}")
    print(f"   Total: {len(results)} conversations")
    print(f"   Success: {sum(1 for r in results if r['success'])}")
    print(f"   Failed: {sum(1 for r in results if not r['success'])}")
    print(f"{'='*80}\n")


def main():
    if len(sys.argv) < 2:
        print("Usage: python eval_agent.py <conversation_id> [<conversation_id2> ...] [--workers N]")
        print("\nExamples:")
        print("  python eval_agent.py 215471174574005")
        print("  python eval_agent.py 215471174574005 215470699049129 215471210499353")
        print("  python eval_agent.py 215471174574005 --workers 5")
        sys.exit(1)
    
    # Parse arguments
    args = sys.argv[1:]
    num_workers = 3  # default
    conversation_ids = []
    
    i = 0
    while i < len(args):
        if args[i] == "--workers" and i + 1 < len(args):
            num_workers = int(args[i + 1])
            i += 2
        else:
            conversation_ids.append(args[i])
            i += 1
    
    if not conversation_ids:
        print("Error: No conversation IDs provided")
        sys.exit(1)
    
    print(f"\n🧪 DRY RUN MODE - Evaluating {len(conversation_ids)} conversation(s)\n")
    
    run_evaluation(conversation_ids, num_workers=num_workers)


if __name__ == "__main__":
    main()

