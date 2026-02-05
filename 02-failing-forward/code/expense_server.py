"""
Failing Forward Expense Server

Demonstrates all four Failing Forward patterns:
1. Errors as Curriculum - Teaching errors that guide recovery
2. Error Chains - Multi-step recovery processes
3. Pre-filled Parameters - Handing agents everything they need
4. Alternative Actions - Multiple paths to success

Run with: python expense_server.py
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

from mcp.server.fastmcp import FastMCP

# Create the MCP server
server = FastMCP("expense-server")


# ============================================================================
# Mock Database
# ============================================================================


@dataclass
class Expense:
    id: str
    amount: float
    category: str
    description: str
    date: str
    status: str
    created_at: datetime
    receipt_url: str | None = None


@dataclass
class Receipt:
    id: str
    url: str
    expense_amount: float
    uploaded_at: datetime


@dataclass
class Approval:
    id: str
    type: str
    status: Literal["pending", "approved", "denied"]
    approver: str
    created_at: datetime
    expense_id: str | None = None


class MockDatabase:
    def __init__(self) -> None:
        self.expenses: dict[str, Expense] = {}
        self.receipts: dict[str, Receipt] = {}
        self.approvals: dict[str, Approval] = {}
        self._expense_counter = 1
        self._receipt_counter = 1
        self._approval_counter = 1

    async def create_expense(
        self,
        amount: float,
        category: str,
        description: str,
        date: str,
        receipt_url: str | None = None,
    ) -> Expense:
        expense_id = f"exp_{self._expense_counter}"
        self._expense_counter += 1
        expense = Expense(
            id=expense_id,
            amount=amount,
            category=category,
            description=description,
            date=date,
            receipt_url=receipt_url,
            status="pending_approval",
            created_at=datetime.now(),
        )
        self.expenses[expense_id] = expense
        return expense

    async def create_receipt(self, expense_amount: float) -> Receipt:
        receipt_id = f"rcpt_{self._receipt_counter}"
        self._receipt_counter += 1
        receipt = Receipt(
            id=receipt_id,
            url=f"https://storage.example.com/receipts/{receipt_id}.jpg",
            expense_amount=expense_amount,
            uploaded_at=datetime.now(),
        )
        self.receipts[receipt_id] = receipt
        return receipt

    async def create_approval(
        self, approval_type: str, expense_id: str | None = None
    ) -> Approval:
        approval_id = f"apr_{self._approval_counter}"
        self._approval_counter += 1
        approver = (
            "finance-manager@company.com"
            if approval_type == "late_expense"
            else "manager@company.com"
        )
        approval = Approval(
            id=approval_id,
            expense_id=expense_id,
            type=approval_type,
            status="pending",
            approver=approver,
            created_at=datetime.now(),
        )
        self.approvals[approval_id] = approval
        return approval

    async def get_approval(self, approval_id: str) -> Approval | None:
        return self.approvals.get(approval_id)


database = MockDatabase()


# ============================================================================
# Structured Response Helpers
# ============================================================================


@dataclass
class ToolResult:
    status: Literal["success", "failed", "needs_action", "needs_clarification"]
    message: str
    error: str | None = None
    next_action: str | None = None
    next_action_params: dict[str, Any] | None = None
    alternative_actions: list[dict[str, Any]] | None = None
    hint: str | None = None
    tell_user: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "status": self.status,
            "message": self.message,
        }
        if self.error:
            result["error"] = self.error
        if self.next_action:
            result["next_action"] = self.next_action
        if self.next_action_params:
            result["next_action_params"] = self.next_action_params
        if self.alternative_actions:
            result["alternative_actions"] = self.alternative_actions
        if self.hint:
            result["hint"] = self.hint
        if self.tell_user:
            result["tell_user"] = self.tell_user
        # Add any extra fields
        result.update(self.extra)
        return result


def tool_response(result: ToolResult) -> str:
    """Convert a ToolResult to a JSON string response."""
    return json.dumps(result.to_dict(), indent=2)


# ============================================================================
# Constants
# ============================================================================

VALID_CATEGORIES = ["meals", "travel", "supplies", "software", "equipment"]
RECEIPT_THRESHOLD = 25
APPROVAL_THRESHOLD = 100
LATE_EXPENSE_DAYS = 90


# ============================================================================
# Tool 1: Submit Expense (Main tool demonstrating all patterns)
# ============================================================================


@server.tool()
async def submit_expense(
    amount: float,
    category: str,
    description: str,
    date: str,
    receipt_url: str | None = None,
    approval_id: str | None = None,
) -> str:
    """
    Submit an expense for reimbursement.

    This tool demonstrates the Failing Forward pattern - errors guide recovery.

    IMPORTANT: This tool will return structured errors with next_action when:
    - Receipt is required but not provided (expenses over $25)
    - Category is invalid
    - Date is in the future
    - Expense is too old (over 90 days)
    - Amount exceeds approval threshold ($100+)

    Always check the status field in the response and follow the next_action if provided.

    Args:
        amount: Expense amount in USD
        category: One of: meals, travel, supplies, software, equipment
        description: Brief description of the expense
        date: Date of expense in YYYY-MM-DD format
        receipt_url: URL to receipt image (required for expenses over $25)
        approval_id: Approval ID for expenses over $100 or late expenses
    """
    # ========================================================================
    # Validation 1: Amount must be positive
    # ========================================================================
    if amount <= 0:
        return tool_response(
            ToolResult(
                status="failed",
                error="invalid_amount",
                message="Expense amount must be greater than zero",
                next_action="resubmit",
                hint="Check that the amount is positive. The user may have entered it incorrectly.",
                tell_user="The expense amount must be greater than zero. Could you confirm the amount?",
            )
        )

    # ========================================================================
    # Validation 2: Date cannot be in the future
    # ========================================================================
    expense_date = datetime.strptime(date, "%Y-%m-%d")
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    if expense_date > today:
        return tool_response(
            ToolResult(
                status="failed",
                error="future_date",
                message=f"Expense date {date} is in the future. Expenses must be dated today or earlier.",
                next_action="resubmit",
                next_action_params={
                    "suggested_date": today.strftime("%Y-%m-%d"),
                },
                hint="Ask the user to confirm the correct date. They may have made a typo.",
                tell_user="The expense date appears to be in the future. Could you confirm the correct date?",
            )
        )

    # ========================================================================
    # Validation 3: Check if expense is too old (needs special approval)
    # ========================================================================
    days_since_expense = (today - expense_date).days

    if days_since_expense > LATE_EXPENSE_DAYS and not approval_id:
        return tool_response(
            ToolResult(
                status="needs_action",
                error="late_expense",
                message=f"This expense is {days_since_expense} days old, which exceeds the {LATE_EXPENSE_DAYS}-day limit.",
                next_action="request_late_expense_approval",
                next_action_params={
                    "expense_date": date,
                    "days_late": days_since_expense - LATE_EXPENSE_DAYS,
                    "amount": amount,
                    "category": category,
                    "description": description,
                    "reason_required": True,
                },
                alternative_actions=[
                    {
                        "action": "request_late_expense_approval",
                        "description": "Request special approval for the late expense",
                        "when_to_use": "When the expense is legitimate but was submitted late",
                        "params": {
                            "expense_date": date,
                            "days_late": days_since_expense - LATE_EXPENSE_DAYS,
                        },
                    },
                    {
                        "action": "cancel",
                        "description": "Cancel the expense submission",
                        "when_to_use": "When the user decides not to submit the old expense",
                    },
                ],
                hint=f"This expense is {days_since_expense - LATE_EXPENSE_DAYS} days past the submission deadline. Ask the user why it was submitted late and whether they want to request special approval.",
                tell_user=f"This expense is over {LATE_EXPENSE_DAYS} days old and requires special approval. Would you like me to request approval from finance? I'll need a brief explanation for why it's being submitted late.",
            )
        )

    # ========================================================================
    # Validation 4: Category must be valid
    # ========================================================================
    if category.lower() not in VALID_CATEGORIES:
        # PATTERN: Pre-filled parameters - suggest the best match
        suggestions = [
            c
            for c in VALID_CATEGORIES
            if c.startswith(category.lower()[:3])
            or category.lower().startswith(c[:3])
        ]

        return tool_response(
            ToolResult(
                status="failed",
                error="invalid_category",
                message=f"Category '{category}' is not recognized.",
                next_action="resubmit",
                next_action_params={
                    "amount": amount,
                    "description": description,
                    "date": date,
                    "receipt_url": receipt_url,
                    "category": suggestions[0] if suggestions else None,
                },
                hint=f"The user said '{category}'. Map this to one of: {', '.join(VALID_CATEGORIES)}. " + (f"'{suggestions[0]}' seems like the best match." if suggestions else "Ask user to clarify if unclear."),
                tell_user=f"I don't recognize the category '{category}'. Valid options are: {', '.join(VALID_CATEGORIES)}. Which one should I use?",
                extra={"valid_options": VALID_CATEGORIES, "suggested_category": suggestions[0] if suggestions else None},
            )
        )

    # Normalize category to lowercase
    normalized_category = category.lower()

    # ========================================================================
    # Validation 5: Receipt required for expenses over $25
    # ========================================================================
    if amount > RECEIPT_THRESHOLD and not receipt_url:
        return tool_response(
            ToolResult(
                status="needs_action",
                error="receipt_required",
                message=f"Expenses over ${RECEIPT_THRESHOLD} require a receipt. This expense is ${amount:.2f}.",
                next_action="upload_receipt",
                next_action_params={
                    "expense_amount": amount,
                    "expense_category": normalized_category,
                    "expense_description": description,
                    "expense_date": date,
                    "supported_formats": ["image/jpeg", "image/png", "application/pdf"],
                    "max_size_mb": 10,
                },
                hint="Ask the user to provide a photo or scan of the receipt. Once uploaded, retry submit_expense with the receipt_url.",
                tell_user=f"Since this expense is over ${RECEIPT_THRESHOLD}, I'll need a photo or scan of the receipt. Could you upload it?",
            )
        )

    # ========================================================================
    # Validation 6: Large expenses need manager approval
    # ========================================================================
    if amount > APPROVAL_THRESHOLD and not approval_id:
        return tool_response(
            ToolResult(
                status="needs_action",
                error="approval_required",
                message=f"Expenses over ${APPROVAL_THRESHOLD} require manager approval. This expense is ${amount:.2f}.",
                next_action="request_expense_approval",
                next_action_params={
                    "amount": amount,
                    "category": normalized_category,
                    "description": description,
                    "date": date,
                    "receipt_url": receipt_url,
                },
                hint="Large expenses need approval before submission. Request approval and then retry with the approval_id.",
                tell_user=f"This expense of ${amount:.2f} needs manager approval. I'll send the request now.",
            )
        )

    # ========================================================================
    # Success! Create the expense
    # ========================================================================
    expense = await database.create_expense(
        amount=amount,
        category=normalized_category,
        description=description,
        date=date,
        receipt_url=receipt_url,
    )

    return tool_response(
        ToolResult(
            status="success",
            message=f"Expense submitted for ${amount:.2f} in {normalized_category}",
            tell_user=f"Your expense for ${amount:.2f} has been submitted successfully and is pending approval.",
            extra={
                "expense_id": expense.id,
                "current_status": expense.status,
            },
        )
    )


# ============================================================================
# Tool 2: Upload Receipt
# ============================================================================


@server.tool()
async def upload_receipt(
    expense_amount: float,
    file_data: str | None = None,
    file_type: str | None = None,
) -> str:
    """
    Upload a receipt image for an expense.

    Returns a receipt_url that can be used with submit_expense.
    This is typically called after submit_expense returns a receipt_required error.

    Args:
        expense_amount: The amount of the expense this receipt is for
        file_data: Base64 encoded file data (simulated in this example)
        file_type: File mime type: image/jpeg, image/png, or application/pdf
    """
    # Validate file type if provided
    valid_types = ["image/jpeg", "image/png", "application/pdf"]
    if file_type and file_type not in valid_types:
        return tool_response(
            ToolResult(
                status="failed",
                error="invalid_file_type",
                message=f"File type '{file_type}' is not supported.",
                next_action="upload_receipt",
                hint="Ask the user to provide a JPEG, PNG, or PDF file.",
                tell_user="The receipt must be a JPEG, PNG, or PDF file. Could you provide it in one of those formats?",
                extra={"valid_types": valid_types},
            )
        )

    # Create the receipt
    receipt = await database.create_receipt(expense_amount)

    return tool_response(
        ToolResult(
            status="success",
            message="Receipt uploaded successfully",
            next_action="submit_expense",
            next_action_params={
                "receipt_url": receipt.url,
            },
            hint="Now retry submit_expense with this receipt_url",
            tell_user="Receipt uploaded! I'll now submit the expense.",
            extra={
                "receipt_id": receipt.id,
                "receipt_url": receipt.url,
            },
        )
    )


# ============================================================================
# Tool 3: Request Expense Approval (for large expenses)
# ============================================================================


@server.tool()
async def request_expense_approval(
    amount: float,
    category: str,
    description: str,
    date: str,
    receipt_url: str | None = None,
) -> str:
    """
    Request manager approval for a large expense (over $100).

    Returns an approval_id that can be used with submit_expense.
    In a real system, this would send a notification to the manager.

    Args:
        amount: Expense amount
        category: Expense category
        description: Expense description
        date: Expense date
        receipt_url: Receipt URL if already uploaded
    """
    approval = await database.create_approval(approval_type="large_expense")

    # In a real system, this would be async and require waiting
    # For demo purposes, we'll auto-approve
    return tool_response(
        ToolResult(
            status="success",
            message=f"Approval request sent to {approval.approver}",
            next_action="submit_expense",
            next_action_params={
                "amount": amount,
                "category": category,
                "description": description,
                "date": date,
                "receipt_url": receipt_url,
                "approval_id": approval.id,
            },
            hint="Approval granted. Now retry submit_expense with the approval_id.",
            tell_user=f"Your expense has been approved by {approval.approver}. Submitting now...",
            extra={
                "approval_id": approval.id,
                "approval_status": "approved",  # Simulated instant approval for demo
                "approver": approval.approver,
            },
        )
    )


# ============================================================================
# Tool 4: Request Late Expense Approval (for old expenses)
# ============================================================================


@server.tool()
async def request_late_expense_approval(
    expense_date: str,
    days_late: int,
    amount: float,
    category: str,
    description: str,
    late_reason: str,
) -> str:
    """
    Request special approval for an expense that's over 90 days old.

    Requires a reason for why the expense is being submitted late.
    Returns an approval_id that can be used with submit_expense.

    Args:
        expense_date: Original date of the expense
        days_late: Number of days past the submission deadline
        amount: Expense amount
        category: Expense category
        description: Expense description
        late_reason: Explanation for why the expense is being submitted late
    """
    # Validate that a reason was provided
    if not late_reason or len(late_reason.strip()) < 10:
        return tool_response(
            ToolResult(
                status="failed",
                error="reason_required",
                message="A detailed explanation is required for late expense submissions.",
                next_action="request_late_expense_approval",
                next_action_params={
                    "expense_date": expense_date,
                    "days_late": days_late,
                    "amount": amount,
                    "category": category,
                    "description": description,
                },
                hint="Ask the user to provide a reason for the late submission. It should be at least a sentence explaining the circumstances.",
                tell_user="I need a brief explanation for why this expense is being submitted late. What happened?",
            )
        )

    approval = await database.create_approval(approval_type="late_expense")

    return tool_response(
        ToolResult(
            status="success",
            message=f"Late expense approval granted by {approval.approver}",
            next_action="submit_expense",
            next_action_params={
                "amount": amount,
                "category": category,
                "description": description,
                "date": expense_date,
                "approval_id": approval.id,
            },
            hint="Late expense approved. Now retry submit_expense with the approval_id.",
            tell_user="The late expense has been approved. Submitting now...",
            extra={
                "approval_id": approval.id,
                "approval_status": "approved",  # Simulated for demo
                "approver": approval.approver,
                "reason_recorded": late_reason,
            },
        )
    )


# ============================================================================
# Tool 5: Get Category Suggestions (helper tool)
# ============================================================================


@server.tool()
async def get_expense_categories() -> str:
    """Get the list of valid expense categories with descriptions."""
    categories = [
        {
            "name": "meals",
            "description": "Food and beverages for business purposes",
            "examples": ["lunch meetings", "team dinners", "client meals"],
        },
        {
            "name": "travel",
            "description": "Transportation and lodging",
            "examples": ["flights", "hotels", "rental cars", "uber/taxi"],
        },
        {
            "name": "supplies",
            "description": "Office and work supplies",
            "examples": ["notebooks", "pens", "desk accessories"],
        },
        {
            "name": "software",
            "description": "Software subscriptions and licenses",
            "examples": ["SaaS tools", "annual licenses", "cloud services"],
        },
        {
            "name": "equipment",
            "description": "Hardware and equipment",
            "examples": ["monitors", "keyboards", "headsets"],
        },
    ]

    return tool_response(
        ToolResult(
            status="success",
            message="Here are the valid expense categories and their rules",
            extra={
                "categories": categories,
                "receipt_threshold": RECEIPT_THRESHOLD,
                "approval_threshold": APPROVAL_THRESHOLD,
                "late_expense_days": LATE_EXPENSE_DAYS,
            },
        )
    )


# ============================================================================
# Start the server
# ============================================================================


def main() -> None:
    """Run the expense server."""
    import sys
    print("Failing Forward Expense Server running on stdio", file=sys.stderr)
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
