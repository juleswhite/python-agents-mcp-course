"""
Context-Aware Workspace Agent - Tutorial 05

This agent demonstrates the Active Learning pattern with context discovery.
It checks for directory context rules before creating or modifying files.

Run with: python workspace_agent.py "Your request here"

Examples:
  python workspace_agent.py "Create an expense for my $200 dinner at Fancy Restaurant"
  python workspace_agent.py "What are the rules for travel expenses?"
  python workspace_agent.py "Create a weekly report for Project Alpha"
"""

import asyncio
import sys
from typing import Any

from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from llm import Message, Tool, create_llm_from_env


# Load environment variables from .env file
load_dotenv()


def mcp_tools_to_llm_tools(mcp_tools: list[Any]) -> list[Tool]:
    """Convert MCP tools to our LLM format."""
    return [
        Tool(
            name=t.name,
            description=t.description or f"Tool: {t.name}",
            input_schema=t.inputSchema,
        )
        for t in mcp_tools
    ]


def get_result_text(result: Any) -> str:
    """Extract text from MCP result."""
    if not result.content:
        return "(no output)"
    parts = []
    for c in result.content:
        if c.type == "text":
            parts.append(c.text)
        else:
            parts.append(str(c))
    return "\n".join(parts)


# The system prompt that instills context discovery habits
SYSTEM_PROMPT = """You are a workspace assistant that helps manage files and content.

## CRITICAL: Context Discovery Protocol

Before creating or modifying ANY file, you MUST:
1. Call get_directory_context(path) for the target directory
2. Read and understand ALL context rules (global AND local)
3. Follow the naming conventions and required fields exactly
4. Use the templates provided in the context

This is not optional. The context files contain rules that MUST be followed.

## When Asked to Create Files

1. First, determine where the file should go based on what it is:
   - Expenses go in "expenses/" or "expenses/travel/" for travel-related
   - Reports go in "reports/"
   - Project files go in "projects/"
2. Call get_directory_context for that location
3. Follow the naming convention from the context EXACTLY
4. Include all required fields from the context
5. Use the template if one is provided

## When Asked About Rules

If the user asks about rules or conventions:
1. Call get_directory_context for the relevant directory
2. Summarize the rules clearly
3. Point out any inheritance from parent directories

## Available Tools

- list_files: See what's in a directory
- read_file: Read file contents
- write_file: Create or update files
- get_directory_context: Get rules for a directory (USE THIS FIRST!)

## File Path Convention

All paths are relative to the workspace root. Use paths like:
- "." for workspace root
- "expenses" for the expenses directory
- "expenses/travel" for travel expenses
- "reports" for reports

## Important Reminders

- Context discovery is NOT optional - always check before creating files
- Naming conventions are strict - follow them exactly
- Ask the user for any missing required information before creating files
- Show the user what you're creating before you create it"""


async def run_workspace_agent(user_message: str) -> None:
    """Run the context-aware workspace agent."""
    # Create LLM (auto-detects from environment variables)
    llm = create_llm_from_env()

    # Connect to the workspace server
    print("Connecting to workspace server...\n")

    server_params = StdioServerParameters(
        command="python",
        args=["workspace_server.py"],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as client:
            await client.initialize()

            # Discover tools
            tools_result = await client.list_tools()
            mcp_tools = tools_result.tools
            tools = mcp_tools_to_llm_tools(mcp_tools)
            print(f"Discovered {len(tools)} tools: {', '.join(t.name for t in tools)}\n")

            # Initialize conversation
            messages: list[Message] = [
                Message(role="system", content=SYSTEM_PROMPT),
                Message(role="user", content=user_message),
            ]

            # The Agent Loop
            iteration = 0
            max_iterations = 15

            while iteration < max_iterations:
                iteration += 1
                print(f"\n--- Iteration {iteration} ---")

                # DECIDE: Ask LLM what to do
                response = await llm.chat(messages, tools)

                if response.tool_calls:
                    # ACT: Execute each tool call
                    for tool_call in response.tool_calls:
                        print(f"Calling: {tool_call.name}({tool_call.arguments})")

                        result = await client.call_tool(
                            tool_call.name,
                            tool_call.arguments,
                        )

                        # OBSERVE: Process result and add to conversation
                        result_text = get_result_text(result)
                        is_error = getattr(result, "isError", False)

                        # Show a preview of the result
                        preview = result_text[:300]
                        suffix = "..." if len(result_text) > 300 else ""
                        error_note = " (error)" if is_error else ""
                        print(f"Result{error_note}: {preview}{suffix}")

                        # Add the interaction to conversation history
                        messages.append(Message(
                            role="assistant",
                            content=f"I'll use the {tool_call.name} tool.",
                        ))
                        messages.append(Message(
                            role="user",
                            content=f"Tool result:\n{result_text}",
                        ))
                else:
                    # FINISH: No tool call means the LLM is done
                    print("\n" + "=" * 50)
                    print("FINAL RESPONSE")
                    print("=" * 50 + "\n")
                    print(response.content)
                    break

            if iteration >= max_iterations:
                print("\n(Reached maximum iterations)")


# Main entry point
if __name__ == "__main__":
    user_message = sys.argv[1] if len(sys.argv) > 1 else "What directories are available and what are their rules?"

    print("=" * 50)
    print("CONTEXT-AWARE WORKSPACE AGENT")
    print("=" * 50)
    print(f"\nQuestion: {user_message}\n")

    try:
        asyncio.run(run_workspace_agent(user_message))
    except Exception as e:
        print(f"Agent error: {e}", file=sys.stderr)
        sys.exit(1)
