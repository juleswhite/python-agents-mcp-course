# Intelligence Budget - Python MCP Servers

This directory contains Python implementations of the Intelligence Budget tutorials, demonstrating different patterns for distributing intelligence between agents and tools.

## Overview

The Intelligence Budget concept explores where to place semantic reasoning in your MCP architecture:

1. **Agent-Heavy** - Agent does all reasoning, tools just store data
2. **Tool-Heavy** - Tools handle all business logic, agent extracts facts
3. **Hybrid** - Agent provides flexible input, tools process intelligently
4. **Scripted Orchestration** - Agent writes code, tools execute it
5. **Self-Prompting** - Tools make their own LLM calls for focused tasks
6. **Validate at Source** - Tools perform semantic validation

## Setup

### 1. Create Virtual Environment

```bash
cd python-code
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

Create or edit `.env` file with your OpenAI API key:

```
OPENAI_API_KEY=your-api-key-here
```

## Server Files

| File | Description | Intelligence Pattern |
|------|-------------|---------------------|
| `agent_heavy_server.py` | Minimal tools, agent reasons about everything | High agent tokens |
| `tool_heavy_server.py` | All business logic in tools | Low agent tokens |
| `hybrid_server.py` | Flexible input, smart tool processing | Balanced |
| `scripted_orchestration_server.py` | Agent writes code, tool executes | Very efficient |
| `self_prompting_server.py` | Tools make focused LLM calls | Testable classification |
| `validate_at_source_server.py` | Full validation stack in tools | Robust validation |

## Running Servers

Each server can be run directly:

```bash
python agent_heavy_server.py
python tool_heavy_server.py
python hybrid_server.py
python scripted_orchestration_server.py
python self_prompting_server.py
python validate_at_source_server.py
```

All servers run on stdio transport and can be connected to by MCP clients.

## Running Tests

The comprehensive test suite verifies all servers and patterns:

```bash
python test_all.py
```

This tests:
1. All servers start correctly
2. Budget boundary (agent-heavy vs tool-heavy behavior)
3. Self-prompting (classification with internal LLM calls)
4. Scripted orchestration (code execution)
5. Validate at source (semantic validation)

## Key Concepts

### Budget Boundary
Where does intelligence live? Agent-heavy means the agent knows all rules and orchestrates everything. Tool-heavy means tools encapsulate all business logic.

### Scripted Orchestration
Instead of the agent calling tools one-by-one and seeing all intermediate results, the agent writes a script that executes outside its context window, returning only the final result.

### Self-Prompting
Tools can make their own LLM calls with focused prompts. This keeps the agent's context clean while allowing semantic reasoning in tools.

### Validate at Source
Validation happens in layers: format (free), business rules (free), semantic (LLM), human review (flagged). The tool handles all validation, not the agent.

## Architecture

```
database.py           # Shared mock database (expenses, approvals)
├── agent_heavy_server.py
├── tool_heavy_server.py
├── hybrid_server.py
├── scripted_orchestration_server.py
├── self_prompting_server.py
├── validate_at_source_server.py
└── test_all.py       # Comprehensive test suite
```

## Dependencies

- `mcp` - Model Context Protocol Python SDK
- `openai` - OpenAI API client (for self-prompting and tests)
- `httpx` - HTTP client
- `python-dotenv` - Environment variable loading
- `pydantic` - Data validation and settings

## License

MIT
