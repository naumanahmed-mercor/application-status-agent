"""LLM client for the application status agent."""

import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# Load environment variables from .env file
load_dotenv()


def planner_llm():
    """LLM for planning with structured output."""
    return ChatOpenAI(model=os.getenv("MODEL_NAME", "gpt-4o-mini"), temperature=0)


def drafter_llm():
    """LLM for drafting responses."""
    return ChatOpenAI(model=os.getenv("MODEL_NAME", "gpt-4o-mini"), temperature=0.2)
