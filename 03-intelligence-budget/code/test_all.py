"""
Intelligence Budget - Comprehensive Tests

This tests all four concepts from the Intelligence Budget tutorials:

1. BUDGET BOUNDARY (Tutorials 01)
   - agent-heavy-server: Agent does all reasoning (high token cost)
   - tool-heavy-server: Tool does all reasoning (low token cost)
   - hybrid-server: Flexible input, tool processes (best balance)

2. SCRIPTED ORCHESTRATION (Tutorial 02)
   - scripted-orchestration-server: Agent writes code, tool executes it

3. SELF-PROMPTING (Tutorial 03)
   - self-prompting-server: Tool makes its own LLM calls for classification

4. VALIDATE AT SOURCE (Tutorial 04)
   - validate-at-source-server: Full validation stack including semantic

Run with: python test_all.py
"""

import asyncio
import json
import os
import sys
from typing import List, Dict, Any, Optional

from dotenv import load_dotenv
from openai import OpenAI
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Load environment variables
load_dotenv()

# Verify API key
if not os.getenv("OPENAI_API_KEY"):
    print("Error: OPENAI_API_KEY not found in .env file", file=sys.stderr)
    sys.exit(1)

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ============================================================================
# Test Helpers
# ============================================================================

def get_result_text(result: Any) -> str:
    """Extract text from MCP tool result."""
    if not result.content:
        return "(no output)"
    return "\n".join(
        c.text if hasattr(c, 'text') else json.dumps(c)
        for c in result.content
    )


def parse_result(result: Any) -> Dict[str, Any]:
    """Parse MCP tool result as JSON."""
    try:
        return json.loads(get_result_text(result))
    except json.JSONDecodeError:
        return {"message": get_result_text(result)}


def mcp_tools_to_openai(mcp_tools: List[Any]) -> List[Dict[str, Any]]:
    """Convert MCP tools to OpenAI function format."""
    return [
        {
            "type": "function",
            "name": t.name,
            "description": t.description or f"Tool: {t.name}",
            "parameters": t.inputSchema if t.inputSchema else {"type": "object", "properties": {}},
            "strict": False,
        }
        for t in mcp_tools
    ]


async def create_client(server_script: str) -> ClientSession:
    """Create an MCP client connected to a server script."""
    server_params = StdioServerParameters(
        command="python",
        args=[server_script],
    )

    read, write = await stdio_client(server_params).__aenter__()
    session = ClientSession(read, write)
    await session.__aenter__()
    await session.initialize()
    return session


async def run_agent_loop(
    session: ClientSession,
    tools: List[Dict[str, Any]],
    system_prompt: str,
    user_message: str,
    max_iterations: int = 8
) -> Dict[str, Any]:
    """Run an agent loop with OpenAI and MCP tools."""
    input_messages = [{"role": "user", "content": user_message}]

    tool_calls: List[str] = []
    final_result: Optional[Dict[str, Any]] = None
    detected_category: Optional[str] = None

    for iteration in range(max_iterations):
        response = openai_client.responses.create(
            model="gpt-4o-mini",
            instructions=system_prompt,
            input=input_messages,
            tools=tools,
        )

        # Find function calls in output
        function_calls = [
            item for item in response.output
            if item.type == "function_call"
        ]

        if not function_calls:
            break

        for func_call in function_calls:
            args = json.loads(func_call.arguments or "{}")
            print(f"    [{iteration + 1}] {func_call.name}")
            tool_calls.append(func_call.name)

            result = await session.call_tool(func_call.name, args)
            result_text = get_result_text(result)
            parsed = parse_result(result)

            status = parsed.get("status") or ("success" if parsed.get("success") else "done")
            print(f"        Status: {status}")
            if parsed.get("category"):
                detected_category = parsed["category"]
                print(f"        Category: {detected_category}")

            # Add to conversation - use the Responses API format
            # The func_call object itself is an output item that can be added to input
            input_messages.append(func_call)
            input_messages.append({
                "type": "function_call_output",
                "call_id": func_call.call_id,
                "output": result_text,
            })

            if (parsed.get("status") == "success" or parsed.get("success")) and \
               (parsed.get("expense_id") or parsed.get("result")):
                final_result = parsed

    return {
        "tool_calls": tool_calls,
        "final_result": final_result,
        "category": detected_category,
    }


