#!/usr/bin/env python3
"""CLI script to run the application status agent."""

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ts_agent.runner import run_agent
from ts_agent.types import AgentInput


def main():
    """Main CLI function."""
    if len(sys.argv) != 2:
        print("Usage: python run_agent.py '<user_message>'")
        print("Example: python run_agent.py 'Status of my SWE app?'")
        sys.exit(1)
    
    user_msg = sys.argv[1]
    
    # For testing, you can modify these or pass them as arguments
    user_id = None
    email = None
    
    # You can also set these via environment variables or command line args
    import os
    if os.getenv("USER_ID"):
        user_id = os.getenv("USER_ID")
    if os.getenv("EMAIL"):
        email = os.getenv("EMAIL")
    
    inp = AgentInput(user_msg=user_msg, user_id=user_id, email=email)
    
    try:
        result = run_agent(inp)
        print(result.model_dump_json(indent=2))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
