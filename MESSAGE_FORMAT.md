# Message Format Specification

## Overview
The agent now supports multi-message conversations instead of single queries. This allows for back-and-forth conversations between the user and the agent.

## Message Structure

### Individual Message Format
```json
{
  "role": "user" | "assistant",
  "content": "The message content"
}
```

### Message Array Format
```json
{
  "messages": [
    {
      "role": "user",
      "content": "I want to withdraw my application"
    },
    {
      "role": "assistant", 
      "content": "I understand you'd like to withdraw your application. Let me check your current applications..."
    },
    {
      "role": "user",
      "content": "Yes, I want to withdraw my Software Engineer application at Company X"
    }
  ],
  "user_email": "user@example.com"
}
```

## Field Specifications

### Required Fields
- **`role`**: `"user"` or `"assistant"` - Who sent the message
- **`content`**: `string` - The actual message text

## Usage Examples

### Single Message
```json
{
  "messages": [
    {
      "role": "user",
      "content": "I want to withdraw my application"
    }
  ],
  "user_email": "user@example.com"
}
```

### Full Conversation Context
```json
{
  "messages": [
    {
      "role": "user",
      "content": "What's the status of my applications?"
    },
    {
      "role": "assistant",
      "content": "You have 2 applications: Software Engineer at Company A (Interview Scheduled) and Data Scientist at Company B (Under Review)."
    },
    {
      "role": "user", 
      "content": "I want to withdraw the Software Engineer one"
    }
  ],
  "user_email": "user@example.com"
}
```

## Implementation Notes

1. **Always Array**: Always expects `messages` array, no single message support
2. **Latest User Message**: The agent processes the most recent user message as the primary query
3. **Context Awareness**: All previous messages provide context for better responses
4. **State Management**: Conversation history is maintained in the agent's state
5. **Tool Execution**: Only the latest user message triggers tool execution, but context influences planning

## API Endpoints

### LangGraph Server
```bash
# Always use messages array
curl -X POST http://localhost:8123/threads \
  -H "Content-Type: application/json" \
  -d '{"input": {"messages": [{"role": "user", "content": "Hello"}], "user_email": "user@example.com"}}'
```

### Direct Runner
```python
from src.agent.runner import run_agent_with_messages

# Single message
result = run_agent_with_messages([
    {"role": "user", "content": "Hello"}
], "user@example.com")

# Multi-message conversation
result = run_agent_with_messages([
    {"role": "user", "content": "Hello"},
    {"role": "assistant", "content": "Hi! How can I help?"},
    {"role": "user", "content": "What's my application status?"}
], "user@example.com")
```
