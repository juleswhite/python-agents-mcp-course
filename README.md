# AI Agents with Model Context Protocol - Code Examples

This repository contains code examples for the Coursera course "AI Agents with Model Context Protocol."

**Available in both Python and TypeScript!**

## Prerequisites

### For Python
- Python 3.10+
- pip
- An API key from OpenAI, Anthropic, or Google (set in `.env` file)

### For TypeScript
- Node.js 18+
- npm
- An OpenAI API key (set in `.env` file)

## Setup

Each module has its own `code/` directory with **both Python and TypeScript** implementations.

### Python Setup
```bash
cd <module>/code
pip install -r requirements.txt
cp .env.example .env  # Then add your API key(s)
```

### TypeScript Setup
```bash
cd <module>/code
npm install
cp .env.example .env  # Then add your OPENAI_API_KEY
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

| Item | Type | Python Files | TypeScript Files |
|------|------|--------------|------------------|
| Model Context Protocol: Syntax, Semantics, Timing | Video | — | — |
| Model Context Protocol & AI Agents | Video | — | — |
| What is an MCP Server? | Video | — | — |
| Tool Specifications | Video | — | — |
| **Building Your First MCP Server** | Ungraded Plugin | `server.py` | `server.ts` |
| **Building Your First MCP AI Agent** | Ungraded Plugin | `agent.py`, `llm.py` | `agent.ts`, `llm.ts` |
| Agents Talking to Tools vs. Tools with AI | Video | — | — |

**Code Location:** `01-intro-to-mcp-agents/code/`

**Key Files:**
| Python | TypeScript | Description |
|--------|------------|-------------|
| `server.py` | `server.ts` | Basic MCP tool server with `list_files` and `read_file` tools |
| `agent.py` | `agent.ts` | Agent loop implementation (PERCEIVE→DECIDE→ACT→OBSERVE) |
| `llm.py` | `llm.ts` | LLM integration utilities (OpenAI/Anthropic/Gemini) |
| `test_server.py` | `test-server.ts` | Tests server tools directly without an agent |

**Python Commands:**
```bash
cd 01-intro-to-mcp-agents/code
pip install -r requirements.txt
python server.py              # Start the basic MCP server
python agent.py "question"    # Run the basic agent
python test_server.py         # Test server tools directly
```

**TypeScript Commands:**
```bash
cd 01-intro-to-mcp-agents/code
npm install
npm run server       # Start the basic MCP server
npm run agent        # Run the basic agent
npm run test-server  # Test server tools directly
```

---

### Module 3: Building AI Agents with Model Context Protocol

| Item | Type | Python Files | TypeScript Files |
|------|------|--------------|------------------|
| Resources | Video | — | — |
| **Teaching Agents to Use Tools** | Ungraded Plugin | `workspace_server.py` | `workspace-server.ts` |
| **Teaching Agents to Seek Help** | Ungraded Plugin | `workspace_server.py` | `workspace-server.ts` |
| **Helping Agents Find Guidance** | Ungraded Plugin | `workspace_server.py` | `workspace-server.ts` |
| **Helping AI Agents on the Fly** | Ungraded Plugin | `workspace_server.py` | `workspace-server.ts` |
| **Helping AI Agents Discover Workspace-related Guidance** | Ungraded Plugin | `workspace_agent.py` | `workspace-agent.ts` |

**Code Location:** `01-intro-to-mcp-agents/code/`

**Key Files:**
| Python | TypeScript | Description |
|--------|------------|-------------|
| `workspace_server.py` | `workspace-server.ts` | Enhanced server with workspace-aware tools and context discovery |
| `workspace_agent.py` | `workspace-agent.ts` | Agent that works within a defined workspace with context awareness |
| `workspace/` | `workspace/` | Sample workspace with `.context.md` files for testing |

**Python Commands:**
```bash
cd 01-intro-to-mcp-agents/code
python workspace_server.py           # Start workspace-aware server
python workspace_agent.py "question" # Run workspace agent with context discovery
```

**TypeScript Commands:**
```bash
cd 01-intro-to-mcp-agents/code
npm run workspace-server  # Start workspace-aware server
npm run workspace-agent   # Run workspace agent with context discovery
```

---

### Module 4: Robust Error Handling Techniques for AI Agents

| Item | Type | Python Files | TypeScript Files |
|------|------|--------------|------------------|
| **Responses are More than Data** | Ungraded Plugin | `expense_server.py` | `expense-server.ts` |
| **Designing Errors to Help AI Agents** | Ungraded Plugin | `expense_server.py` | `expense-server.ts` |
| **Errors in Complex Workflows** | Ungraded Plugin | `expense_server.py` | `expense-server.ts` |
| **Minimizing AI Agent Cognitive Burden from Error Recovery** | Ungraded Plugin | `expense_server.py` | `expense-server.ts` |
| **Helping AI Agents Find Alternative Paths to Fix Errors** | Ungraded Plugin | `expense_server.py` | `expense-server.ts` |

**Code Location:** `02-failing-forward/code/`

**Key Files:**
| Python | TypeScript | Description |
|--------|------------|-------------|
| `expense_server.py` | `expense-server.ts` | MCP server demonstrating all Failing Forward patterns |
| `expense_agent.py` | `expense-agent.ts` | Agent that learns from errors to complete expense tasks |
| `test_failing_forward.py` | `test-failing-forward.ts` | Comprehensive tests for all failing forward patterns |

**Python Commands:**
```bash
cd 02-failing-forward/code
pip install -r requirements.txt
python expense_server.py           # Start the expense server
python expense_agent.py "request"  # Run the expense agent
python test_failing_forward.py     # Run failing forward tests
```

**TypeScript Commands:**
```bash
cd 02-failing-forward/code
npm install
npm run server  # Start the expense server
npm run agent   # Run the expense agent
npm run test    # Run failing forward tests
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

