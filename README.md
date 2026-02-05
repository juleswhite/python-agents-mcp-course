# AI Agents with Model Context Protocol - Python Code Examples

This repository contains Python code examples for the Coursera course "AI Agents with Model Context Protocol."

## Prerequisites

- Python 3.10+
- pip
- An API key from OpenAI, Anthropic, or Google (set in `.env` file)

## Setup

Each module has its own `code/` directory. To set up any module:

```bash
cd <module>/code
pip install -r requirements.txt
cp .env.example .env  # Then add your API key(s)
```

---

## Course Structure & Code Mapping

### Module 1: Getting Started with Model Context Protocol (MCP) for AI Agents

| Item | Type | Code Files |
|------|------|------------|
| Why Do We Need Model Context Protocol? | Video | — |
| Model Context Protocol & AI Problem Solving with Tools | Video | — |
| MCP Allows AI to Communicate with the Computer | Video | — |
| AI @ Work - What My Work with AI Looks Like | Video | — |
| My AI Tools | Reading | — |
| Learning More & Staying Connected | Reading | — |

*Module 1 is conceptual introduction — no code exercises.*

---

### Module 2: AI Agent Loops & Model Context Protocol

| Item | Type | Code Files | Run Command |
|------|------|------------|-------------|
| Model Context Protocol: Syntax, Semantics, Timing | Video | — | — |
| Model Context Protocol & AI Agents | Video | — | — |
| What is an MCP Server? | Video | — | — |
| Tool Specifications | Video | — | — |
| **Building Your First MCP Server** | Ungraded Plugin | `server.py` | `python server.py` |
| **Building Your First MCP AI Agent** | Ungraded Plugin | `agent.py`, `llm.py` | `python agent.py "question"` |
| Agents Talking to Tools vs. Tools with AI | Video | — | — |

**Code Location:** `01-intro-to-mcp-agents/code/`

**Key Files:**
| File | Description |
|------|-------------|
| `server.py` | Basic MCP tool server with `list_files` and `read_file` tools |
| `agent.py` | Agent loop implementation (PERCEIVE→DECIDE→ACT→OBSERVE) |
| `llm.py` | LLM integration utilities (OpenAI/Anthropic/Gemini) |
| `test_server.py` | Tests server tools directly without an agent |
| `server_with_resources.py` | Server with MCP resources for teaching agents |
| `agent_with_learning.py` | Agent that reads resources before acting |

**Commands:**
```bash
cd 01-intro-to-mcp-agents/code
pip install -r requirements.txt
python server.py              # Start the basic MCP server
python agent.py "question"    # Run the basic agent
python test_server.py         # Test server tools directly
```

---

### Module 3: Building AI Agents with Model Context Protocol

| Item | Type | Code Files | Run Command |
|------|------|------------|-------------|
| Resources | Video | — | — |
| **Teaching Agents to Use Tools** | Ungraded Plugin | `workspace_server.py` | `python workspace_server.py` |
| **Teaching Agents to Seek Help** | Ungraded Plugin | `workspace_server.py` | `python workspace_server.py` |
| **Helping Agents Find Guidance** | Ungraded Plugin | `workspace_server.py` | `python workspace_server.py` |
| **Helping AI Agents on the Fly** | Ungraded Plugin | `workspace_server.py` | `python workspace_server.py` |
| **Helping AI Agents Discover Workspace-related Guidance** | Ungraded Plugin | `workspace_agent.py` | `python workspace_agent.py "question"` |

**Code Location:** `01-intro-to-mcp-agents/code/`

**Key Files:**
| File | Description |
|------|-------------|
| `workspace_server.py` | Enhanced server with workspace-aware tools and context discovery |
| `workspace_agent.py` | Agent that works within a defined workspace with context awareness |
| `workspace/` | Sample workspace with `.context.md` files for testing |

**Commands:**
```bash
cd 01-intro-to-mcp-agents/code
python workspace_server.py           # Start workspace-aware server
python workspace_agent.py "question" # Run workspace agent with context discovery
```

---

### Module 4: Robust Error Handling Techniques for AI Agents

