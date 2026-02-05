"""
Agent-Heavy Expense Server

In this approach, the tool is minimal - just a database insert.
The agent must:
- Know all business rules
- Determine categories
- Check limits and thresholds
- Orchestrate the workflow

Result: High token cost, potential for errors, but maximum flexibility
"""

import json
import sys
from typing import Optional

from pydantic import Field
from mcp.server.fastmcp import FastMCP

from database import database, storage

# Create the MCP server
mcp = FastMCP("expense-agent-heavy")


def tool_response(data: dict) -> str:
    """Format response as JSON string."""
    return json.dumps(data, indent=2)


# Agent-Heavy: Tool is just storage, no validation or business logic
@mcp.tool()
async def submit_expense(
    amount: float = Field(description="Expense amount in dollars"),
    category: str = Field(description="Expense category (meals, travel, supplies, etc)"),
    description: str = Field(description="What the expense was for"),
    receipt_url: Optional[str] = Field(default=None, description="URL to receipt image"),
    approval_id: Optional[str] = Field(default=None, description="Manager approval ID if required"),
) -> str:
    """Submit an expense to the system. Agent must handle all validation and categorization."""
    # Minimal validation - just store what we're given
    if amount <= 0:
        raise ValueError("Amount must be positive")

    # Store the expense
    expense = await database.create_expense(
        amount=amount,
        category=category,
        description=description,
        receipt_url=receipt_url,
        approval_id=approval_id,
        status="submitted",
    )

    return tool_response({
        "success": True,
        "expense_id": expense.id,
        "expense_number": expense.number,
        "message": f"Expense {expense.number} submitted",
    })


# Agent needs helper tools to gather business rules
@mcp.tool()
async def get_category_rules() -> str:
    """Get rules for all expense categories including limits and thresholds."""
    rules = database.get_all_category_rules()

    categories = [
        {
            "name": name,
            "max_amount": rule.max_amount,
            "receipt_required_over": rule.receipt_required_over,
            "approval_required_over": rule.approval_required_over,
        }
        for name, rule in rules.items()
    ]

    return tool_response({
        "categories": categories,
        "notes": [
            "Meals with clients should use 'client_entertainment' category",
            "Team events should use 'team_meals' category",
            "Always check receipt and approval requirements before submitting",
        ],
    })


@mcp.tool()
async def upload_receipt(
    file_data: str = Field(description="Base64 encoded file data"),
    file_type: str = Field(description="File mime type (image/jpeg, image/png, application/pdf)"),
) -> str:
    """Upload a receipt image for an expense."""
    # Simulate receipt upload
    receipt = await storage.upload_receipt(file_data, file_type)

    return tool_response({
        "success": True,
        "receipt_url": receipt["url"],
        "receipt_id": receipt["id"],
    })


@mcp.tool()
async def request_approval(
    amount: float = Field(description="Expense amount"),
    category: str = Field(description="Expense category"),
    description: str = Field(description="Expense description"),
    receipt_url: Optional[str] = Field(default=None, description="Receipt URL if available"),
) -> str:
    """Request manager approval for an expense."""
    approval = await database.create_approval(
        amount=amount,
        category=category,
        description=description,
    )

    return tool_response({
        "success": True,
        "approval_id": approval.id,
        "approval_status": approval.status,
        "approver": approval.approver_name,
        "message": f"Approval request sent to {approval.approver_name}",
    })


# Start the server
if __name__ == "__main__":
    print("Agent-Heavy Expense Server running on stdio", file=sys.stderr)
    mcp.run()
