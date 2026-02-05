"""
MCP Tool Server with Resources - Tutorial 03

This server extends the basic file server with Resources,
demonstrating the Active Learning pattern. Resources provide
documentation that agents can read before using tools.

Run with: python server_with_resources.py
"""

import json
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP


# Initialize the MCP server
mcp = FastMCP("file-server-with-resources")


# ============================================
# TOOLS (same as before)
# ============================================

@mcp.tool()
def list_files(path: str) -> str:
    """
    List files and directories in a given path.

    TIP: Read resource://files/guide for best practices on exploring directories.

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


@mcp.tool()
def read_file(path: str) -> str:
    """
    Read the contents of a text file.

    TIP: Read resource://files/guide for tips on which files to examine first.

    Args:
        path: Path to the file to read

    Returns:
        The contents of the file (truncated if very long)
    """
    try:
        absolute_path = Path(path).resolve()
        content = absolute_path.read_text(encoding="utf-8")

        # Truncate very long files
        max_length = 10000
        if len(content) > max_length:
            content = content[:max_length] + "\n\n... (truncated)"

        return content
    except Exception as e:
        return f'Error: Could not read file "{path}". {str(e)}'


# ============================================
# RESOURCES (new in Tutorial 03)
# ============================================

# Resource 1: Usage guide for the file tools
@mcp.resource("resource://files/guide")
def get_guide() -> str:
    """How to effectively use the file exploration tools."""
    return """# File Exploration Guide

## Available Tools

### list_files
Lists contents of a directory. Use this to explore what's available.
- Use "." for current directory
- Returns icons: \U0001F4C1 for directories, \U0001F4C4 for files
- Supports relative and absolute paths

### read_file
Reads a text file. Use this to examine file contents.
- Works with any text file (.ts, .js, .json, .md, .txt, etc.)
- Large files are truncated to 10,000 characters
- Returns helpful error messages if file doesn't exist

## Recommended Workflow

When exploring a new codebase or directory:

1. **Start with an overview**: Use list_files(".") to see what's in the current directory
2. **Look for documentation**: Check for README.md, CONTRIBUTING.md, or docs/ folder
3. **Read documentation first**: These files explain the project structure and purpose
4. **Check configuration**: Look at package.json, tsconfig.json for project settings
5. **Explore source code**: Based on what you learned, dive into relevant files

## Common Patterns

### Understanding a Node.js project
1. Read package.json for dependencies and scripts
2. Read README.md for project overview
3. Check tsconfig.json or jsconfig.json for configuration
4. Look for src/ or lib/ for main source code

### Finding specific functionality
1. List directory structure to understand organization
2. Look for descriptive file/folder names
3. Read index.ts or main.ts as entry points
4. Follow imports to find related code

## Error Handling

If you encounter an error:
- "ENOENT" means the file or directory doesn't exist - check the path
- "EACCES" means permission denied - the file may be protected
- "EISDIR" means you tried to read a directory as a file - use list_files instead

## Tips for Effective Exploration

- Start broad, then narrow down based on what you find
- Documentation files often explain more than code comments
- Package.json "main" or "exports" fields point to entry points
- Test files often demonstrate how code is meant to be used
"""


# Resource 2: Common file patterns and what they mean
@mcp.resource("resource://files/patterns")
def get_patterns() -> str:
    """Common file patterns in projects and what they indicate."""
    patterns = {
        "patterns": [
            {
                "pattern": "package.json",
                "meaning": "Node.js project configuration",
                "read_priority": "high",
                "contains": "dependencies, scripts, project metadata"
            },
            {
                "pattern": "tsconfig.json",
                "meaning": "TypeScript configuration",
                "read_priority": "medium",
                "contains": "compiler options, include/exclude paths"
            },
            {
                "pattern": "README.md",
                "meaning": "Project documentation",
                "read_priority": "high",
                "contains": "project overview, setup instructions, usage"
            },
            {
                "pattern": "*.test.ts or *.spec.ts",
                "meaning": "Test files",
                "read_priority": "low",
                "contains": "tests showing how code should behave"
            },
            {
                "pattern": "index.ts",
                "meaning": "Module entry point",
                "read_priority": "high",
                "contains": "main exports, often re-exports from other files"
            },
            {
                "pattern": ".env or .env.example",
                "meaning": "Environment configuration",
                "read_priority": "medium",
                "contains": "environment variables (don't expose .env contents)"
            },
            {
                "pattern": "src/ or lib/",
                "meaning": "Source code directory",
                "read_priority": "high",
                "contains": "main application code"
            },
            {
                "pattern": "dist/ or build/",
                "meaning": "Compiled output",
                "read_priority": "low",
                "contains": "generated files, usually ignored"
            }
        ]
    }
    return json.dumps(patterns, indent=2)


# ============================================
# START SERVER
# ============================================

if __name__ == "__main__":
    print("File server with resources running on stdio", file=sys.stderr)
    mcp.run()
