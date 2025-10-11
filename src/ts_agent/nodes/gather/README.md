# Gather Node

The gather node is responsible for executing all the tool calls planned by the plan node and storing the results in the global state.

## Purpose

The gather node:
1. Takes tool calls from the plan node
2. Executes each tool call using the MCP tools
3. Stores all results in the global state
4. Provides execution statistics and error handling

## Input

- `tool_calls`: List of tool calls from the plan node
- `user_email`: User's email address (from state)
- `context`: Additional context (from state)

## Output

The gather node adds the following to the global state:

### Execution Results
- `tool_results`: List of all tool execution results
- `successful_tools`: Names of successfully executed tools
- `failed_tools`: Names of tools that failed
- `total_execution_time_ms`: Total execution time
- `success_rate`: Success rate (0.0-1.0)
- `execution_status`: "completed" or "failed"

### Individual Tool Data
- `{tool_name}_data`: Individual tool results stored with tool name as key
  - Example: `get_user_applications_data`, `search_talent_docs_data`

## Tool Execution

The gather node executes tools in the following order:

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
- `search_talent_docs` - Search documentation (query, threshold, limit)
- `get_talent_docs_stats` - System statistics (no parameters)

## Error Handling

The gather node handles errors gracefully:
- **Tool validation errors**: Invalid tool names or parameters
- **Execution errors**: Network issues, API errors, timeouts
- **Data conversion errors**: Issues converting responses to dictionaries

Each tool execution is wrapped in try-catch, so one failed tool doesn't stop the others.

## Execution Flow

1. **Validate tool calls** - Check tool names and parameters
2. **Execute tools sequentially** - Run each tool with proper error handling
3. **Store results** - Save all results to global state
4. **Generate statistics** - Calculate success rates and timing
5. **Update state** - Mark execution as completed

## Example Execution

```python
# Input state from plan node
state = {
    "tool_calls": [
        {
            "tool_name": "get_user_applications",
            "parameters": {"user_email": "user@example.com"},
            "reasoning": "Get user's applications"
        },
        {
            "tool_name": "search_talent_docs", 
            "parameters": {"query": "interview tips", "threshold": 0.7, "limit": 5},
            "reasoning": "Find relevant documentation"
        }
    ]
}

# After gather node execution
state = {
    "tool_results": [...],  # Detailed results
    "successful_tools": ["get_user_applications", "search_talent_docs"],
    "failed_tools": [],
    "total_execution_time_ms": 2500.0,
    "success_rate": 1.0,
    "execution_status": "completed",
    "get_user_applications_data": {...},  # Individual tool data
    "search_talent_docs_data": {...}
}
```

## Performance

- **Sequential execution**: Tools are executed one at a time
- **Timing tracking**: Each tool's execution time is measured
- **Error isolation**: Failed tools don't affect successful ones
- **State management**: All results are stored for easy access by subsequent nodes