| Item | Type | Code Files | Run Command |
|------|------|------------|-------------|
| **Responses are More than Data** | Ungraded Plugin | `expense_server.py` | `python expense_server.py` |
| **Designing Errors to Help AI Agents** | Ungraded Plugin | `expense_server.py` | `python expense_server.py` |
| **Errors in Complex Workflows** | Ungraded Plugin | `expense_server.py` | `python expense_server.py` |
| **Minimizing AI Agent Cognitive Burden from Error Recovery** | Ungraded Plugin | `expense_server.py` | `python expense_server.py` |
| **Helping AI Agents Find Alternative Paths to Fix Errors** | Ungraded Plugin | `expense_server.py` | `python expense_server.py` |

**Code Location:** `02-failing-forward/code/`

**Key Files:**
| File | Description |
|------|-------------|
| `expense_server.py` | MCP server demonstrating all Failing Forward patterns |
| `expense_agent.py` | Agent that learns from errors to complete expense tasks |
| `test_failing_forward.py` | Comprehensive tests for all failing forward patterns |

**Commands:**
```bash
cd 02-failing-forward/code
pip install -r requirements.txt
python expense_server.py           # Start the expense server
python expense_agent.py "request"  # Run the expense agent
python test_failing_forward.py     # Run failing forward tests
```

**Pattern Mapping:**
| Coursera Item | Pattern | Implementation |
|---------------|---------|----------------|
| Responses are More than Data | Response-as-Instruction | `next_action`, `hint` fields in responses |
| Designing Errors to Help AI Agents | Errors as Curriculum | `submit_expense` validation with guidance |
| Errors in Complex Workflows | Error Chains | `request_late_expense_approval` → `check_approval_status` |
| Minimizing AI Agent Cognitive Burden | Pre-filled Parameters | `suggested_params` in error responses |
| Helping AI Agents Find Alternative Paths | Alternative Actions | `alternatives` array in responses |

---

### Module 5: Faster, More Predictable, More Capable AI Agents

| Item | Type | Code Files | Run Command |
|------|------|------------|-------------|
| **Managing AI Agent Cognitive Load** | Ungraded Plugin | `agent_heavy_server.py`<br>`tool_heavy_server.py` | `python agent_heavy_server.py`<br>`python tool_heavy_server.py` |
| **Predictability, Lower Cost, Speed: Scripted Orchestration** | Ungraded Plugin | `scripted_orchestration_server.py` | `python scripted_orchestration_server.py` |
| Prompts and MCP | Video | — | — |
| **Self-Prompting: Adding Reasoning to Tools** | Ungraded Plugin | `self_prompting_server.py` | `python self_prompting_server.py` |
| **AI Agent Tool Design for Common Errors** | Ungraded Plugin | `validate_at_source_server.py` | `python validate_at_source_server.py` |
| AI Agents, MCP, & Identity / Security | Video | — | — |
| Wrapping Up | Video | — | — |
| Final Assessment | Assignment | — | — |

**Code Location:** `03-intelligence-budget/code/`

**Key Files:**
| File | Description |
|------|-------------|
| `agent_heavy_server.py` | Minimal tools approach - agent does most processing |
| `tool_heavy_server.py` | Rich tools approach - tools pre-process data for agent |
| `hybrid_server.py` | Balanced approach combining both strategies |
| `scripted_orchestration_server.py` | Tools that let agent write scripts for batch operations |
| `self_prompting_server.py` | Tools that make isolated LLM calls for semantic reasoning |
| `validate_at_source_server.py` | Tools with layered validation (format → business → semantic) |
| `database.py` | Shared mock database used by all server examples |
| `test_all.py` | Comprehensive test suite comparing all approaches |

**Commands:**
```bash
cd 03-intelligence-budget/code
pip install -r requirements.txt
python agent_heavy_server.py   # Start agent-heavy server
python tool_heavy_server.py    # Start tool-heavy server
python hybrid_server.py        # Start hybrid server
python test_all.py             # Run comparison tests
```

**Pattern Mapping:**
| Coursera Item | Pattern | Implementation |
|---------------|---------|----------------|
| Managing AI Agent Cognitive Load | Intelligence Budget | Agent-heavy vs tool-heavy approaches |
| Predictability, Lower Cost, Speed | Scripted Orchestration | `execute_script` tool for batch operations |
| Self-Prompting: Adding Reasoning | Self-Prompting | Isolated LLM calls within tools |
| AI Agent Tool Design for Common Errors | Validate at Source | Layered validation stack (format → business → semantic) |