| Item | Type | Python Files | TypeScript Files |
|------|------|--------------|------------------|
| **Managing AI Agent Cognitive Load** | Ungraded Plugin | `agent_heavy_server.py`<br>`tool_heavy_server.py` | `agent-heavy-server.ts`<br>`tool-heavy-server.ts` |
| **Predictability, Lower Cost, Speed: Scripted Orchestration** | Ungraded Plugin | `scripted_orchestration_server.py` | `scripted-orchestration-server.ts` |
| Prompts and MCP | Video | — | — |
| **Self-Prompting: Adding Reasoning to Tools** | Ungraded Plugin | `self_prompting_server.py` | `self-prompting-server.ts` |
| **AI Agent Tool Design for Common Errors** | Ungraded Plugin | `validate_at_source_server.py` | `validate-at-source-server.ts` |
| AI Agents, MCP, & Identity / Security | Video | — | — |
| Wrapping Up | Video | — | — |
| Final Assessment | Assignment | — | — |

**Code Location:** `03-intelligence-budget/code/`

**Key Files:**
| Python | TypeScript | Description |
|--------|------------|-------------|
| `agent_heavy_server.py` | `agent-heavy-server.ts` | Minimal tools approach - agent does most processing |
| `tool_heavy_server.py` | `tool-heavy-server.ts` | Rich tools approach - tools pre-process data for agent |
| `hybrid_server.py` | `hybrid-server.ts` | Balanced approach combining both strategies |
| `scripted_orchestration_server.py` | `scripted-orchestration-server.ts` | Tools that let agent write scripts for batch operations |
| `self_prompting_server.py` | `self-prompting-server.ts` | Tools that make isolated LLM calls for semantic reasoning |
| `validate_at_source_server.py` | `validate-at-source-server.ts` | Tools with layered validation (format → business → semantic) |
| `database.py` | `database.ts` | Shared mock database used by all server examples |
| `test_all.py` | `test-all.ts` | Comprehensive test suite comparing all approaches |

**Python Commands:**
```bash
cd 03-intelligence-budget/code
pip install -r requirements.txt
python agent_heavy_server.py   # Start agent-heavy server
python tool_heavy_server.py    # Start tool-heavy server
python hybrid_server.py        # Start hybrid server
python test_all.py             # Run comparison tests
```

