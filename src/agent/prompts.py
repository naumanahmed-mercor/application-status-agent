"""
LangSmith prompts collection and client.
All LLM prompts are stored in LangSmith and fetched at runtime.
"""

import os
from langsmith import Client


class LangSmithPromptClient:
    """Client for fetching prompts from LangSmith at runtime."""
    
    def __init__(self):
        """Initialize LangSmith client."""
        self.client = Client()
        self.project_name = os.getenv("LANGSMITH_PROJECT", "application-status-agent")
        
    def get_prompt(self, prompt_name: str) -> str:
        """
        Fetch a prompt from LangSmith by name.
        
        Args:
            prompt_name: Name of the prompt in LangSmith
            
        Returns:
            Prompt template string
            
        Raises:
            Exception: If prompt cannot be fetched from LangSmith
        """
        try:
            # Pull the prompt from LangSmith
            prompt = self.client.pull_prompt(prompt_name)
            
            # Handle different prompt types
            if hasattr(prompt, 'template'):
                # Direct template access
                return prompt.template
            elif hasattr(prompt, 'content'):
                # Direct content access
                return prompt.content
            elif hasattr(prompt, 'messages') and prompt.messages:
                # Chat prompt with messages
                if hasattr(prompt.messages[0], 'prompt') and hasattr(prompt.messages[0].prompt, 'template'):
                    return prompt.messages[0].prompt.template
                elif hasattr(prompt.messages[0], 'content'):
                    return prompt.messages[0].content
                else:
                    return str(prompt.messages[0])
            elif hasattr(prompt, 'prompt') and hasattr(prompt.prompt, 'template'):
                # SystemMessagePromptTemplate case
                return prompt.prompt.template
            elif isinstance(prompt, dict):
                return prompt.get('template', prompt.get('content', str(prompt)))
            else:
                return str(prompt)
        except Exception as e:
            raise Exception(f"Failed to fetch prompt '{prompt_name}' from LangSmith: {e}")


# Global prompt client instance
prompt_client = LangSmithPromptClient()


def get_prompt(prompt_name: str) -> str:
    """
    Get a prompt by name from LangSmith.
    
    Args:
        prompt_name: Name of the prompt
        
    Returns:
        Prompt template string
    """
    return prompt_client.get_prompt(prompt_name)


# Prompt names used throughout the system (matching LangSmith names)
PROMPT_NAMES = {
    "PLAN_NODE": "agent-plan-prompt",
    "COVERAGE_NODE": "agent-coverage-prompt", 
    "DRAFT_NODE": "agent-draft-prompt"
}
