# Application Status Agent - Deployment Guide

## Overview
This guide will help you deploy the Application Status Agent to LangGraph Cloud.

## Prerequisites

1. **LangGraph CLI**: Install the LangGraph CLI
   ```bash
   pip install langgraph-cli
   ```

2. **Authentication**: Make sure you're logged in to LangGraph
   ```bash
   langgraph login
   ```

3. **Environment Variables**: Ensure your `.env` file contains all required variables:
   ```bash
   # OpenAI API Key
   OPENAI_API_KEY=your_openai_api_key
   
   # LangSmith Configuration
   LANGCHAIN_API_KEY=your_langsmith_api_key
   LANGCHAIN_TRACING_V2=true
   LANGCHAIN_PROJECT=application-status-agent
   LANGSMITH_PROJECT=application-status-agent
   
   # MCP Server Configuration
   MCP_SERVER_URL=your_mcp_server_url
   MCP_API_KEY=your_mcp_api_key
   ```

## Deployment Steps

### 1. Verify Project Structure
Your project should have the following structure:
```
application-status-agent/
├── langgraph.json          # LangGraph configuration
├── pyproject.toml          # Python dependencies
├── .env                    # Environment variables
├── src/
│   └── agent/
│       ├── graph.py        # Main graph definition
│       ├── runner.py       # Agent runner
│       ├── types.py        # State definitions
│       ├── llm.py          # LLM configurations
│       ├── prompts.py      # LangSmith prompt client
│       └── nodes/          # Node implementations
│           ├── plan/
│           ├── gather/
│           ├── coverage/
│           └── draft/
└── src/mcp/                # MCP client integration
```

### 2. Test Locally (Optional)
Test your agent locally before deployment:
```bash
# Install dependencies
pip install -e .

# Test the graph
python -c "from src.agent.graph import graph; print('Graph loaded successfully')"
```

### 3. Deploy to LangGraph Cloud
Deploy your agent:
```bash
langgraph deploy
```

This will:
- Upload your code to LangGraph Cloud
- Install dependencies from `pyproject.toml`
- Configure the environment with your `.env` variables
- Make your agent available via API

### 4. Verify Deployment
After deployment, you can:

1. **Check deployment status**:
   ```bash
   langgraph status
   ```

2. **View logs**:
   ```bash
   langgraph logs
   ```

3. **Test the deployed agent**:
   ```bash
   langgraph test
   ```

## Configuration Details

### langgraph.json
```json
{
  "$schema": "https://langgra.ph/schema.json",
  "dependencies": ["."],
  "graphs": {
    "agent": "./src/agent/graph.py:graph"
  },
  "env": ".env",
  "image_distro": "wolfi"
}
```

### Key Points:
- **Graph Export**: The `graph` variable in `src/agent/graph.py` is exported for LangGraph
- **Dependencies**: All dependencies are listed in `pyproject.toml`
- **Environment**: Uses `.env` file for configuration
- **Image**: Uses Wolfi distribution for optimal performance

## Usage After Deployment

Once deployed, your agent will be available at:
- **API Endpoint**: `https://api.langgraph.com/agents/{your-agent-id}`
- **Web Interface**: Available in LangGraph Cloud dashboard

### Example API Usage:
```python
import requests

# Your agent endpoint
url = "https://api.langgraph.com/agents/{your-agent-id}/invoke"

# Example request
payload = {
    "input": {
        "user_query": "I want to withdraw my application",
        "user_email": "user@example.com"
    }
}

response = requests.post(url, json=payload)
result = response.json()
```

## Troubleshooting

### Common Issues:

1. **Import Errors**: Ensure all imports use relative paths from `src/`
2. **Missing Dependencies**: Check `pyproject.toml` includes all required packages
3. **Environment Variables**: Verify `.env` file has all required variables
4. **Graph Export**: Ensure `graph` variable is properly exported in `graph.py`

### Debug Commands:
```bash
# Check project structure
langgraph validate

# View detailed logs
langgraph logs --follow

# Redeploy if needed
langgraph deploy --force
```

## Production Considerations

1. **Environment Variables**: Use LangGraph's environment variable management for production secrets
2. **Monitoring**: Set up monitoring and alerting in LangGraph Cloud
3. **Scaling**: Configure auto-scaling based on usage patterns
4. **Security**: Ensure API keys are properly secured and rotated

## Support

- **LangGraph Documentation**: https://langgraph.com/docs
- **LangGraph Cloud**: https://cloud.langgraph.com
- **Community Support**: LangGraph Discord/Forum