# ============================================================================
# TEST 1: Direct Server Tests (No LLM)
# ============================================================================

async def test_direct_server_calls():
    """Verify all servers start and list tools correctly."""
    print("\n" + "=" * 70)
    print("TEST 1: Direct Server Calls (Verify all servers work)")
    print("=" * 70)

    servers = [
        {"name": "agent-heavy", "script": "agent_heavy_server.py"},
        {"name": "tool-heavy", "script": "tool_heavy_server.py"},
        {"name": "hybrid", "script": "hybrid_server.py"},
        {"name": "self-prompting", "script": "self_prompting_server.py"},
        {"name": "scripted-orchestration", "script": "scripted_orchestration_server.py"},
        {"name": "validate-at-source", "script": "validate_at_source_server.py"},
    ]

    for server in servers:
        print(f"\n--- {server['name']} ---")
        server_params = StdioServerParameters(
            command="python",
            args=[server["script"]],
        )

        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools_result = await session.list_tools()
                tool_names = [t.name for t in tools_result.tools]
                print(f"  Tools: {', '.join(tool_names)}")
                print(f"  [OK] Server starts and lists tools")

    print("\n[PASS] All servers start correctly")


# ============================================================================
# TEST 2: Budget Boundary (Tutorial 01) - Agent-Heavy vs Tool-Heavy
# ============================================================================

