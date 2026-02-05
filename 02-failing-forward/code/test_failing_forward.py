"""
Failing Forward - Server Demo

This script demonstrates the Failing Forward pattern by making direct
tool calls and showing the structured responses.

The key insight: the tool responses contain everything an agent needs
to recover from errors - next_action, next_action_params, hints, etc.

Run with: python test_failing_forward.py
"""

import asyncio
import json
from datetime import datetime
from typing import Any

from dotenv import load_dotenv
from mcp import types
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

# Load environment variables
load_dotenv()


# ============================================================================
# Helpers
# ============================================================================


def get_result_text(result: types.CallToolResult) -> str:
    """Extract text from MCP tool result."""
    if not result.content:
        return "(no output)"
    parts = []
    for content in result.content:
        if isinstance(content, types.TextContent):
            parts.append(content.text)
        else:
            parts.append(json.dumps(content.model_dump() if hasattr(content, 'model_dump') else str(content)))
    return "\n".join(parts)


def parse_result(result: types.CallToolResult) -> dict[str, Any]:
    """Parse tool result text into dictionary."""
    return json.loads(get_result_text(result))


# ============================================================================
# Main Demo
# ============================================================================


async def run_demo() -> None:
    """Run the Failing Forward pattern demo."""
    print("\n" + "=" * 70)
    print("FAILING FORWARD PATTERN - SERVER DEMO")
    print("=" * 70)
    print("\nThis demo shows how tool responses guide agent behavior.")
    print("Notice how each error response includes next_action and hints.\n")

    # Connect to the expense server
    server_params = StdioServerParameters(
        command="python",
        args=["expense_server.py"],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("Connected to Expense Server\n")

            today = datetime.now().strftime("%Y-%m-%d")

            # ====================================================================
            # Demo 1: Receipt Required
            # ====================================================================
            print("=" * 70)
            print("DEMO 1: Receipt Required Error")
            print("=" * 70)
            print("\nSubmitting a $75 expense WITHOUT a receipt...\n")

            demo1 = await session.call_tool(
                name="submit_expense",
                arguments={
                    "amount": 75,
                    "category": "meals",
                    "description": "Team lunch at downtown cafe",
                    "date": today,
                },
            )
            demo1_result = parse_result(demo1)

            print("TOOL RESPONSE:")
            print(json.dumps(demo1_result, indent=2))
            print("\n📌 KEY INSIGHT: The response tells the agent exactly what to do next:")
            print(f'   - next_action: "{demo1_result.get("next_action")}"')
            print(f'   - hint: "{demo1_result.get("hint")}"')
            print("   - Pre-filled params include supported formats and size limits")

            # ====================================================================
            # Demo 2: Invalid Category
            # ====================================================================
            print("\n" + "=" * 70)
            print("DEMO 2: Invalid Category Error")
            print("=" * 70)
            print("\nSubmitting with category 'food' instead of 'meals'...\n")

            demo2 = await session.call_tool(
                name="submit_expense",
                arguments={
                    "amount": 20,
                    "category": "food",
                    "description": "Quick lunch",
                    "date": today,
                },
            )
            demo2_result = parse_result(demo2)

            print("TOOL RESPONSE:")
            print(json.dumps(demo2_result, indent=2))
            print("\n📌 KEY INSIGHT: The response provides valid options and a hint:")
            print(f'   - valid_options: {json.dumps(demo2_result.get("valid_options"))}')
            print(f'   - hint: "{demo2_result.get("hint")}"')

            # ====================================================================
            # Demo 3: Large Expense Needs Approval
            # ====================================================================
            print("\n" + "=" * 70)
            print("DEMO 3: Approval Required for Large Expense")
            print("=" * 70)
            print("\nSubmitting a $200 expense (over approval threshold)...\n")

            demo3 = await session.call_tool(
                name="submit_expense",
                arguments={
                    "amount": 200,
                    "category": "meals",
                    "description": "Client dinner",
                    "date": today,
                    "receipt_url": "https://example.com/receipt.jpg",
                },
            )
            demo3_result = parse_result(demo3)

            print("TOOL RESPONSE:")
            print(json.dumps(demo3_result, indent=2))
            print("\n📌 KEY INSIGHT: The response guides to the approval flow:")
            print(f'   - next_action: "{demo3_result.get("next_action")}"')
            print("   - Pre-filled params preserve all the expense details")

            # ====================================================================
            # Demo 4: Following the Recovery Flow
            # ====================================================================
            print("\n" + "=" * 70)
            print("DEMO 4: Complete Recovery Flow")
            print("=" * 70)
            print("\nWatch how the tool responses chain together:\n")

            # Step 1: Submit without receipt
            print("Step 1: Submit $50 expense (no receipt)")
            step1 = await session.call_tool(
                name="submit_expense",
                arguments={
                    "amount": 50,
                    "category": "meals",
                    "description": "Business lunch",
                    "date": today,
                },
            )
            step1_result = parse_result(step1)
            print(f'   Status: {step1_result.get("status")} ({step1_result.get("error")})')
            print(f'   Next action: {step1_result.get("next_action")}')

            # Step 2: Upload receipt
            print("\nStep 2: Upload receipt (following the guidance)")
            step2 = await session.call_tool(
                name="upload_receipt",
                arguments={
                    "expense_amount": 50,
                    "file_type": "image/jpeg",
                },
            )
            step2_result = parse_result(step2)
            print(f'   Status: {step2_result.get("status")}')
            print(f'   Receipt URL: {step2_result.get("receipt_url")}')
            print(f'   Next action: {step2_result.get("next_action")}')

            # Step 3: Resubmit with receipt
            print("\nStep 3: Resubmit with receipt URL")
            step3 = await session.call_tool(
                name="submit_expense",
                arguments={
                    "amount": 50,
                    "category": "meals",
                    "description": "Business lunch",
                    "date": today,
                    "receipt_url": step2_result.get("receipt_url"),
                },
            )
            step3_result = parse_result(step3)
            print(f'   Status: {step3_result.get("status")}')
            print(f'   Expense ID: {step3_result.get("expense_id")}')
            print(f'   Message: {step3_result.get("message")}')

            print("\n📌 KEY INSIGHT: The agent never needed special instructions.")
            print("   The tool responses guided the entire recovery flow.\n")

            # ====================================================================
            # Demo 5: Successful Small Expense
            # ====================================================================
            print("=" * 70)
            print("DEMO 5: Successful Small Expense (No Issues)")
            print("=" * 70)
            print("\nSubmitting a $15 expense (under receipt threshold)...\n")

            demo5 = await session.call_tool(
                name="submit_expense",
                arguments={
                    "amount": 15,
                    "category": "meals",
                    "description": "Coffee meeting",
                    "date": today,
                },
            )
            demo5_result = parse_result(demo5)

            print("TOOL RESPONSE:")
            print(json.dumps(demo5_result, indent=2))
            print("\n📌 Success responses also provide guidance:")
            print(f'   - tell_user: "{demo5_result.get("tell_user")}"')

            # ====================================================================
            # Summary
            # ====================================================================
            print("\n" + "=" * 70)
            print("SUMMARY: The Failing Forward Pattern")
            print("=" * 70)
            print("""
The key insight: Tool responses ARE instructions.

When an error occurs, the response includes:
  • status: What happened ("failed", "needs_action")
  • error: Machine-readable error code
  • message: Human-readable explanation
  • next_action: What tool to call next
  • next_action_params: Pre-filled parameters for that tool
  • hint: Strategy guidance for the agent
  • tell_user: What to communicate to the user

An agent with just a MINIMAL system prompt ("You are an expense assistant")
can successfully navigate complex workflows because the tool responses
teach it what to do at each step.

To see this in action with a real agent, run:
  python expense_agent.py "Submit a 75 dollar lunch expense"
""")


def main() -> None:
    """Entry point for the demo."""
    asyncio.run(run_demo())


if __name__ == "__main__":
    main()
