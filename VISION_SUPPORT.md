# Vision Support for Attachments

This document explains how attachments (especially images) are processed in the agent and how to enable vision capabilities.

## Summary

✅ **The LLM (gpt-5) can directly access images via URLs** - no need to download or encode them.  
✅ **Intercom's signed attachment URLs work perfectly** - they can be passed directly to the LLM.  
✅ **Two modes available**: Text-only awareness vs. Full vision analysis.

## How Attachments Work

### 1. Extraction (Already Implemented)

Attachments are automatically extracted from Intercom conversations by `IntercomClient.get_conversation_data_for_agent()`:

```python
{
  "role": "user",
  "content": "Look at this screenshot...",
  "attachments": [
    {
      "type": "upload",
      "name": "screenshot.png",
      "url": "https://mercor-aae4779d23c4.intercom-attachments-5.com/...",
      "content_type": "image/png",
      "filesize": 950134,
      "width": "3256",
      "height": "1928"
    }
  ]
}
```

### 2. Two Formatting Modes

#### Mode A: Text-Only Awareness (Current Default)

**Function**: `format_conversation_history(messages, subject)` in `src/utils/prompts.py`

**Use Case**: When you want the LLM to know about attachments but not necessarily analyze them.

**Output Format**:
```
1. User: Look at this screenshot...
   📎 Attachment 1: screenshot.png (Type: image/png)
      URL: https://...
      Size: 927.9 KB
      Dimensions: 3256x1928
```

**Pros**:
- Simple text-based approach
- Works with existing prompt structure
- Lower cost (no vision API calls)

**Cons**:
- LLM cannot actually "see" or analyze the image
- Only knows the filename, type, and URL

#### Mode B: Full Vision Analysis (New Capability)

**Function**: `convert_messages_to_langchain_with_vision(messages, subject, user_name, user_email)` in `src/utils/prompts.py`

**Use Case**: When you need the LLM to actually analyze image content (screenshots, diagrams, etc.)

**Output Format**: Structured LangChain messages with `image_url` content types

**Example**:
```python
from src.utils.prompts import convert_messages_to_langchain_with_vision
from langchain_openai import ChatOpenAI

# Get messages from Intercom
messages = conversation_data["messages"]
subject = conversation_data["subject"]
user_name = conversation_data["user_name"]
user_email = conversation_data["user_email"]

# Convert to LangChain format with vision
langchain_messages = convert_messages_to_langchain_with_vision(
    messages=messages,
    subject=subject,
    user_name=user_name,
    user_email=user_email
)

# Invoke LLM with vision
llm = ChatOpenAI(model="gpt-5", temperature=0.2)
response = llm.invoke(langchain_messages)
```

**Pros**:
- LLM can actually see and analyze image content
- Can answer questions about what's in the image
- Can extract text from screenshots, identify UI elements, etc.

**Cons**:
- Higher API costs (vision models are more expensive)
- Requires structured message format (not simple text)
- Need to update nodes to use structured messages instead of text prompts

## When to Use Each Mode

### Use Text-Only Mode When:
- User is just sharing a document/image for reference
- The filename/type is sufficient context
- You want to minimize API costs
- The image isn't critical to understanding the query

### Use Vision Mode When:
- User asks "what do you see in this image?"
- Screenshot contains important information (error messages, data, UI state)
- User references specific visual elements
- You need to extract text or identify objects in images

## Implementation Status

✅ **Completed**:
- Attachment extraction from Intercom API
- Text-only formatting (default)
- Vision-capable message conversion function
- Testing and verification

⏳ **To Integrate Vision in Nodes** (Optional):
Currently, all nodes use text-based prompts via `format_conversation_history()`. To enable vision analysis in specific nodes:

1. **Draft Node** - Most valuable for vision:
   ```python
   # In draft_node() function
   # Instead of: conversation_history = format_conversation_history(...)
   # Use:
   langchain_messages = convert_messages_to_langchain_with_vision(
       messages=state["messages"],
       subject=state.get("subject"),
       user_name=state.get("user_details", {}).get("name"),
       user_email=state.get("user_details", {}).get("email")
   )
   # Then invoke LLM with structured messages instead of text prompt
   ```

2. **Coverage Node** - Useful for assessing if image provides needed info
3. **Plan Node** - Could help identify if image analysis tools are needed

## Cost Considerations

Vision API calls are more expensive than text-only:
- Text-only (gpt-5): ~$0.01-0.05 per request
- Vision (gpt-5 with images): ~$0.10-0.50 per request (depends on image size/detail)

**Recommendation**: Use vision mode selectively, perhaps:
- Detect when user explicitly references an image ("in this screenshot", "as shown", etc.)
- Check message intent before deciding to use vision
- Add a flag in state to control vision mode: `use_vision: bool`

## Testing

To test vision capabilities:

```bash
# Test with a specific conversation that has attachments
python -c "
from src.clients.intercom import IntercomClient
from src.utils.prompts import convert_messages_to_langchain_with_vision
from langchain_openai import ChatOpenAI
import os

client = IntercomClient(os.getenv('INTERCOM_API_KEY'))
data = client.get_conversation_data_for_agent('YOUR_CONVERSATION_ID')

messages = convert_messages_to_langchain_with_vision(
    data['messages'], data['subject'], data['user_name'], data['user_email']
)

llm = ChatOpenAI(model=os.getenv('MODEL_NAME'))
response = llm.invoke(messages + [{'role': 'user', 'content': 'Describe the images.'}])
print(response.content)
"
```

## Next Steps

1. **Decide on vision strategy**: Always use vision? Selective? User-triggered?
2. **Update nodes if needed**: Modify draft/coverage/plan nodes to use structured messages
3. **Add vision flag**: Add `use_vision: bool` to state for control
4. **Monitor costs**: Track vision API usage and costs
5. **Update prompts**: Optimize prompts for vision analysis scenarios

## Questions?

- Should vision be always-on or selective?
- Which nodes would benefit most from vision?
- Do we need to detect image-related queries automatically?