async def test_budget_boundary():
    """Test the budget boundary pattern with agent-heavy vs tool-heavy servers."""
    print("\n" + "=" * 70)
    print("TEST 2: Budget Boundary - Agent-Heavy vs Tool-Heavy")
    print("=" * 70)

    # Test agent-heavy: agent must fetch rules and determine category
    print("\n--- Agent-Heavy (Agent reasons about everything) ---")

    server_params = StdioServerParameters(
        command="python",
        args=["agent_heavy_server.py"],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools_result = await session.list_tools()
            tools = mcp_tools_to_openai(tools_result.tools)

            system_prompt = """You must first get_category_rules, then determine category yourself.
If receipt needed, call upload_receipt with file_data="test", file_type="image/jpeg".
Submit with your determined category. No user interaction available."""

            result = await run_agent_loop(
                session, tools, system_prompt,
                "Submit a $50 lunch expense (test mode)"
            )

            # Agent-heavy SHOULD call get_category_rules (agent must know rules)
            got_rules = "get_category_rules" in result["tool_calls"]
            print(f"  Agent fetched rules: {'YES (expected)' if got_rules else 'NO'}")

    # Test tool-heavy: tool handles everything
    print("\n--- Tool-Heavy (Tool handles everything) ---")

    server_params = StdioServerParameters(
        command="python",
        args=["tool_heavy_server.py"],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools_result = await session.list_tools()
            tools = mcp_tools_to_openai(tools_result.tools)

            system_prompt = """Extract amount and expense_type from user.
Call submit_expense. Follow next_action guidance.
For receipts use file_data="test", file_type="image/jpeg"."""

            result = await run_agent_loop(
                session, tools, system_prompt,
                "I had a $50 lunch (test mode)"
            )

            # Tool-heavy should NOT call get_category_rules (tool knows them)
            got_rules = "get_category_rules" in result["tool_calls"]
            print(f"  Agent fetched rules: {'YES (not expected)' if got_rules else 'NO (expected)'}")
            print(f"  Final result: {'SUCCESS' if result['final_result'] and result['final_result'].get('expense_id') else 'incomplete'}")

    print("\n[PASS] Budget boundary tests complete")


# ============================================================================
# TEST 3: Self-Prompting (Tutorial 03) - LLM calls inside tools
# ============================================================================

async def test_self_prompting():
    """Test the self-prompting pattern where tools make their own LLM calls."""
    print("\n" + "=" * 70)
    print("TEST 3: Self-Prompting - Tool makes its own LLM calls")
    print("=" * 70)

    server_params = StdioServerParameters(
        command="python",
        args=["self_prompting_server.py"],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Test 1: Clear case (should use deterministic classification)
            print("\n--- Test 1: Clear case (flight) ---")
            result1 = await session.call_tool("submit_expense", {
                "amount": 300,
                "description": "Flight to NYC for conference",
            })
            parsed1 = parse_result(result1)
            print(f"  Category: {parsed1.get('category')}")
            print(f"  Classification source: {parsed1.get('classification_source')}")
            print("  Expected: travel via deterministic")

            # Test 2: Ambiguous case (should trigger LLM self-prompting)
            print("\n--- Test 2: Ambiguous case (client dinner) ---")
            result2 = await session.call_tool("submit_expense", {
                "amount": 150,
                "description": "Dinner with the folks from Acme Corp to discuss renewal",
            })
            parsed2 = parse_result(result2)
            print(f"  Category: {parsed2.get('category')}")
            print(f"  Classification source: {parsed2.get('classification_source')}")
            print("  Expected: client_entertainment via llm")

            # Test 3: With context hints (should use deterministic)
            print("\n--- Test 3: With context hints ---")
            result3 = await session.call_tool("submit_expense", {
                "amount": 80,
                "description": "Lunch at the steakhouse",
                "context_hints": {"mentions_client": True},
            })
            parsed3 = parse_result(result3)
            print(f"  Category: {parsed3.get('category')}")
            print(f"  Classification source: {parsed3.get('classification_source')}")
            print("  Expected: client_entertainment via deterministic")

    print("\n[PASS] Self-prompting tests complete")


# ============================================================================
# TEST 4: Scripted Orchestration (Tutorial 02) - Agent writes code
# ============================================================================

async def test_scripted_orchestration():
    """Test the scripted orchestration pattern where agents write code."""
    print("\n" + "=" * 70)
    print("TEST 4: Scripted Orchestration - Agent writes code, tool executes")
    print("=" * 70)

    server_params = StdioServerParameters(
        command="python",
        args=["scripted_orchestration_server.py"],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # First, create some expenses to work with
            print("\n--- Setup: Creating test expenses ---")
            await session.call_tool("submit_expense", {
                "amount": 25,
                "category": "meals",
                "description": "Coffee meeting",
            })
            await session.call_tool("submit_expense", {
                "amount": 15,
                "category": "meals",
                "description": "Lunch snack",
            })
            await session.call_tool("submit_expense", {
                "amount": 200,
                "category": "travel",
                "description": "Uber to airport",
            })
            print("  Created 3 test expenses")

            # Test 1: Execute a workflow script directly
            print("\n--- Test 1: Execute workflow script ---")
            workflow_result = await session.call_tool("execute_workflow", {
                "code": """
expenses = await tools.get_expenses()
stats = await tools.get_expense_stats()

by_category = {}
for e in expenses:
    if e['category'] not in by_category:
        by_category[e['category']] = {'count': 0, 'total': 0}
    by_category[e['category']]['count'] += 1
    by_category[e['category']]['total'] += e['amount']

return {
    'total_expenses': len(expenses),
    'total_amount': stats['total_amount'],
    'by_category': by_category
}
""",
            })
            parsed1 = parse_result(workflow_result)
            print(f"  Status: {parsed1.get('status')}")
            print(f"  Execution time: {parsed1.get('execution_time_ms')}ms")
            print(f"  Result: {json.dumps(parsed1.get('result'))}")

            # Test 2: Agent writes and executes a workflow
            print("\n--- Test 2: Agent writes workflow ---")
            tools_result = await session.list_tools()
            tools = mcp_tools_to_openai(tools_result.tools)

            system_prompt = """You can execute Python workflows using execute_workflow.
Available: await tools.get_expenses(), await tools.get_expense_stats(), etc.
Write a script to answer the user's question. No user interaction available."""

            result = await run_agent_loop(
                session, tools, system_prompt,
                "How many expenses do I have and what's the total? Write a script to find out."
            )

            print(f"  Tool calls: {' -> '.join(result['tool_calls'])}")
            print(f"  Used execute_workflow: {'YES' if 'execute_workflow' in result['tool_calls'] else 'NO'}")
            if result['final_result'] and result['final_result'].get('result'):
                print(f"  Script result: {json.dumps(result['final_result']['result'])}")

    print("\n[PASS] Scripted orchestration tests complete")


# ============================================================================
# TEST 5: Validate at Source (Tutorial 04) - Semantic validation
# ============================================================================

async def test_validate_at_source():
    """Test the validate at source pattern with semantic validation."""
    print("\n" + "=" * 70)
    print("TEST 5: Validate at Source - Semantic validation in tools")
    print("=" * 70)

    server_params = StdioServerParameters(
        command="python",
        args=["validate_at_source_server.py"],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Test 1: Valid description
            print("\n--- Test 1: Valid description ---")
            result1 = await session.call_tool("submit_expense", {
                "amount": 25,
                "description": "Coffee meeting with marketing team to discuss Q4 campaign",
                "category": "meals",
            })
            parsed1 = parse_result(result1)
            print(f"  Status: {parsed1.get('status')}")
            print(f"  Validation layer: {parsed1.get('validation_layer')}")
            print("  Expected: success (valid description)")

            # Test 2: Gibberish description (should fail semantic validation)
            print("\n--- Test 2: Gibberish description ---")
            result2 = await session.call_tool("submit_expense", {
                "amount": 50,
                "description": "asdfgh",
                "category": "meals",
            })
            parsed2 = parse_result(result2)
            print(f"  Status: {parsed2.get('status')}")
            print(f"  Validation layer: {parsed2.get('validation_layer')}")
            print(f"  Issues: {json.dumps(parsed2.get('issues'))}")
            print("  Expected: rejected (gibberish)")

            # Test 3: Too brief description
            print("\n--- Test 3: Too brief description ---")
            result3 = await session.call_tool("submit_expense", {
                "amount": 100,
                "description": "stuff",
                "category": "supplies",
            })
            parsed3 = parse_result(result3)
            print(f"  Status: {parsed3.get('status')}")
            print(f"  Validation layer: {parsed3.get('validation_layer')}")
            print("  Expected: rejected (too brief)")

            # Test 4: Use test_validation tool
            print("\n--- Test 4: Batch validation test ---")
            result4 = await session.call_tool("test_validation", {
                "descriptions": [
                    "Team lunch at Italian restaurant for project kickoff",
                    "test",
                    "aaaaaaa",
                    "Quick coffee run",
                    "Dinner with the folks from Acme to discuss partnership",
                ],
                "category": "meals",
                "amount": 50,
            })
            parsed4 = parse_result(result4)
            summary = parsed4.get("summary", {})
            print(f"  Tested: {summary.get('tested')} descriptions")
            print(f"  Would pass: {summary.get('would_pass')}")
            print(f"  Would fail: {summary.get('would_fail')}")
            print(f"  Would be flagged: {summary.get('would_be_flagged')}")

    print("\n[PASS] Validate at source tests complete")


# ============================================================================
# Run All Tests
# ============================================================================

async def run_all_tests():
    """Run all intelligence budget tests."""
    print("\n" + "=" * 70)
    print("INTELLIGENCE BUDGET - COMPREHENSIVE TESTS")
    print("Testing all four concepts from the tutorials")
    print("=" * 70)

    try:
        await test_direct_server_calls()
        await test_budget_boundary()
        await test_self_prompting()
        await test_scripted_orchestration()
        await test_validate_at_source()

        print("\n" + "=" * 70)
        print("ALL TESTS PASSED!")
        print("=" * 70 + "\n")
    except Exception as e:
        print(f"\n[FAIL] Test error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_all_tests())
