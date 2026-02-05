# MCP Agents Tutorial - Python Version

This directory contains Python implementations of the MCP (Model Context Protocol) agent tutorials, converted from the original TypeScript versions.

## Prerequisites

- Python 3.10+
- An API key from one of:
  - OpenAI (`OPENAI_API_KEY`)
  - Anthropic (`ANTHROPIC_API_KEY`)
  - Google (`GEMINI_API_KEY`)

## Setup

1. **Create a virtual environment** (recommended):

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**:

   Copy the `.env.example` to `.env` (or use the provided `.env`) and add your API key:

   ```bash
   cp .env.example .env
   # Edit .env and add your API key
   ```

   The `.env` file should contain at least one of:
   ```
   OPENAI_API_KEY=your-openai-api-key
   ANTHROPIC_API_KEY=your-anthropic-api-key
   GEMINI_API_KEY=your-gemini-api-key
   ```

## Files Overview

### Core Modules

| File | Description |
|------|-------------|
| `llm.py` | LLM abstraction layer supporting OpenAI, Anthropic, and Gemini |
| `server.py` | Basic MCP server with `list_files` and `read_file` tools |
| `server_with_resources.py` | MCP server with tools AND resources for active learning |
| `workspace_server.py` | Context-aware workspace server with `.context.md` support |

### Agents

| File | Description |
|------|-------------|
| `agent.py` | Basic file research agent demonstrating the agent loop |
| `agent_with_learning.py` | Agent with active learning (reads resources before acting) |
| `workspace_agent.py` | Context-aware workspace agent for file management |

### Test Scripts

| File | Description |
|------|-------------|
| `test_server.py` | Tests the basic MCP server (no LLM needed) |
| `test_resources.py` | Tests the MCP server with resources (no LLM needed) |

## Running the Examples

### Test the MCP Server (No API Key Required)

```bash
# Test the basic server
python test_server.py

# Test the server with resources
python test_resources.py
```

### Run the File Research Agent

```bash
# Default question
python agent.py

# Custom question
python agent.py "What files are here and what do they do?"
python agent.py "Read the requirements.txt and explain the dependencies"
```

### Run the Agent with Active Learning

```bash
# Default question
python agent_with_learning.py

# Custom question
python agent_with_learning.py "What is this project about?"
python agent_with_learning.py "How should I explore this codebase?"
```

### Run the Workspace Agent

First, create a `workspace/` directory with some content and `.context.md` files:

```bash
mkdir -p workspace/expenses workspace/reports
echo "# Global Rules" > workspace/.context.md
echo "# Expense Rules" > workspace/expenses/.context.md
```

Then run the agent:

```bash
python workspace_agent.py "What directories are available?"
python workspace_agent.py "What are the rules for expenses?"
```

## Architecture

### The Agent Loop

All agents follow the same pattern:

1. **PERCEIVE**: Connect to MCP server, discover available tools (and resources)
2. **DECIDE**: Ask the LLM what to do given the conversation history
3. **ACT**: Execute tool calls requested by the LLM
4. **OBSERVE**: Process results and add to conversation history
5. **REPEAT**: Continue until the LLM responds without tool calls

### MCP Protocol

- **Tools**: Functions the agent can call (like `list_files`, `read_file`)
- **Resources**: Static content the agent can read for context (like guides)
- **Transport**: Communication happens via stdio (stdin/stdout)

## Troubleshooting

### "No API key found" Error

Make sure you have a `.env` file with at least one API key set.

### "Connection refused" or Similar

The agent spawns the server as a subprocess. Make sure:
- You're running from the `python-code/` directory
- The server file exists and is valid Python
- No syntax errors in the server code

### Timeout Errors

The LLM API calls have a 60-second timeout. If you're getting timeouts:
- Check your internet connection
- Verify your API key is valid
- Try a different LLM provider

## License

Part of the MCP Patterns Course tutorials.
