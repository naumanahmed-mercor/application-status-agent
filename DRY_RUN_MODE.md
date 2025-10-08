# Dry-Run / Evaluation Mode

This document explains how to use the agent in **dry-run mode** to evaluate it on real conversations without making any changes to Intercom.

## What is Dry-Run Mode?

Dry-run mode allows you to:
- ✅ Run the agent on real conversations
- ✅ Test all logic, planning, and response generation
- ✅ See exactly what would be sent/updated
- ❌ **NO actual writes to Intercom** (messages, notes, custom attributes, snoozes)

This is perfect for:
- **Evaluation**: Test agent performance on real conversations
- **Development**: Debug and iterate without affecting production
- **Testing**: Validate changes before deployment
- **Analysis**: Compare agent responses to actual human responses

## How to Enable Dry-Run Mode

Simply set the `DRY_RUN` environment variable to `true`:

### Option 1: In .env file

```bash
# In your .env file
DRY_RUN=true
```

### Option 2: Command line

```bash
# For a single run
DRY_RUN=true python scripts/run_agent.py 215471174574005

# Or export for the session
export DRY_RUN=true
python scripts/run_agent.py 215471174574005
```

### Option 3: In code

```python
import os
os.environ["DRY_RUN"] = "true"
```

## What Gets Blocked in Dry-Run Mode

All Intercom write operations are blocked and logged instead:

### 1. Messages (send_message)
```
[DRY RUN] Would send message to conversation 215471174574005:
--- MESSAGE START ---
Hi James,

Thanks for reaching out! I can help you with that...
--- MESSAGE END ---
```

### 2. Notes (add_note)
```
[DRY RUN] Would add note to conversation 215471174574005: 
🔍 Response Validation Results...
```

### 3. Custom Attributes (update_conversation_custom_attribute)
```
[DRY RUN] Would update custom attribute on conversation 215471174574005: 
Melvin Status = success
```

### 4. Snooze Actions (snooze_conversation)
```
[DRY RUN] Would snooze conversation 215471174574005 until 2025-10-08 15:30:00 
(timestamp: 1728397800)
```

## What Still Works in Dry-Run Mode

These operations continue to work normally:

- ✅ **Read operations**: Fetching conversations, messages, user data
- ✅ **MCP tool calls**: Searching docs, getting applications, checking jobs
- ✅ **LLM calls**: Planning, drafting responses, coverage analysis
- ✅ **Validation**: Response validation via external API
- ✅ **State management**: All internal agent state tracking

## Example Usage

### Basic Evaluation Run

```bash
# Set dry-run mode
export DRY_RUN=true

# Run agent on a conversation
python scripts/run_agent.py 215471174574005

# Check logs to see what would have been sent
# All write operations will be logged with [DRY RUN] prefix
```

### Batch Evaluation

```python
import os
from agent.runner import run_agent

# Enable dry-run mode
os.environ["DRY_RUN"] = "true"

# List of conversation IDs to evaluate
conversation_ids = [
    "215471174574005",
    "215471174574006",
    "215471174574007",
]

results = []
for conv_id in conversation_ids:
    print(f"\n{'='*80}")
    print(f"Evaluating conversation: {conv_id}")
    print(f"{'='*80}\n")
    
    result = run_agent(conv_id)
    results.append({
        "conversation_id": conv_id,
        "response": result.get("response"),
        "final_state": result.get("state"),
    })

# Analyze results
for r in results:
    print(f"\nConversation: {r['conversation_id']}")
    print(f"Response: {r['response'][:100]}...")
```

### Compare with Actual Response

```python
import os
from agent.runner import run_agent
from clients.intercom import IntercomClient

# Get the real conversation
client = IntercomClient(os.getenv("INTERCOM_API_KEY"))
real_conversation = client.get_conversation("215471174574005")

# Get last actual response (if any)
actual_response = None
for part in real_conversation.get("conversation_parts", {}).get("conversation_parts", []):
    if part.get("part_type") == "comment" and part.get("author", {}).get("type") == "admin":
        actual_response = part.get("body")

# Run agent in dry-run mode
os.environ["DRY_RUN"] = "true"
result = run_agent("215471174574005")
agent_response = result.get("response")

# Compare
print("ACTUAL RESPONSE:")
print(actual_response)
print("\n" + "="*80 + "\n")
print("AGENT RESPONSE (DRY RUN):")
print(agent_response)
```

## Verifying Dry-Run Mode is Active

When dry-run mode is active, you'll see this warning at the start:

```
⚠️  IntercomClient: DRY RUN MODE - No write operations will be executed
```

If you don't see this warning, dry-run mode is **NOT** active and writes will go through!

## Disabling Dry-Run Mode

To return to normal operation:

### Option 1: Update .env
```bash
# In your .env file
DRY_RUN=false
# OR simply remove the line
```

### Option 2: Unset environment variable
```bash
unset DRY_RUN
```

### Option 3: Explicitly set to false
```bash
export DRY_RUN=false
python scripts/run_agent.py 215471174574005
```

## Implementation Details

Dry-run mode is implemented in the `IntercomClient` class:

```python
class IntercomClient:
    def __init__(self, api_key: str):
        import os
        self.api_key = api_key
        
        # Check for dry-run mode from environment variable
        self.dry_run = os.getenv("DRY_RUN", "false").lower() in ("true", "1", "yes")
        
        if self.dry_run:
            logger.warning("⚠️  IntercomClient: DRY RUN MODE - No write operations will be executed")
```

All write methods check `self.dry_run` before executing:

```python
def send_message(self, conversation_id: str, message_body: str, admin_id: str):
    if self.dry_run:
        logger.info(f"[DRY RUN] Would send message to conversation {conversation_id}...")
        return {"type": "conversation", "id": conversation_id, "dry_run": True}
    
    # Normal execution...
```

## Tips for Evaluation

1. **Enable verbose logging** to see all dry-run operations:
   ```python
   import logging
   logging.basicConfig(level=logging.INFO)
   ```

2. **Save agent outputs** for comparison:
   ```python
   with open(f"eval_results_{conv_id}.json", "w") as f:
       json.dump(result, f, indent=2)
   ```

3. **Check LangSmith traces** - dry-run mode doesn't affect tracing

4. **Test edge cases** - use dry-run to test unusual conversations safely

5. **Validate before deployment** - always run a batch evaluation in dry-run mode before deploying changes

## Safety Notes

- ⚠️ **Always verify** the warning message appears when starting
- ⚠️ **Double-check** your .env file before running in production
- ⚠️ **Read operations still work** - the agent can still see real conversation data
- ⚠️ **External APIs may still be called** - MCP tools, validation endpoints, etc.

## Troubleshooting

### Dry-run mode not activating

Check these:
1. Is `DRY_RUN=true` in your .env file?
2. Is the .env file in the correct location?
3. Are you loading environment variables? (`load_dotenv()`)
4. Check for typos: `DRY_RUN` not `DRYRUN` or `DRY-RUN`

### Still seeing writes to Intercom

If writes are still happening:
1. Check the logs for the warning message
2. Verify the environment variable: `echo $DRY_RUN`
3. Check if you're using a different .env file
4. Restart your application/script after changing .env

### Need to test a write operation

If you need to test actual writes:
1. Use a test Intercom workspace (not production!)
2. Create test conversations
3. Set `DRY_RUN=false` explicitly
4. Always verify you're in the test workspace first!

