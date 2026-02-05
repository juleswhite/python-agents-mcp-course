"""
Tool-Heavy Expense Server

In this approach, all business logic lives in the tool.
The agent must:
- Extract facts from user input
- Map to expected enums/types
- Call the tool
- Follow the tool's instructions

Result: Low token cost, high consistency, but requires structured input
"""

import json
import sys
from typing import Optional, Literal

from pydantic import Field
from mcp.server.fastmcp import FastMCP

from database import database, storage

# Create the MCP server
mcp = FastMCP("expense-tool-heavy")


def tool_response(data: dict) -> str:
    """Format response as JSON string."""
    return json.dumps(data, indent=2)


# Tool-Heavy: All business logic in the tool
@mcp.tool()
async def submit_expense(
    amount: float = Field(description="Expense amount in dollars"),
    expense_type: Literal["meal", "travel", "supplies", "software"] = Field(
        description="General type of expense"
    ),
    description: str = Field(description="Brief description of the expense"),
    has_client_attendees: Optional[bool] = Field(
        default=None, description="Was a client present at this expense event?"
    ),
    receipt_url: Optional[str] = Field(
        default=None, description="URL to receipt if already uploaded"
    ),
    approval_id: Optional[str] = Field(
        default=None, description="Manager approval ID if already obtained"
    ),
) -> str:
    """Submit an expense. Tool handles all validation, categorization, and workflow orchestration."""
    # TOOL DETERMINES CATEGORY (not agent)
    if expense_type == "meal" and has_client_attendees:
        category = "client_entertainment"
    elif expense_type == "meal":
        category = "meals"
    else:
        category = expense_type

    # TOOL KNOWS ALL THE RULES
    rules = database.get_category_rules(category)

    # TOOL VALIDATES AMOUNT
    if amount <= 0:
        return tool_response({
            "status": "failed",
            "message": "Amount must be greater than zero",
            "error": "invalid_amount",
        })

    if amount > rules.max_amount:
        return tool_response({
            "status": "failed",
            "message": f"{category} expenses cannot exceed ${rules.max_amount}",
            "error": "amount_too_high",
            "max_allowed": rules.max_amount,
            "current_amount": amount,
            "hint": "Amount exceeds category maximum. User may need to split expense or choose different category.",
        })

    # TOOL CHECKS RECEIPT REQUIREMENT
    if amount > rules.receipt_required_over and not receipt_url:
        return tool_response({
            "status": "needs_receipt",
            "message": f"{category} expenses over ${rules.receipt_required_over} require a receipt",
            "category": category,
            "amount": amount,
            "receipt_threshold": rules.receipt_required_over,
            "next_action": "upload_receipt",
            "next_action_params": {
                "expense_amount": amount,
                "expense_category": category,
                "supported_formats": ["image/jpeg", "image/png", "application/pdf"],
                "max_size_mb": 10,
            },
            "hint": "Ask user to provide receipt photo. After upload, retry submit_expense with receipt_url.",
            "tell_user": "I'll need a photo or scan of the receipt to process this expense.",
        })

    # TOOL CHECKS APPROVAL REQUIREMENT
    if amount > rules.approval_required_over and not approval_id:
        return tool_response({
            "status": "needs_approval",
            "message": f"{category} expenses over ${rules.approval_required_over} require manager approval",
            "category": category,
            "amount": amount,
            "approval_threshold": rules.approval_required_over,
            "next_action": "request_approval",
            "next_action_params": {
                "amount": amount,
                "category": category,
                "description": description,
                "receipt_url": receipt_url,
            },
            "hint": "Request approval from manager. After approval, retry submit_expense with approval_id.",
            "tell_user": "This expense needs manager approval. I'll send the request now, which typically takes 1-2 business days.",
        })

    # TOOL CREATES THE EXPENSE
    expense = await database.create_expense(
        amount=amount,
        category=category,
        description=description,
        receipt_url=receipt_url,
        approval_id=approval_id,
        status="approved",
    )

    return tool_response({
        "status": "success",
        "expense_id": expense.id,
        "expense_number": expense.number,
        "category": category,
        "amount": amount,
        "message": f"Expense {expense.number} submitted successfully",
        "tell_user": f"Your {category} expense for ${amount:.2f} has been submitted and approved.",
    })


@mcp.tool()
async def upload_receipt(
    file_data: str = Field(description="Base64 encoded file data"),
    file_type: str = Field(description="File mime type (image/jpeg, image/png, application/pdf)"),
    expense_amount: Optional[float] = Field(
        default=None, description="Amount of the expense this receipt is for"
    ),
    expense_category: Optional[str] = Field(
        default=None, description="Category of the expense"
    ),
) -> str:
    """Upload a receipt image for an expense."""
    receipt = await storage.upload_receipt(file_data, file_type)

    return tool_response({
        "status": "success",
        "receipt_url": receipt["url"],
        "receipt_id": receipt["id"],
        "message": "Receipt uploaded successfully",
        "next_action": "submit_expense",
        "hint": "Now retry submit_expense with this receipt_url",
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
        "status": "success",
        "approval_id": approval.id,
        "approval_status": approval.status,
        "approver": approval.approver_name,
        "message": f"Approval request sent to {approval.approver_name}",
        "next_action": "wait",
        "hint": "Tell user the approval request has been sent. They should check back in 1-2 business days.",
        "tell_user": f"I've sent the approval request to {approval.approver_name}. This typically takes 1-2 business days.",
    })


# Start the server
if __name__ == "__main__":
    print("Tool-Heavy Expense Server running on stdio", file=sys.stderr)
    mcp.run()
