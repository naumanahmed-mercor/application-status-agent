# Agent Architecture

## Overview

The Application Status Agent is a conversational AI system designed to help users with queries about their job applications, payments, and other talent-related questions. It uses an agentic workflow to gather information, analyze coverage, and provide accurate responses.

## High-Level Flow

```
Intercom Conversation → Initialize → [Plan → Gather → Coverage] Loop → Draft → Validate → Response → Finalize
                                          ↓                                      ↓          ↓
                                      Escalate ←────────────────────────────────┘          │
                                          │                                                 │
                                          └─────────────────────────────────────────────────┘
```

## Data Sources

The agent connects to two primary data sources:

- **MCP Server**: Provides tools to fetch user data (applications, jobs, payments, etc.)
- **Vector Store for Talent Docs**: RAG system for searching internal documentation

---

## Nodes

### 1. Initialize

**Purpose**: Fetch conversation data from Intercom and set up the agent.

**Responsibilities**:
- Fetch conversation messages and user email from Intercom
- Initialize MCP client and fetch available tools
- Set up initial state (hops array, max_hops, etc.)
- Load Melvin admin ID from environment

**Triggers**: Always the first node when agent is invoked

**Next Nodes**:
- `Plan` - If initialization successful
- `Escalate` - If Intercom or MCP connection fails

---

### 2. Plan

**Purpose**: Analyze the user query and decide which tools/docs to fetch.

**Responsibilities**:
- Understand user intent from conversation history
- Select appropriate MCP tools to execute
- Plan documentation searches for internal policies
- Consider previous hop results if in a loop (context-aware planning)
- Differentiate between tools (user data) and docs (policies/FAQs)

**Triggers**: 
- After Initialize (first hop)
- After Coverage determines more data is needed (subsequent hops)

**Next Nodes**:
- `Gather` - Always proceeds to execute the plan

**Key Features**:
- Can plan multiple `search_talent_docs` queries in a single hop
- Prioritizes documentation searches for internal process questions
- Uses conversation history for context-aware planning

---

### 3. Gather

**Purpose**: Execute all tool calls and documentation searches planned by the Plan node.

**Responsibilities**:
- Execute MCP tool calls in parallel
- Fetch documentation from vector store
- Store results in state (`tool_data` and `docs_data`)
- Accumulate data across hops (not overwrite)
- Handle tool execution errors gracefully

**Triggers**: After Plan node completes

**Next Nodes**:
- `Coverage` - Always proceeds to analyze data sufficiency

**Key Features**:
- Handles queries that don't require tools (e.g., "Hi")
- Stores tool data and docs data separately
- Accumulates results across hops for comprehensive context

---

### 4. Coverage

**Purpose**: Analyze if we have sufficient data to answer the user's query.

**Responsibilities**:
- Evaluate accumulated tool data and documentation
- Calculate coverage score (0-100%)
- Identify missing data gaps
- Decide next action: continue, gather more, or escalate
- Check hop limit (max 2 hops)

**Triggers**: After Gather node completes

**Next Nodes**:
- `Plan` - If data insufficient and hops not exhausted (loop back)
- `Draft` - If data sufficient
- `Escalate` - If hops exhausted or coverage analysis fails

**Decision Logic**:
```
If data_sufficient = true → Draft
If data_sufficient = false AND hop < max_hops → Plan (loop)
If data_sufficient = false AND hop >= max_hops → Escalate
```

---

### 5. Draft

**Purpose**: Generate a response to the user based on accumulated data.

**Responsibilities**:
- Create a comprehensive response using all tool data and documentation
- Format response for user consumption
- Determine response type: `REPLY` or `ROUTE_TO_TEAM`
- Handle contradictions in data (e.g., docs say withdrawal not possible)
- Ask clarifying questions only as last resort

**Triggers**: After Coverage determines data is sufficient

**Next Nodes**:
- `Validate` - If `response_type = REPLY`
- `Escalate` - If `response_type = ROUTE_TO_TEAM` or generation error

**Response Format**:
```json
{
  "text": "Generated response text",
  "response_type": "REPLY" | "ROUTE_TO_TEAM"
}
```

**Key Features**:
- LLM returns `text` field, converted to `response` internally
- Defaults to `REPLY` for backwards compatibility
- Direct, factual responses (not overly helpful)

---

### 6. Validate

**Purpose**: Validate the draft response against policy and intent classification.

**Responsibilities**:
- Send response to external validation endpoint
- Add validation results as Intercom note (raw JSON)
- Route based on validation result
- Handle validation errors gracefully

**Triggers**: After Draft node (only for `REPLY` type)

**Next Nodes**:
- `Response` - If `overall_passed = true`
- `Escalate` - If `overall_passed = false` or validation error

**Validation Note**: Always adds raw JSON validation response as note, even if parsing fails

---

### 7. Escalate

**Purpose**: Handle all escalation scenarios and prepare for human takeover.

**Responsibilities**:
- Determine escalation source
- Add escalation note to Intercom with reason
- Store escalation data in state

**Triggers**: Multiple scenarios (see Escalation Scenarios section below)

**Next Nodes**:
- `Finalize` - Always proceeds to cleanup

**Escalation Note Format**:
```
🚨 Escalation: {escalation_reason}
```

---

### 8. Response

**Purpose**: Deliver the validated response to the user via Intercom.

**Responsibilities**:
- Send response message to Intercom conversation
- Track delivery status and timing
- Handle delivery errors

**Triggers**: After Validate node (if validation passed)

**Next Nodes**:
- `Finalize` - Always proceeds to cleanup

---

### 9. Finalize

**Purpose**: Cleanup and final actions before ending the workflow.

**Responsibilities**:
- Determine and update Melvin Status custom attribute
- Snooze conversation for 5 minutes
- Store finalization data in state

