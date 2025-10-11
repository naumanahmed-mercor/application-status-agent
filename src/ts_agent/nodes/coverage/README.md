# Coverage Node

The coverage node analyzes whether we have sufficient data to respond to the user's query and manages the loop counter to prevent infinite loops.

## Purpose

The coverage node:
1. Analyzes gathered data against the original user query
2. Determines if we have sufficient information to respond
3. Manages the hop counter to prevent infinite loops
4. Routes to the next appropriate node (plan, respond, or escalate)

## Input

- `user_query`: Original user query from state
- `tool_results`: Results from executed tools
- `successful_tools`: Names of successfully executed tools
- `failed_tools`: Names of failed tools
- `hops`: Current hop counter
- `max_hops`: Maximum allowed hops (default: 2)

## Output

The coverage node adds the following to the global state:

### Coverage Analysis
- `coverage_analysis`: Complete coverage analysis results
- `data_sufficient`: Boolean indicating if data is sufficient
- `missing_data`: List of identified data gaps
- `coverage_reasoning`: Reasoning for the coverage assessment
- `needs_more_data`: Whether more data gathering is needed

### Loop Management
- `hops`: Updated hop counter (incremented by 1)
- `max_hops`: Maximum allowed hops (default: 2)

### Routing Decision
- `next_node`: Next node to execute ("plan", "respond", "escalate")
- `escalation_reason`: Reason for escalation if needed

## Coverage Analysis Process

### 1. Data Assessment
The node uses an LLM to analyze:
- **Available data**: What information we have from executed tools
- **Data quality**: Whether the data is sufficient and relevant
- **Missing gaps**: What additional information would be helpful
- **Coverage score**: Overall assessment (0.0-1.0)

### 2. Gap Identification
Identifies specific data gaps with:
- **Gap type**: Category of missing data
- **Description**: What specific information is missing
- **Priority**: Importance level (1=critical, 5=optional)
- **Suggested tools**: Tools that could provide this data

### 3. Routing Decision
Based on analysis, determines next action:
- **"continue"**: Data is sufficient, proceed to response
- **"gather_more"**: Need more data, return to planning
- **"escalate"**: Cannot gather sufficient data, escalate to human

## Loop Management

### Hop Counter
- **Increments** the hop counter on each coverage analysis
- **Tracks** progress through planning/execution cycles
- **Prevents** infinite loops by limiting to max_hops (default: 2)

### Loop Limits
- **Max hops**: 2 (configurable)
- **Exceeded limit**: Automatically escalates to human team
- **Escalation reason**: "Exceeded maximum hops"

## Context-Aware Planning

When routing back to the plan node, the coverage node provides:
- **Previous tool results**: What tools were already executed
- **Failed tools**: Tools that didn't work
- **Data gaps**: Specific missing information
- **Coverage analysis**: Previous assessment results
- **Hop information**: Current cycle count

This allows the plan node to:
- **Avoid repeating** successful tools
- **Focus on gaps** identified by coverage analysis
- **Try different approaches** for failed tools
- **Make informed decisions** about additional data needs

## Example Coverage Analysis

```python
# Input: User asks "What's my application status?"
# Tools executed: get_user_applications, get_user_applications_detailed

coverage_analysis = {
    "coverage_score": 1.0,
    "data_sufficient": True,
    "available_data": ["applications", "application_details"],
    "missing_data": [],
    "reasoning": "We have comprehensive application data",
    "confidence": 0.9
}

# Result: next_node = "continue"
```

## Example Insufficient Data

```python
# Input: User asks "Tell me about my background check and interview history"
# Tools executed: get_user_background_status (failed), get_user_interviews

coverage_analysis = {
    "coverage_score": 0.5,
    "data_sufficient": False,
    "available_data": ["interviews"],
    "missing_data": [
        {
            "gap_type": "background_status",
            "description": "Background check status information",
            "suggested_tools": ["get_user_background_status"],
            "priority": 2
        }
    ],
    "reasoning": "Missing critical background check data",
    "confidence": 0.8
}

# Result: next_node = "plan" (if hops < max_hops)
```

## Error Handling

The coverage node handles:
- **JSON parsing errors**: Extracts JSON from LLM responses
- **Analysis failures**: Escalates when coverage analysis fails
- **Loop exhaustion**: Escalates when max hops exceeded
- **Data quality issues**: Identifies and reports data problems

## Performance

- **LLM-based analysis**: Uses structured output for consistent results
- **Efficient routing**: Quick decision making for next steps
- **Loop prevention**: Prevents infinite planning cycles
- **Context preservation**: Maintains state across planning cycles