**TypeScript Commands:**
```bash
cd 03-intelligence-budget/code
npm install
npm run agent-heavy  # Start agent-heavy server
npm run tool-heavy   # Start tool-heavy server
npm run hybrid       # Start hybrid server
npm run test         # Run comparison tests
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

| Module | Coursera Item | Python | TypeScript |
|--------|---------------|--------|------------|
| 2 | Building Your First MCP Server | `server.py` | `server.ts` |
| 2 | Building Your First MCP AI Agent | `agent.py` | `agent.ts` |
| 3 | Teaching Agents to Use Tools | `workspace_server.py` | `workspace-server.ts` |
| 3 | Teaching Agents to Seek Help | `workspace_server.py` | `workspace-server.ts` |
| 3 | Helping Agents Find Guidance | `workspace_server.py` | `workspace-server.ts` |
| 3 | Helping AI Agents on the Fly | `workspace_server.py` | `workspace-server.ts` |
| 3 | Helping AI Agents Discover Workspace-related Guidance | `workspace_agent.py` | `workspace-agent.ts` |
| 4 | Responses are More than Data | `expense_server.py` | `expense-server.ts` |
| 4 | Designing Errors to Help AI Agents | `expense_server.py` | `expense-server.ts` |
| 4 | Errors in Complex Workflows | `expense_server.py` | `expense-server.ts` |
| 4 | Minimizing AI Agent Cognitive Burden from Error Recovery | `expense_server.py` | `expense-server.ts` |
| 4 | Helping AI Agents Find Alternative Paths to Fix Errors | `expense_server.py` | `expense-server.ts` |
| 5 | Managing AI Agent Cognitive Load | `agent_heavy_server.py`<br>`tool_heavy_server.py` | `agent-heavy-server.ts`<br>`tool-heavy-server.ts` |
| 5 | Predictability, Lower Cost, Speed: Scripted Orchestration | `scripted_orchestration_server.py` | `scripted-orchestration-server.ts` |
| 5 | Self-Prompting: Adding Reasoning to Tools | `self_prompting_server.py` | `self-prompting-server.ts` |
| 5 | AI Agent Tool Design for Common Errors | `validate_at_source_server.py` | `validate-at-source-server.ts` |

---

## Environment Setup

Create a `.env` file in each module's `code/` directory.

### For Python (supports multiple providers):
```env
OPENAI_API_KEY=your-openai-key-here
ANTHROPIC_API_KEY=your-anthropic-key-here
GOOGLE_API_KEY=your-google-key-here
```

### For TypeScript (OpenAI only):
```env
OPENAI_API_KEY=your-openai-key-here
```

---

## Project Structure

Each module contains both Python and TypeScript implementations:

```
code-repo/
├── README.md
│
├── 01-intro-to-mcp-agents/
│   └── code/
│       ├── Python Files:
│       │   ├── server.py              # Module 2: Building Your First MCP Server
│       │   ├── agent.py               # Module 2: Building Your First MCP AI Agent
│       │   ├── llm.py                 # LLM utilities (OpenAI/Anthropic/Gemini)
│       │   ├── workspace_server.py    # Module 3: All workspace/context items
│       │   ├── workspace_agent.py     # Module 3: Workspace-related Guidance
│       │   ├── test_server.py         # Server testing
│       │   ├── requirements.txt       # Python dependencies
│       │   └── README.md              # Python setup instructions
│       │
│       ├── TypeScript Files:
│       │   ├── server.ts              # Module 2: Building Your First MCP Server
│       │   ├── agent.ts               # Module 2: Building Your First MCP AI Agent
│       │   ├── llm.ts                 # LLM utilities
│       │   ├── workspace-server.ts    # Module 3: All workspace/context items
│       │   ├── workspace-agent.ts     # Module 3: Workspace-related Guidance
│       │   ├── test-server.ts         # Server testing
│       │   └── package.json           # TypeScript dependencies
│       │
│       └── workspace/                 # Sample workspace with .context.md files
│
├── 02-failing-forward/
│   └── code/
│       ├── Python Files:
│       │   ├── expense_server.py           # Module 4: All error handling items
│       │   ├── expense_agent.py            # Agent for expense workflows
│       │   ├── test_failing_forward.py     # Pattern tests
│       │   ├── requirements.txt            # Python dependencies
│       │   └── README.md                   # Python setup instructions
│       │
│       └── TypeScript Files:
│           ├── expense-server.ts           # Module 4: All error handling items
│           ├── expense-agent.ts            # Agent for expense workflows
│           ├── test-failing-forward.ts     # Pattern tests
│           └── package.json                # TypeScript dependencies
│
└── 03-intelligence-budget/
    └── code/
        ├── Python Files:
        │   ├── agent_heavy_server.py           # Module 5: Managing Cognitive Load
        │   ├── tool_heavy_server.py            # Module 5: Managing Cognitive Load
        │   ├── hybrid_server.py                # Balanced approach
        │   ├── scripted_orchestration_server.py # Module 5: Scripted Orchestration
        │   ├── self_prompting_server.py        # Module 5: Self-Prompting
        │   ├── validate_at_source_server.py    # Module 5: Tool Design for Errors
        │   ├── database.py                     # Shared mock database
        │   ├── test_all.py                     # Comparison tests
        │   ├── requirements.txt                # Python dependencies
        │   └── README.md                       # Python setup instructions
        │
        └── TypeScript Files:
            ├── agent-heavy-server.ts           # Module 5: Managing Cognitive Load
            ├── tool-heavy-server.ts            # Module 5: Managing Cognitive Load
            ├── hybrid-server.ts                # Balanced approach
            ├── scripted-orchestration-server.ts # Module 5: Scripted Orchestration
            ├── self-prompting-server.ts        # Module 5: Self-Prompting
            ├── validate-at-source-server.ts    # Module 5: Tool Design for Errors
            ├── database.ts                     # Shared mock database
            ├── test-all.ts                     # Comparison tests
            └── package.json                    # TypeScript dependencies
```

---

## License

MIT