**Triggers**: After Escalate or Response nodes

**Next Nodes**:
- `END` - Workflow terminates

**Melvin Status Mapping**:
| Scenario | Status |
|----------|--------|
| Response delivered successfully | `success` |
| User requested human | `ROUTE_TO_TEAM` |
| Validation failed | `VALIDATION_FAILED` |
| Draft generation error | `RESPONSE_FAILED` |
| Hops exhausted | `ROUTE_TO_TEAM` |
| Initialization failed | `error` |
| Message delivery failed | `MESSAGE_FAILED` |

---

## Escalation Scenarios

The agent can escalate in 7 different scenarios:

### 1. **Exhausted Hops** (Coverage)
- **When**: Coverage analysis shows insufficient data AND hop count reaches max (2)
- **Reason**: `"Exceeded maximum hops (2). Unable to gather sufficient data."`
- **Status**: `ROUTE_TO_TEAM`

### 2. **Route to Team** (Draft)
- **When**: User explicitly requests to talk to a human
- **Reason**: `"User requested to talk to a human"`
- **Status**: `ROUTE_TO_TEAM`

### 3. **Validation Failed** (Validate)
- **When**: Validation endpoint returns `overall_passed: false`
- **Reason**: `"Validation failed - see validation note for details"`
- **Status**: `VALIDATION_FAILED`

### 4. **Draft Generation Error** (Draft)
- **When**: Exception during response generation
- **Reason**: `"Draft generation error: {error}"`
- **Status**: `RESPONSE_FAILED`

### 5. **Initialization Failed** (Initialize)
- **When**: Failed to fetch from Intercom or initialize MCP
- **Reason**: `"Initialization failed: {error}"`
- **Status**: `error`

### 6. **Coverage Analysis Failed** (Coverage)
- **When**: Exception during coverage analysis (LLM failure, JSON parsing error)
- **Reason**: `"Coverage analysis failed: {error}"`
- **Status**: `error`

### 7. **Validation Error** (Validate)
- **When**: Exception while calling validation endpoint (network error, timeout)
- **Reason**: `"Validation error: {error}"`
- **Status**: `error`

---

## State Management

The agent uses a structured state to track data across nodes:

### Key State Fields:

- **`conversation_id`**: Intercom conversation ID (primary input)
- **`messages`**: Array of conversation messages (fetched from Intercom)
- **`user_email`**: User's email address
- **`melvin_admin_id`**: Melvin bot admin ID for Intercom actions

### Data Storage:

- **`tool_data`**: Individual tool results by tool name (accumulated across hops)
- **`docs_data`**: Individual docs results by query (accumulated across hops)

### Loop Management:

- **`hops`**: Array of hop data (each hop contains plan, gather, coverage)
- **`max_hops`**: Maximum allowed hops (default: 2)

### Post-Loop Nodes:

- **`draft`**: Draft node data (response, response_type, timing)
- **`validate`**: Validate node data (validation results, note status)
- **`escalate`**: Escalate node data (source, reason, note status)
- **`response_delivery`**: Response node data (delivery status, timing)
- **`finalize`**: Finalize node data (Melvin Status, snooze status)

---

## Configuration

### Environment Variables:

- `INTERCOM_API_KEY`: Intercom API key for conversation management
- `MELVIN_ADMIN_ID`: Melvin bot admin ID (default: `8918000`)
- `VALIDATION_ENDPOINT`: External validation service URL
- `VALIDATION_API_KEY`: API key for validation service
- `LANGSMITH_API_KEY`: LangSmith API key for prompt management
- `MODEL_NAME`: LLM model to use (e.g., `gpt-4o-mini`)

### Configurable Parameters:

- **Max Hops**: Default is 2, can be configured in state initialization
- **Snooze Duration**: Default is 5 minutes (300 seconds)

---

## Message Format

The agent expects messages in a specific format:

```json
{
  "role": "user" | "assistant",
  "content": "message text"
}
```

**Role Mapping from Intercom**:
- User messages → `"user"`
- Bot messages (Melvin) → `"assistant"`
- Admin messages → `"assistant"`
- Internal notes → Excluded

---

## Prompt Management

All LLM prompts are managed via LangSmith:

- **`agent-plan-prompt`**: Planning node prompt
- **`agent-coverage-prompt`**: Coverage analysis prompt
- **`agent-draft-prompt`**: Response generation prompt

Prompts are fetched at runtime (no caching) for easy updates and A/B testing.

---

## Integration Points

### Intercom:
- Fetch conversation data
- Send messages
- Add internal notes
- Update custom attributes (Melvin Status)
- Snooze conversations

### MCP Server:
- Execute tools (get user data)
- Search talent documentation (RAG)

### Validation Service:
- Validate draft responses
- Policy and intent classification

### LangSmith:
- Fetch prompts
- Track runs and metrics

---

## Key Design Decisions

1. **Separate Tool Data and Docs Data**: Tools fetch user-specific data, docs fetch policies/FAQs
2. **Accumulated State**: Data accumulates across hops, not overwritten
3. **Context-Aware Planning**: Plan node considers previous results when in a loop
4. **Bypass Validation for Route-to-Team**: No need to validate when routing to human
5. **Raw JSON Validation Notes**: Always add validation results to Intercom, even if parsing fails
6. **Bot Messages as Assistant**: Ensures conversation history is correctly attributed
7. **Direct State Access**: Coverage node accesses `state["hops"]` directly to ensure mutations persist

---

## Error Handling

All nodes implement graceful error handling:

- **Errors are logged** with detailed context
- **Escalation is triggered** for unrecoverable errors
- **Partial success is supported** (e.g., some tools fail, others succeed)
- **State is always updated** even on failure
- **Users always receive a response** (either from agent or via escalation to team)

