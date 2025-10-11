# Agent Nodes

This directory contains all the agent nodes organized in subfolders.

## Structure

Each node should have its own subfolder with the following structure:

```
nodes/
├── plan/                    # Plan node
│   ├── __init__.py         # Exports for the node
│   ├── plan.py             # Main node implementation
│   ├── schemas.py          # Node-specific schemas
│   └── README.md           # Node documentation (optional)
├── execute/                 # Execute node (future)
│   ├── __init__.py
│   ├── execute.py
│   ├── schemas.py
│   └── README.md
└── respond/                 # Respond node (future)
    ├── __init__.py
    ├── respond.py
    ├── schemas.py
    └── README.md
```

## Node Development Guidelines

1. **Each node gets its own folder** with descriptive name
2. **Schemas go in the node folder** - keep them close to the implementation
3. **`__init__.py` exports** the main functions and schemas
4. **Main implementation** goes in a file named after the node
5. **Documentation** can be added as README.md in each node folder

## Current Nodes

### Plan Node (`plan/`)
- **Purpose**: Analyzes user queries and creates execution plans
- **Input**: User message, optional email
- **Output**: List of tools to execute with parameters
- **Schemas**: `Plan`, `ToolCall`, `PlanRequest`, `PlanResponse`

## Future Nodes

### Execute Node (`execute/`)
- **Purpose**: Executes the planned tool calls
- **Input**: List of tool calls from plan node
- **Output**: Tool results and execution status

### Respond Node (`respond/`)
- **Purpose**: Generates final response based on tool results
- **Input**: Tool results and original user query
- **Output**: Final response to user
