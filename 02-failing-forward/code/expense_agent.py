"""
Expense Agent - Demonstrating Response-as-Instruction

This agent has a MINIMAL system prompt. It doesn't know about "Failing Forward"
or any special error handling patterns. It's just an expense assistant.

The key insight: the agent successfully navigates complex workflows because
the TOOL RESPONSES guide it. The tools return structured responses with
next_action, next_action_params, and hints that teach the agent what to do.

This demonstrates that well-designed tool responses can guide any reasonable
LLM without requiring special instructions about the pattern.

Run with: python expense_agent.py "Submit a $150 dinner with client from last week"
"""

import asyncio
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from dotenv import load_dotenv
from mcp import types
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from openai import OpenAI

# Load environment variables
load_dotenv()

# Verify API key
if not os.environ.get("OPENAI_API_KEY"):
    print("Error: OPENAI_API_KEY not found. Set it in .env file or environment.")
    sys.exit(1)

openai_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])


# ============================================================================
# Types
# ============================================================================


@dataclass
class ToolResult:
    """Parsed tool result structure."""

    status: str
    message: str
    error: str | None = None
    next_action: str | None = None
    next_action_params: dict[str, Any] | None = None
    hint: str | None = None
    tell_user: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ToolResult":
        return cls(
            status=data.get("status", ""),
            message=data.get("message", ""),
            error=data.get("error"),
            next_action=data.get("next_action"),
            next_action_params=data.get("next_action_params"),
            hint=data.get("hint"),
            tell_user=data.get("tell_user"),
        )


# Type aliases for Responses API
ResponsesInputItem = dict[str, Any]
FunctionCallOutput = dict[str, Any]


# ============================================================================
# Helper Functions
# ============================================================================


def mcp_tools_to_responses_api(mcp_tools: list[types.Tool]) -> list[dict[str, Any]]:
    """Convert MCP tools to OpenAI Responses API format."""
    result = []
    for tool in mcp_tools:
        tool_def = {
            "type": "function",
            "name": tool.name,
            "description": tool.description or f"Tool: {tool.name}",
            "parameters": tool.inputSchema if tool.inputSchema else {"type": "object", "properties": {}},
            "strict": False,
        }
        result.append(tool_def)
    return result


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


def parse_tool_result(result_text: str) -> ToolResult | None:
    """Parse JSON tool result text into ToolResult."""
    try:
        data = json.loads(result_text)
        return ToolResult.from_dict(data)
    except (json.JSONDecodeError, KeyError):
        return None


def get_output_text(response: Any) -> str | None:
    """Extract output text from Responses API response."""
    # The Responses API provides output_text as a convenience property
    if hasattr(response, "output_text") and response.output_text:
        return response.output_text

    # Fallback: look through output items for message content
    if hasattr(response, "output") and response.output:
        for item in response.output:
            if getattr(item, "type", None) == "message":
                content_list = getattr(item, "content", None)
                if content_list:
                    for content in content_list:
                        if getattr(content, "type", None) == "output_text":
                            text = getattr(content, "text", None)
                            if text:
                                return text

    return None


def has_function_calls(response: Any) -> bool:
    """Check if response contains function calls."""
    if not hasattr(response, "output") or not response.output:
        return False
    return any(getattr(item, "type", None) == "function_call" for item in response.output)


def get_function_calls(response: Any) -> list[Any]:
    """Get function call items from response."""
    if not hasattr(response, "output") or not response.output:
        return []
    return [item for item in response.output if getattr(item, "type", None) == "function_call"]


# ============================================================================
# Main Agent Loop
# ============================================================================


async def run_agent(user_message: str) -> None:
    """Run the expense agent with the given user message."""
    print("\n" + "=" * 60)
    print("FAILING FORWARD EXPENSE AGENT")
    print("=" * 60)
    print(f"\nUser request: {user_message}\n")

    # Connect to the expense server
    print("Connecting to Expense Server...\n")

    server_params = StdioServerParameters(
        command="python",
        args=["expense_server.py"],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools_result = await session.list_tools()
            mcp_tools = tools_result.tools
            tools = mcp_tools_to_responses_api(mcp_tools)
            print(f"Discovered {len(tools)} tools: {', '.join(t.name for t in mcp_tools)}\n")

            # MINIMAL system prompt - the agent knows NOTHING about "Failing Forward"
            # or any special error handling patterns. It's just an expense assistant.
            # The tool responses will guide it through any issues.
            today = datetime.now().strftime("%Y-%m-%d")
            system_instructions = f"""You are an expense submission assistant that helps users submit business expenses.

Today's date is {today}.

Be helpful and guide the user through the expense submission process."""

            # Build input for Responses API
            # The input array holds the conversation context
            input_messages: list[ResponsesInputItem] = [
                {
                    "role": "user",
                    "content": user_message,
                }
            ]

            # Agent loop
            iteration = 0
            max_iterations = 10

            while iteration < max_iterations:
                iteration += 1
                print(f"\n--- Iteration {iteration} ---")

                # Call the Responses API
                response = openai_client.responses.create(
                    model="gpt-4o-mini",
                    instructions=system_instructions,
                    input=input_messages,
                    tools=tools,
                )

                # Check if the model wants to call functions
                if has_function_calls(response):
                    function_calls = get_function_calls(response)

                    for function_call in function_calls:
                        args = json.loads(function_call.arguments)
                        print(f"\nCalling: {function_call.name}")
                        print(f"Arguments: {json.dumps(args, indent=2)}")

                        result = await session.call_tool(
                            name=function_call.name,
                            arguments=args,
                        )

                        result_text = get_result_text(result)
                        parsed = parse_tool_result(result_text)

                        # Show the result
                        print("\nResult:")
                        if parsed:
                            print(f"  Status: {parsed.status}")
                            if parsed.error:
                                print(f"  Error: {parsed.error}")
                            print(f"  Message: {parsed.message}")
                            if parsed.next_action:
                                print(f"  Next Action: {parsed.next_action}")
                                if parsed.next_action_params:
                                    print(f"  Next Action Params: {json.dumps(parsed.next_action_params, indent=4)}")
                            if parsed.hint:
                                print(f"  Hint: {parsed.hint}")
                        else:
                            print(f"  {result_text[:200]}...")

                        # Add the function call and its output to the input for the next iteration
                        # First, add the function call that was made
                        input_messages.append({
                            "type": "function_call",
                            "call_id": function_call.call_id,
                            "name": function_call.name,
                            "arguments": function_call.arguments,
                        })

                        # Then add the function call output
                        input_messages.append({
                            "type": "function_call_output",
                            "call_id": function_call.call_id,
                            "output": result_text,
                        })
                else:
                    # Agent finished - show final response
                    output_text = get_output_text(response)
                    print("\n" + "=" * 60)
                    print("FINAL RESPONSE")
                    print("=" * 60)
                    print(f"\n{output_text}\n")
                    break

            if iteration >= max_iterations:
                print("\n(Reached maximum iterations)")


# ============================================================================
# Entry Point
# ============================================================================


def main() -> None:
    """Entry point for the expense agent."""
    user_message = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "Submit a $150 dinner expense with a client from last Tuesday"
    )
    asyncio.run(run_agent(user_message))


if __name__ == "__main__":
    main()
