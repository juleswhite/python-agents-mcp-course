"""
Hybrid Expense Server

In this approach, we combine the best of both:
- Agent extracts from natural language (flexible input)
- Tool normalizes and validates (deterministic processing)
- Tool enforces business rules (consistent)
- Tool provides context-aware guidance (intelligent)

Result: Low token cost, high flexibility, high consistency
"""

import json
import sys
from typing import Optional, List, Dict, Any, Literal

from pydantic import BaseModel, Field
from mcp.server.fastmcp import FastMCP

from database import database, storage

# Create the MCP server
mcp = FastMCP("expense-hybrid")


def tool_response(data: dict) -> str:
    """Format response as JSON string."""
    return json.dumps(data, indent=2)


# Context model for structured input
class ExpenseContext(BaseModel):
    """Contextual information to help categorize and route the expense."""
    has_client_involved: Optional[bool] = Field(
        default=None, description="Was a client or customer present or involved?"
    )
    is_team_event: Optional[bool] = Field(
        default=None, description="Was this a team event or group activity?"
    )
    is_recurring: Optional[bool] = Field(
        default=None, description="Is this a recurring expense?"
    )
    urgency: Optional[Literal["normal", "urgent"]] = Field(
        default=None, description="How urgently does this need to be processed?"
    )


# HELPER: Smart categorization based on description + context
def determine_category(
    description: str,
    context: Optional[ExpenseContext] = None
) -> str:
    """Determine expense category based on description and context."""
    lower = description.lower()

    # Check for meal-related keywords
    if any(word in lower for word in ["dinner", "lunch", "breakfast", "meal", "restaurant", "food"]):
        if context and context.has_client_involved:
            return "client_entertainment"
        if context and context.is_team_event:
            return "team_meals"
        return "meals"

    # Check for travel keywords
    if any(word in lower for word in ["flight", "hotel", "rental", "uber", "taxi", "airbnb"]):
        return "travel"

    # Check for software keywords
    if any(word in lower for word in ["software", "subscription", "saas", "license"]):
        return "software"

    # Check for supplies keywords
    if any(word in lower for word in ["office", "supplies", "equipment", "furniture"]):
        return "supplies"

    return "unknown"


def suggest_categories(description: str) -> List[Dict[str, Any]]:
    """Suggest possible categories based on description."""
    suggestions: List[Dict[str, Any]] = []
    lower = description.lower()

    if "eat" in lower or "food" in lower:
        suggestions.append({"name": "meals", "confidence": 0.7})
    if "client" in lower or "customer" in lower:
        suggestions.append({"name": "client_entertainment", "confidence": 0.6})
    if "trip" in lower or "travel" in lower:
        suggestions.append({"name": "travel", "confidence": 0.8})
    if "buy" in lower or "purchase" in lower:
        suggestions.append({"name": "supplies", "confidence": 0.5})

    return sorted(suggestions, key=lambda x: x["confidence"], reverse=True)


