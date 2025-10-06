# Plan Node

The plan node is responsible for analyzing user queries and creating execution plans for the agent.

## Purpose

Given a user's question or request, the plan node:
1. Analyzes what information the user needs
2. Determines which MCP tools can provide that information
3. Creates a structured plan with tool calls and parameters
4. Validates that all required parameters are provided

## Input

- `user_query`: The user's question or request
- `user_email`: User's email address (optional)
- `context`: Additional context (optional)

## Output

- `plan`: Complete execution plan
- `tool_calls`: List of tools to execute with parameters
- `reasoning`: Explanation of why this plan was created
- `needs_user_email`: Whether user email is required
- `response_strategy`: How to respond to the user

## Available Tools

The plan node can select from these MCP tools:

### User Data Tools (require user_email)
- `get_user_background_status` - Background check status
- `get_user_applications` - List of job applications
- `get_user_applications_detailed` - Detailed application info
- `get_user_jobs` - Current jobs and employment
- `get_user_interviews` - Interview history
- `get_user_work_trials` - Work trial history
- `get_user_fraud_reports` - Fraud report status
- `get_user_details` - Basic user profile

### Documentation Tools
- `search_talent_docs` - Search documentation (requires query, threshold, limit)
- `get_talent_docs_stats` - System statistics (no parameters)

## Example Plans

### Application Status Query
```json
{
  "tool_calls": [
    {
      "tool_name": "get_user_applications",
      "parameters": {"user_email": "user@example.com"},
      "reasoning": "Get list of applications"
    },
    {
      "tool_name": "get_user_applications_detailed", 
      "parameters": {"user_email": "user@example.com"},
      "reasoning": "Get detailed application information"
    }
  ]
}
```

### Documentation Search
```json
{
  "tool_calls": [
    {
      "tool_name": "search_talent_docs",
      "parameters": {
        "query": "interview process",
        "threshold": 0.7,
        "limit": 5
      },
      "reasoning": "Find relevant documentation"
    }
  ]
}
```

## Validation

The plan node validates:
- Tool names exist in available tools list
- Required parameters are provided for each tool
- Parameter types are correct (e.g., threshold is number)
- User email is provided for user data tools

## Error Handling

- Invalid tool names raise `ValueError`
- Missing required parameters raise `ValueError`
- Invalid parameter types raise `ValueError`
- JSON parsing errors are caught and re-raised
