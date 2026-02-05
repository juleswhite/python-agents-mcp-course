"""
MCP Tool Server - Tutorial 01

This server exposes two tools:
- list_files: List contents of a directory
- read_file: Read contents of a file

Run with: python server.py
"""

import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP


# Initialize the MCP server
mcp = FastMCP("file-server")


# Tool 1: List directory contents
@mcp.tool()
def list_files(path: str) -> str:
    """
    List files and directories in a given path.

    Args:
        path: Directory path to list (use '.' for current directory)

    Returns:
        A formatted list of files and directories
    """
    try:
        absolute_path = Path(path).resolve()
        entries = list(absolute_path.iterdir())

        lines = []
        for entry in sorted(entries, key=lambda e: (not e.is_dir(), e.name.lower())):
            icon = "\U0001F4C1" if entry.is_dir() else "\U0001F4C4"  # folder or file emoji
            lines.append(f"{icon} {entry.name}")

        return "\n".join(lines) if lines else "(empty directory)"
    except Exception as e:
        return f"Error: {str(e)}"


# Tool 2: Read file contents
@mcp.tool()
def read_file(path: str) -> str:
    """
    Read the contents of a text file.

    Args:
        path: Path to the file to read

    Returns:
        The contents of the file
    """
    try:
        absolute_path = Path(path).resolve()
        content = absolute_path.read_text(encoding="utf-8")
        return content
    except Exception as e:
        return f'Error: Could not read file "{path}". {str(e)}'


# Start the server
if __name__ == "__main__":
    import sys
    print("File server running on stdio", file=sys.stderr)
    mcp.run()