# Hybrid: Flexible input, smart processing
@mcp.tool()
async def submit_expense(
    amount: float = Field(description="Expense amount in dollars"),
    description: str = Field(description="What was purchased or paid for (in user's own words)"),
    context: Optional[ExpenseContext] = Field(
        default=None,
        description="Contextual information to help categorize and route the expense"
    ),
    receipt_url: Optional[str] = Field(
        default=None, description="URL to receipt if already uploaded"
    ),
    approval_id: Optional[str] = Field(
        default=None, description="Manager approval ID if already obtained"
    ),
) -> str:
    """Submit an expense. Provide natural description and context; tool handles categorization and validation."""
    # TOOL INTELLIGENTLY DETERMINES CATEGORY
    category = determine_category(description, context)

    # If category is ambiguous, ask for clarification
    if category == "unknown":
        suggestions = suggest_categories(description)
        return tool_response({
            "status": "needs_clarification",
            "message": "Could not determine expense category from description",
            "description_provided": description,
            "suggested_categories": suggestions,
            "hint": "Description is ambiguous. Present category options to user or ask for more details about what this expense was for.",
            "tell_user": "I'm not sure how to categorize this expense. Could you tell me more about what it was for?",
        })

    # TOOL USES CONTEXT FOR BETTER DECISIONS
    rules = database.get_category_rules(category)
    is_urgent = context.urgency == "urgent" if context else False

    # Urgent expenses might have different thresholds
    effective_approval_threshold = (
        rules.approval_required_over * 1.5 if is_urgent else rules.approval_required_over
    )

    # Standard validations
    if amount <= 0:
        return tool_response({
            "status": "failed",
            "message": "Amount must be greater than zero",
            "error": "invalid_amount",
            "hint": "Amount is not valid. Ask user to verify the expense amount.",
        })

    if amount > rules.max_amount:
        return tool_response({
            "status": "failed",
            "message": f"{category} expenses cannot exceed ${rules.max_amount}",
            "error": "amount_too_high",
            "max_allowed": rules.max_amount,
            "current_amount": amount,
            "current_category": category,
            "alternative_actions": [
                {
                    "action": "split_expense",
                    "description": "Split this into multiple smaller expenses",
                    "when_to_use": "The expense can be logically divided into separate items",
                },
                {
                    "action": "request_exception",
                    "description": "Request a policy exception for this amount",
                    "when_to_use": "The expense is justified but exceeds normal limits",
                    "params": {
                        "amount": amount,
                        "category": category,
                        "justification": f"Expense of ${amount} exceeds {category} limit of ${rules.max_amount}",
                    },
                },
                {
                    "action": "recategorize",
                    "description": "Consider if this should be in a different category",
                    "when_to_use": "The expense might fit better in another category with higher limits",
                },
            ],
            "hint": "Amount exceeds maximum. Present alternatives to user.",
            "tell_user": f"This {category} expense of ${amount} exceeds our ${rules.max_amount} limit. We have a few options...",
        })

    # TOOL CHECKS RECEIPT (with context-aware messaging)
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
                "expense_description": description,
                "supported_formats": ["image/jpeg", "image/png", "application/pdf"],
                "max_size_mb": 10,
            },
            "hint": (
                "This is urgent. Explain that receipt can be uploaded immediately via phone camera."
                if is_urgent
                else "Ask user to provide receipt photo. After upload, retry submit_expense with receipt_url."
            ),
            "tell_user": (
                "I'll need the receipt right away since this is urgent. You can snap a photo with your phone and upload it."
                if is_urgent
                else "I'll need a photo or scan of the receipt to process this expense."
            ),
        })

    # TOOL CHECKS APPROVAL (with contextual routing)
    if amount > effective_approval_threshold and not approval_id:
        return tool_response({
            "status": "needs_approval",
            "message": f"{category} expenses over ${effective_approval_threshold} require approval",
            "category": category,
            "amount": amount,
            "approval_threshold": effective_approval_threshold,
            "is_urgent": is_urgent,
            "next_action": "request_approval",
            "next_action_params": {
                "amount": amount,
                "category": category,
                "description": description,
                "receipt_url": receipt_url,
                "urgency": context.urgency if context else "normal",
            },
            "hint": (
                "Mark as urgent. Approver will be notified to expedite."
                if is_urgent
                else "Request approval from manager. Standard timeline is 2-3 business days."
            ),
            "tell_user": (
                "This needs approval, but I'll mark it as urgent for faster processing. Your manager will be notified immediately."
                if is_urgent
                else "I'll send this to your manager for approval. This typically takes a couple of days."
            ),
        })

    # TOOL CREATES WITH FULL CONTEXT
    expense = await database.create_expense(
        amount=amount,
        category=category,
        description=description,
        receipt_url=receipt_url,
        approval_id=approval_id,
        status="approved",
        metadata={
            "has_client": context.has_client_involved if context else None,
            "is_team_event": context.is_team_event if context else None,
            "is_recurring": context.is_recurring if context else None,
            "urgency": context.urgency if context else None,
            "original_description": description,
        },
    )

    urgent_message = " Marked as urgent for priority processing." if is_urgent else ""
    return tool_response({
        "status": "success",
        "expense_id": expense.id,
        "expense_number": expense.number,
        "category": category,
        "amount": amount,
        "message": f"Expense {expense.number} submitted successfully",
        "tell_user": f"Your {category} expense for ${amount:.2f} has been submitted.{urgent_message}",
    })


@mcp.tool()
async def upload_receipt(
    file_data: str = Field(description="Base64 encoded file data"),
    file_type: str = Field(description="File mime type"),
    expense_description: Optional[str] = Field(
        default=None, description="Description of the expense"
    ),
) -> str:
    """Upload a receipt image."""
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
    urgency: Optional[Literal["normal", "urgent"]] = Field(default=None, description="Urgency level"),
) -> str:
    """Request manager approval."""
    approval = await database.create_approval(
        amount=amount,
        category=category,
        description=description,
    )

    is_urgent = urgency == "urgent"

    return tool_response({
        "status": "success",
        "approval_id": approval.id,
        "approval_status": approval.status,
        "approver": approval.approver_name,
        "is_urgent": is_urgent,
        "message": f"Approval request sent to {approval.approver_name}",
        "next_action": "wait",
        "hint": (
            "Urgent approval requested. Typical response time is 24 hours."
            if is_urgent
            else "Tell user the approval request has been sent. Standard response time is 1-2 business days."
        ),
        "tell_user": (
            f"I've sent the approval request to {approval.approver_name}. Since this is urgent, they'll typically respond within 24 hours."
            if is_urgent
            else f"I've sent the approval request to {approval.approver_name}. This usually takes 1-2 business days."
        ),
    })


# Start the server
if __name__ == "__main__":
    print("Hybrid Expense Server running on stdio", file=sys.stderr)
    mcp.run()
