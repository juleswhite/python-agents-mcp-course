"""
File Research Agent with Active Learning - Tutorial 03

This agent demonstrates the Active Learning pattern:
it reads available resources BEFORE using tools, building
contextual knowledge that helps it act more effectively.

Run with: python agent_with_learning.py "Your question here"

Example:
  python agent_with_learning.py "What is this project about?"
  python agent_with_learning.py "How should I explore this codebase?"
"""

import asyncio
import sys
from typing import Any

from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pydantic import AnyUrl

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


async def run_agent_with_learning(user_message: str) -> None:
    """Run the file research agent with active learning."""
    # Create LLM (auto-detects from environment variables)
    llm = create_llm_from_env()

    # ========================================
    # PERCEIVE: Connect, discover tools AND resources
    # ========================================
    print("Connecting to MCP server...\n")

    server_params = StdioServerParameters(
        command="python",
        args=["server_with_resources.py"],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as client:
            await client.initialize()

            # Discover tools
            tools_result = await client.list_tools()
            mcp_tools = tools_result.tools
            tools = mcp_tools_to_llm_tools(mcp_tools)
            print(f"Discovered {len(tools)} tools: {', '.join(t.name for t in tools)}")

            # Discover resources
            resources_result = await client.list_resources()
            resources = resources_result.resources
            print(f"Discovered {len(resources)} resources: {', '.join(r.name for r in resources)}\n")

            # ========================================
            # ACTIVE LEARNING: Read resources before acting
            # ========================================
            print("=== ACTIVE LEARNING PHASE ===")
            print("Reading available resources to build context...\n")

            context_knowledge = ""

            for resource in resources:
                print(f"Reading: {resource.name} ({resource.uri})")
                try:
                    content = await client.read_resource(AnyUrl(str(resource.uri)))
                    if content.contents:
                        first_content = content.contents[0]
                        if hasattr(first_content, "text"):
                            text = first_content.text
                        else:
                            text = str(first_content)
                        context_knowledge += f"\n\n## {resource.name}\n{text}"
                        print(f"  \u2713 Loaded {len(text)} characters")
                except Exception as e:
                    print(f"  \u2717 Failed to read: {e}")

            print("\n=== LEARNING COMPLETE ===\n")

            # ========================================
            # INITIALIZE CONVERSATION WITH LEARNED CONTEXT
            # ========================================
            messages: list[Message] = [
                Message(
                    role="system",
                    content=f"""You are a research assistant that can explore and analyze files in a folder.

IMPORTANT: You have studied the following documentation before starting. Use this knowledge to guide your exploration and provide better answers:

{context_knowledge}

Your job is to help users understand what's in a codebase or document collection.
Follow the recommended workflows and best practices from the documentation above.

When exploring:
1. Follow the "Recommended Workflow" from the guide
2. Use the file patterns knowledge to prioritize what to read
3. Read documentation files before diving into code
4. Synthesize information from multiple files to answer questions

Be thorough but concise.""",
                ),
                Message(role="user", content=user_message),
            ]

            # ========================================
            # THE AGENT LOOP (same as before)
            # ========================================
            iteration = 0
            max_iterations = 10

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
                        preview = result_text[:200]
                        suffix = "..." if len(result_text) > 200 else ""
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


# ========================================
# Main entry point
# ========================================
if __name__ == "__main__":
    user_message = sys.argv[1] if len(sys.argv) > 1 else "What is this project and how is it structured?"

    print("=" * 50)
    print("FILE RESEARCH AGENT (with Active Learning)")
    print("=" * 50)
    print(f"\nQuestion: {user_message}\n")

    try:
        asyncio.run(run_agent_with_learning(user_message))
    except Exception as e:
        print(f"Agent error: {e}", file=sys.stderr)
        sys.exit(1)
