# Agent State Structure

This document provides a detailed breakdown of the agent's state structure.

## Overview

The agent uses a TypedDict-based state that flows through all nodes. The state is divided into several sections:

---

## Input Fields

### Primary Input
- **`conversation_id`**: Intercom conversation ID (required)
  - This is the only required input field
  - Used to fetch conversation data and user email from Intercom

### Derived Fields
- **`messages`**: Array of conversation messages
  - Format: `[{"role": "user|assistant", "content": "..."}]`
  - Fetched from Intercom during initialization
  - Bot messages mapped to "assistant" role

- **`user_email`**: User's email address
  - Fetched from Intercom contact data
  - Used for MCP tool calls

- **`melvin_admin_id`**: Melvin bot admin ID
  - Loaded from `MELVIN_ADMIN_ID` environment variable
  - Used for all Intercom actions (notes, messages, snooze)

- **`timestamp`**: Workflow start timestamp

---

## MCP Integration

- **`available_tools`**: List of available tools from MCP server
  - Fetched during initialization
  - Contains tool definitions (name, description, parameters)

---

## Data Storage (Accumulated Across Hops)

### Tool Data
- **`tool_data`**: Dictionary of individual tool results
  - Key: Tool name (e.g., `"get_user_applications_detailed"`)
  - Value: Tool execution result
  - Accumulates across hops (not overwritten)

### Documentation Data
- **`docs_data`**: Dictionary of individual documentation search results
  - Key: Search query + hop number (e.g., `"payment policies (hop 1)"`)
  - Value: Documentation search result
  - Accumulates across hops with unique keys per hop

---

## Loop Management

### Hops Array
- **`hops`**: Array of hop data structures
  - Each hop represents one iteration of Plan → Gather → Coverage
  - Maximum 2 hops by default

- **`max_hops`**: Maximum allowed hops (default: 2)

### Hop Structure
Each element in the `hops` array contains:

#### Plan Data
```
{
  "plan": {
    "user_query": "extracted user query",
    "reasoning": "why these tools were chosen",
    "tool_calls": [
      {
        "tool_name": "tool name",
        "parameters": {"param": "value"},
        "reasoning": "why this specific tool"
      }
    ]
  }
}
```

#### Gather Data
```
{
  "gather": {
    "tool_results": [
      {
        "tool_name": "tool name",
        "success": true,
        "data": [/* tool response */],
        "error": null,
        "execution_time_ms": 1500,
        "timestamp": "ISO timestamp"
      }
    ],
    "total_execution_time_ms": 3000,
    "success_rate": 1.0,
    "execution_status": "completed"
  }
}
```

#### Coverage Data
```
{
  "coverage": {
    "coverage_analysis": {
      "user_query": "query",
      "data_sufficient": true,
      "coverage_score": 0.95,
      "available_data": ["list", "of", "data"],
      "missing_data": [
        {
          "gap_type": "type",
          "description": "what's missing"
        }
      ],
      "reasoning": "analysis reasoning",
      "confidence": 0.9
    },
    "data_sufficient": true,
    "next_node": "respond",
    "escalation_reason": null
  }
}
```

---

## Post-Loop Nodes

These nodes execute after the Plan → Gather → Coverage loop completes.

### Draft Node
- **`draft`**: Draft node data
  ```
  {
    "response": "generated response text",
    "response_type": "REPLY" | "ROUTE_TO_TEAM",
    "generation_time_ms": 25000,
    "timestamp": "ISO timestamp"
  }
  ```

### Validate Node
- **`validate`**: Validation node data
  ```
  {
    "validation_response": {/* raw validation response */},
    "overall_passed": true,
    "validation_note_added": true,
    "escalation_reason": null,
    "next_action": "response"
  }
  ```

