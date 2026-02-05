# Failing Forward Pattern - Python Implementation

This is the Python implementation of the "Failing Forward" MCP pattern, demonstrating how tool responses can guide agents through complex workflows without requiring special instructions.

## Overview

The Failing Forward pattern demonstrates four key techniques:

1. **Errors as Curriculum** - Teaching errors that guide recovery
2. **Error Chains** - Multi-step recovery processes
3. **Pre-filled Parameters** - Handing agents everything they need
4. **Alternative Actions** - Multiple paths to success

## Files

- `expense_server.py` - MCP server implementing the expense submission tools
- `expense_agent.py` - Agent that uses the tools via OpenAI's Responses API
- `test_failing_forward.py` - Demo script showing the pattern in action

## Setup

### 1. Create a Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

Create a `.env` file with your OpenAI API key:

```
OPENAI_API_KEY=your-api-key-here
```

## Running the Demo

### Test the Server Pattern

This demo shows the structured responses from the expense server:

```bash
python test_failing_forward.py
```

This will demonstrate:
- Receipt required errors with recovery guidance
- Invalid category errors with suggestions
- Approval workflows for large expenses
- Complete recovery flow from error to success

### Run the Agent

Run the expense agent with a custom message:

```bash
python expense_agent.py "Submit a $150 dinner expense with a client from last Tuesday"
```

Or use the default message:

```bash
python expense_agent.py
```

## Key Insight

The agent has a **MINIMAL system prompt** - it knows nothing about "Failing Forward" or any special error handling patterns. It's just an expense assistant.

The agent successfully navigates complex workflows because the **tool responses guide it**. Each tool returns structured responses with:

- `status` - What happened ("success", "failed", "needs_action")
- `error` - Machine-readable error code
- `message` - Human-readable explanation
- `next_action` - What tool to call next
- `next_action_params` - Pre-filled parameters for that tool
- `hint` - Strategy guidance for the agent
- `tell_user` - What to communicate to the user

This demonstrates that well-designed tool responses can guide any reasonable LLM without requiring special instructions about the pattern.

## Example Tool Response

When submitting an expense over $25 without a receipt:

```json
{
  "status": "needs_action",
  "error": "receipt_required",
  "message": "Expenses over $25 require a receipt. This expense is $75.00.",
  "next_action": "upload_receipt",
  "next_action_params": {
    "expense_amount": 75,
    "expense_category": "meals",
    "expense_description": "Team lunch at downtown cafe",
    "expense_date": "2024-01-15",
    "supported_formats": ["image/jpeg", "image/png", "application/pdf"],
    "max_size_mb": 10
  },
  "hint": "Ask the user to provide a photo or scan of the receipt. Once uploaded, retry submit_expense with the receipt_url.",
  "tell_user": "Since this expense is over $25, I'll need a photo or scan of the receipt. Could you upload it?"
}
```

The response tells the agent exactly what to do next, with all parameters pre-filled!
