"""
File Research Agent - Tutorial 02

An AI agent that can explore and research files in a folder.
Demonstrates the Agent Loop: PERCEIVE -> DECIDE -> ACT -> OBSERVE -> REPEAT

Run with: python agent.py "Your question here"

Example:
  python agent.py "What files are here and what do they do?"
  python agent.py "Read package.json and explain the dependencies"
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


async def run_agent(user_message: str) -> None:
    """Run the file research agent."""
    # Create LLM (auto-detects from environment variables)
    llm = create_llm_from_env()

    # ========================================
    # PERCEIVE: Connect to MCP server and discover tools
    # ========================================
    print("Connecting to MCP server...\n")

    server_params = StdioServerParameters(
        command="python",
        args=["server.py"],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as client:
            await client.initialize()

            tools_result = await client.list_tools()
            mcp_tools = tools_result.tools
            tools = mcp_tools_to_llm_tools(mcp_tools)
            print(f"Discovered {len(tools)} tools: {', '.join(t.name for t in tools)}\n")

            # Initialize conversation with system prompt
            messages: list[Message] = [
                Message(
                    role="system",
                    content="""You are a research assistant that can explore and analyze files in a folder.

Your job is to help users understand what's in a codebase or document collection.
You can:
- List files to see what's available
- Read files to understand their contents
- Answer questions by synthesizing information from multiple files

When researching a question:
1. First explore to understand what files exist
2. Read relevant files to gather information
3. Synthesize your findings into a clear answer

Be thorough but concise. If you need to read multiple files to answer a question, do so.
When you have enough information to answer the question, provide a clear, well-organized response.""",
                ),
                Message(role="user", content=user_message),
            ]

            # ========================================
            # THE AGENT LOOP
            # ========================================
            iteration = 0
            max_iterations = 10

            while iteration < max_iterations:
                iteration += 1
                print(f"\n--- Iteration {iteration} ---")

                # ========================================
                # DECIDE: Ask LLM what to do
                # ========================================
                response = await llm.chat(messages, tools)

                if response.tool_calls:
                    # ========================================
                    # ACT: Execute each tool call
                    # ========================================
                    for tool_call in response.tool_calls:
                        print(f"Calling: {tool_call.name}({tool_call.arguments})")

                        result = await client.call_tool(
                            tool_call.name,
                            tool_call.arguments,
                        )

                        # ========================================
                        # OBSERVE: Process result and add to conversation
                        # ========================================
                        result_text = get_result_text(result)
                        is_error = getattr(result, "isError", False)

                        # Show a preview of the result
                        preview = result_text[:200]
                        suffix = "..." if len(result_text) > 200 else ""
                        error_note = " (error)" if is_error else ""
                        print(f"Result{error_note}: {preview}{suffix}")

                        # Add the interaction to conversation history
                        # This allows the LLM to see what happened and decide what to do next
                        messages.append(Message(
                            role="assistant",
                            content=f"I'll use the {tool_call.name} tool.",
                        ))
                        messages.append(Message(
                            role="user",
                            content=f"Tool result:\n{result_text}",
                        ))

                    # REPEAT: Loop continues to next iteration
                else:
                    # ========================================
                    # FINISH: No tool call means the LLM is done
                    # ========================================
                    print("\n" + "=" * 50)
                    print("FINAL RESPONSE")
                    print("=" * 50 + "\n")
                    print(response.content)
                    break

            if iteration >= max_iterations:
                print("\n(Reached maximum iterations)")


# ========================================
# Main entry point
# ========================================
if __name__ == "__main__":
    user_message = sys.argv[1] if len(sys.argv) > 1 else "What files are in the current directory?"

    print("=" * 50)
    print("FILE RESEARCH AGENT")
    print("=" * 50)
    print(f"\nQuestion: {user_message}\n")

    try:
        asyncio.run(run_agent(user_message))
    except Exception as e:
        print(f"Agent error: {e}", file=sys.stderr)
        sys.exit(1)
