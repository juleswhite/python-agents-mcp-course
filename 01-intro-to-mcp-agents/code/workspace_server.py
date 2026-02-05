"""
Context-Aware Workspace Server - Tutorial 05

This server extends the basic file server with context discovery,
demonstrating hierarchical context loading from .context.md files.

Run with: python workspace_server.py
"""

import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP


# Initialize the MCP server
mcp = FastMCP("workspace-server")


# ============================================
# CONTEXT DISCOVERY HELPERS
# ============================================

async def get_context_hierarchy(target_path: str) -> list[str]:
    """
    Get context files from target directory up to workspace root.
    Returns an array of context strings, from most general to most specific.
    """
    contexts: list[str] = []
    absolute_path = Path(target_path).resolve()
    workspace_root = Path("workspace").resolve()

    # Make sure we're within the workspace
    try:
        absolute_path.relative_to(workspace_root)
    except ValueError:
        return []

    current = absolute_path

    # Walk up to workspace root, collecting context files
    while True:
        try:
            current.relative_to(workspace_root)
        except ValueError:
            break

        context_file = current / ".context.md"
        try:
            content = context_file.read_text(encoding="utf-8")
            # Add parent contexts first (insert at beginning), so local context comes last
            try:
                relative_path = str(current.relative_to(workspace_root))
            except ValueError:
                relative_path = "(workspace root)"
            if not relative_path or relative_path == ".":
                relative_path = "(workspace root)"
            contexts.insert(0, f"## Context from: {relative_path}\n\n{content}")
        except (FileNotFoundError, IOError):
            # No context file at this level, continue
            pass

        if current == workspace_root:
            break
        current = current.parent

    return contexts


# ============================================
# TOOLS
# ============================================

# Tool 1: List directory contents
@mcp.tool()
def list_files(path: str) -> str:
    """
    List files and directories in a given path within the workspace.

    Args:
        path: Directory path relative to workspace (use '.' for workspace root)

    Returns:
        A formatted list of files and directories
    """
    try:
        workspace_path = (Path("workspace") / path).resolve()
        entries = list(workspace_path.iterdir())

        lines = []
        for entry in sorted(entries, key=lambda e: (not e.is_dir(), e.name.lower())):
            icon = "\U0001F4C1" if entry.is_dir() else "\U0001F4C4"
            lines.append(f"{icon} {entry.name}")

        return "\n".join(lines) if lines else "(empty directory)"
    except Exception as e:
        return f"Error: {str(e)}"


# Tool 2: Read file contents
@mcp.tool()
def read_file(path: str) -> str:
    """
    Read the contents of a file within the workspace.

    Args:
        path: File path relative to workspace

    Returns:
        The contents of the file
    """
    try:
        workspace_path = (Path("workspace") / path).resolve()
        content = workspace_path.read_text(encoding="utf-8")

        # Truncate very long files
        max_length = 10000
        if len(content) > max_length:
            content = content[:max_length] + "\n\n... (truncated)"

        return content
    except Exception as e:
        return f'Error: Could not read file "{path}". {str(e)}'


# Tool 3: Write file contents
@mcp.tool()
def write_file(path: str, content: str) -> str:
    """
    Write content to a file within the workspace.

    IMPORTANT: Before calling this tool, you should first call get_directory_context
    to understand the naming conventions and required content format for the
    target directory.

    Args:
        path: File path relative to workspace
        content: Content to write to the file

    Returns:
        Success message or error
    """
    try:
        workspace_path = (Path("workspace") / path).resolve()

        # Ensure parent directory exists
        workspace_path.parent.mkdir(parents=True, exist_ok=True)

        workspace_path.write_text(content, encoding="utf-8")

        return f"Successfully wrote {len(content)} characters to {path}"
    except Exception as e:
        return f'Error: Could not write file "{path}". {str(e)}'


# Tool 4: Get directory context (THE KEY DISCOVERY TOOL)
@mcp.tool()
async def get_directory_context(path: str) -> str:
    """
    Get the context rules for a directory within the workspace.

    This returns the .context.md file if one exists, plus any inherited context
    from parent directories. Context is returned in order from most general
    (workspace root) to most specific (target directory).

    IMPORTANT: Always call this tool BEFORE creating or modifying files in a
    directory to understand:
    - Naming conventions (how files should be named)
    - Required fields (what content must include)
    - Templates (what format to use)
    - Any special procedures or approval requirements

    Args:
        path: Directory path relative to workspace (use '.' for workspace root)

    Returns:
        Context rules for the directory
    """
    try:
        workspace_path = (Path("workspace") / path).resolve()
        contexts = await get_context_hierarchy(str(workspace_path))

        if not contexts:
            return f"""No context rules found for "{path}" or its parent directories.

You may proceed without specific conventions, but consider using sensible defaults."""

        header = f"""# Context Rules for: {path}

The following context rules apply to this directory. Rules are listed from most general (workspace-wide) to most specific (this directory). When rules conflict, more specific rules take precedence.

---

"""
        return header + "\n\n---\n\n".join(contexts)
    except Exception as e:
        return f'Error getting context for "{path}": {str(e)}'


# ============================================
# START SERVER
# ============================================

if __name__ == "__main__":
    print("Workspace server running on stdio", file=sys.stderr)
    mcp.run()
