"""
Test script to verify the MCP server with resources works correctly.
This tests the Active Learning pattern without needing an LLM.

Run with: python test_resources.py
"""

import asyncio
import sys
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pydantic import AnyUrl


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


async def test_resources() -> None:
    """Test the MCP server with resources."""
    print("=" * 50)
    print("MCP SERVER WITH RESOURCES TEST")
    print("=" * 50)
    print("\nConnecting to server...")

    server_params = StdioServerParameters(
        command="python",
        args=["server_with_resources.py"],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as client:
            await client.initialize()
            print("Connected!\n")

            # ========================================
            # PERCEIVE: Discover tools
            # ========================================
            print("--- PERCEIVE: Discovering tools ---")
            tools_result = await client.list_tools()
            tools = tools_result.tools
            print(f"Found {len(tools)} tools:")
            for tool in tools:
                desc = (tool.description or "")[:60]
                print(f"  - {tool.name}: {desc}...")

            # ========================================
            # PERCEIVE: Discover resources
            # ========================================
            print("\n--- PERCEIVE: Discovering resources ---")
            resources_result = await client.list_resources()
            resources = resources_result.resources
            print(f"Found {len(resources)} resources:")
            for resource in resources:
                print(f"  - {resource.name} ({resource.uri})")
                if resource.description:
                    print(f"    {resource.description}")

            # ========================================
            # ACTIVE LEARNING: Read resources
            # ========================================
            print("\n--- ACTIVE LEARNING: Reading resources ---")

            for resource in resources:
                print(f"\nReading: {resource.uri}")
                content = await client.read_resource(AnyUrl(str(resource.uri)))

                if content.contents:
                    first_content = content.contents[0]
                    if hasattr(first_content, "text"):
                        text = first_content.text
                    else:
                        text = str(first_content)

                    print("Content preview (first 300 chars):")
                    print("-" * 40)
                    suffix = "..." if len(text) > 300 else ""
                    print(text[:300] + suffix)
                    print("-" * 40)

            # ========================================
            # ACT: Test a tool (to confirm tools still work)
            # ========================================
            print("\n--- ACT: Testing list_files tool ---")
            list_result = await client.call_tool("list_files", {"path": "."})
            print("Result:")
            print(get_result_text(list_result))

    print("\n" + "=" * 50)
    print("ALL TESTS PASSED!")
    print("=" * 50)


if __name__ == "__main__":
    try:
        asyncio.run(test_resources())
    except Exception as e:
        print(f"Test failed: {e}", file=sys.stderr)
        sys.exit(1)