---

## Quick Reference: Coursera Item → Code File

| Module | Coursera Item | Code File |
|--------|---------------|-----------|
| 2 | Building Your First MCP Server | `01-intro-to-mcp-agents/code/server.py` |
| 2 | Building Your First MCP AI Agent | `01-intro-to-mcp-agents/code/agent.py` |
| 3 | Teaching Agents to Use Tools | `01-intro-to-mcp-agents/code/workspace_server.py` |
| 3 | Teaching Agents to Seek Help | `01-intro-to-mcp-agents/code/workspace_server.py` |
| 3 | Helping Agents Find Guidance | `01-intro-to-mcp-agents/code/workspace_server.py` |
| 3 | Helping AI Agents on the Fly | `01-intro-to-mcp-agents/code/workspace_server.py` |
| 3 | Helping AI Agents Discover Workspace-related Guidance | `01-intro-to-mcp-agents/code/workspace_agent.py` |
| 4 | Responses are More than Data | `02-failing-forward/code/expense_server.py` |
| 4 | Designing Errors to Help AI Agents | `02-failing-forward/code/expense_server.py` |
| 4 | Errors in Complex Workflows | `02-failing-forward/code/expense_server.py` |
| 4 | Minimizing AI Agent Cognitive Burden from Error Recovery | `02-failing-forward/code/expense_server.py` |
| 4 | Helping AI Agents Find Alternative Paths to Fix Errors | `02-failing-forward/code/expense_server.py` |
| 5 | Managing AI Agent Cognitive Load | `03-intelligence-budget/code/agent_heavy_server.py`<br>`03-intelligence-budget/code/tool_heavy_server.py` |
| 5 | Predictability, Lower Cost, Speed: Scripted Orchestration | `03-intelligence-budget/code/scripted_orchestration_server.py` |
| 5 | Self-Prompting: Adding Reasoning to Tools | `03-intelligence-budget/code/self_prompting_server.py` |
| 5 | AI Agent Tool Design for Common Errors | `03-intelligence-budget/code/validate_at_source_server.py` |

---

## Environment Setup

Create a `.env` file in each module's `code/` directory:

```env
OPENAI_API_KEY=your-openai-key-here
ANTHROPIC_API_KEY=your-anthropic-key-here
GOOGLE_API_KEY=your-google-key-here
```

You only need to provide the API key(s) for the LLM provider(s) you plan to use.

---

## Project Structure

```
code-repo/
├── README.md
├── .gitignore
│
├── 01-intro-to-mcp-agents/
│   └── code/
│       ├── server.py              # Module 2: Building Your First MCP Server
│       ├── agent.py               # Module 2: Building Your First MCP AI Agent
│       ├── llm.py                 # LLM integration utilities
│       ├── workspace_server.py    # Module 3: All workspace/context items
│       ├── workspace_agent.py     # Module 3: Workspace-related Guidance
│       ├── server_with_resources.py  # Server with MCP resources
│       ├── agent_with_learning.py    # Agent with active learning
│       ├── test_server.py         # Server testing
│       ├── test_resources.py      # Resource testing
│       ├── requirements.txt       # Python dependencies
│       ├── README.md              # Setup instructions
│       └── workspace/             # Sample workspace with .context.md files
│
├── 02-failing-forward/
│   └── code/
│       ├── expense_server.py      # Module 4: All error handling items
│       ├── expense_agent.py       # Agent for expense workflows
│       ├── test_failing_forward.py # Pattern tests
│       ├── requirements.txt       # Python dependencies
│       └── README.md              # Setup instructions
│
└── 03-intelligence-budget/
    └── code/
        ├── agent_heavy_server.py           # Module 5: Managing Cognitive Load
        ├── tool_heavy_server.py            # Module 5: Managing Cognitive Load
        ├── hybrid_server.py                # Balanced approach
        ├── scripted_orchestration_server.py # Module 5: Scripted Orchestration
        ├── self_prompting_server.py        # Module 5: Self-Prompting
        ├── validate_at_source_server.py    # Module 5: Tool Design for Errors
        ├── database.py                     # Shared mock database
        ├── test_all.py                     # Comparison tests
        ├── requirements.txt                # Python dependencies
        └── README.md                       # Setup instructions
```

---

## License

MIT
