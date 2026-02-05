"""
Test script to verify the MCP server works correctly.
This tests the PERCEIVE and ACT phases without needing an LLM.

Run with: python test_server.py
"""

import asyncio
import sys
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


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


async def test_server() -> None:
    """Test the MCP server."""
    print("=" * 50)
    print("MCP SERVER TEST")
    print("=" * 50)
    print("\nConnecting to server...")

    server_params = StdioServerParameters(
        command="python",
        args=["server.py"],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as client:
            await client.initialize()
            print("Connected!\n")

            # PERCEIVE: Discover tools
            print("--- PERCEIVE: Discovering tools ---")
            tools_result = await client.list_tools()
            tools = tools_result.tools
            print(f"Found {len(tools)} tools:")
            for tool in tools:
                print(f"  - {tool.name}: {tool.description}")

            # ACT: Test list_files
            print("\n--- ACT: Testing list_files ---")
            list_result = await client.call_tool("list_files", {"path": "."})
            print("Result:")
            print(get_result_text(list_result))

            # ACT: Test read_file
            print("\n--- ACT: Testing read_file ---")
            read_result = await client.call_tool("read_file", {"path": "requirements.txt"})
            read_text = get_result_text(read_result)
            print("Result (first 200 chars):")
            suffix = "..." if len(read_text) > 200 else ""
            print(read_text[:200] + suffix)

            # ACT: Test error handling
            print("\n--- ACT: Testing error handling ---")
            error_result = await client.call_tool("read_file", {"path": "nonexistent-file.txt"})
            print("Result:")
            print(get_result_text(error_result))
            print(f"isError: {getattr(error_result, 'isError', False)}")

    print("\n" + "=" * 50)
    print("ALL TESTS PASSED!")
    print("=" * 50)


if __name__ == "__main__":
    try:
        asyncio.run(test_server())
    except Exception as e:
        print(f"Test failed: {e}", file=sys.stderr)
        sys.exit(1)