### Escalate Node
- **`escalate`**: Escalation node data
  ```
  {
    "escalation_source": "coverage" | "validate" | "draft" | "initialization",
    "escalation_reason": "reason for escalation",
    "note_added": true,
    "timestamp": "ISO timestamp"
  }
  ```

### Response Node
- **`response_delivery`**: Response delivery data
  ```
  {
    "delivery_attempted": true,
    "delivery_successful": true,
    "delivery_error": null,
    "delivery_time_ms": 1200,
    "status_updated": false
  }
  ```

### Finalize Node
- **`finalize`**: Finalization data
  ```
  {
    "melvin_status": "success" | "route_to_team" | "validation_failed" | ...,
    "status_updated": true,
    "conversation_snoozed": true,
    "snooze_duration_seconds": 300,
    "error": null
  }
  ```

---

## Routing Fields

- **`next_node`**: Next node to route to
  - Set by nodes to control workflow
  - Values: `"plan"`, `"gather"`, `"coverage"`, `"draft"`, `"validate"`, `"escalate"`, `"response"`, `"finalize"`, `"end"`

- **`escalation_reason`**: Reason for escalation
  - Set when escalation is triggered
  - Used by escalate and finalize nodes

---

## Output Fields

- **`response`**: Final response text sent to user
  - Set by draft node
  - Delivered by response node

- **`error`**: Error message if any
  - Set by any node that encounters an error
  - Used for escalation

---

## Intercom Configuration

- **`metadata`**: Additional metadata for Intercom
  - Currently unused but available for future extensions

---

## State Flow Example

### Simple Query (1 hop, successful):
```
1. Initialize:
   - conversation_id: "123"
   - messages: [...]
   - user_email: "user@example.com"
   - available_tools: [...]

2. Plan (Hop 1):
   - hops[0].plan: {tool_calls: [...]}

3. Gather (Hop 1):
   - hops[0].gather: {tool_results: [...]}
   - tool_data: {"get_user_applications": [...]}

4. Coverage (Hop 1):
   - hops[0].coverage: {data_sufficient: true, next_node: "respond"}

5. Draft:
   - draft: {response: "...", response_type: "REPLY"}
   - response: "..."

6. Validate:
   - validate: {overall_passed: true}

7. Response:
   - response_delivery: {delivery_successful: true}

8. Finalize:
   - finalize: {melvin_status: "success", conversation_snoozed: true}
```

### Complex Query (2 hops, escalation):
```
1. Initialize:
   - conversation_id: "456"
   - messages: [...]
   - user_email: "user@example.com"

2. Plan (Hop 1):
   - hops[0].plan: {tool_calls: [tool1, tool2]}

3. Gather (Hop 1):
   - hops[0].gather: {tool_results: [...]}
   - tool_data: {tool1: [...], tool2: [...]}

4. Coverage (Hop 1):
   - hops[0].coverage: {data_sufficient: false, next_node: "plan"}

5. Plan (Hop 2):
   - hops[1].plan: {tool_calls: [tool3, tool4]}

6. Gather (Hop 2):
   - hops[1].gather: {tool_results: [...]}
   - tool_data: {tool1: [...], tool2: [...], tool3: [...], tool4: [...]}

7. Coverage (Hop 2):
   - hops[1].coverage: {data_sufficient: false, next_node: "escalate"}
   - escalation_reason: "Exceeded maximum hops (2)"

8. Escalate:
   - escalate: {escalation_source: "coverage", note_added: true}

9. Finalize:
   - finalize: {melvin_status: "route_to_team", conversation_snoozed: true}
```

---

## Key Design Principles

1. **Immutability of Hop Data**: Once a hop is completed, its data is never modified
2. **Accumulation, Not Replacement**: `tool_data` and `docs_data` accumulate across hops
3. **Separation of Tools and Docs**: Different storage for user data vs documentation
4. **Post-Loop Independence**: Draft, validate, escalate nodes are stored at top level, not in hops
5. **State Always Valid**: Every node ensures state remains consistent even on error

