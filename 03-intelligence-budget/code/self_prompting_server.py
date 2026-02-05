"""
Self-Prompting Expense Server

This server demonstrates SELF-PROMPTING - where tools make their own LLM calls
in isolated, focused contexts. The key insight: semantic reasoning doesn't have
to happen in the agent's crowded context just because it requires an LLM.

When a tool makes an LLM call:
- The agent (which is an LLM) invokes the tool
- The tool constructs a FOCUSED prompt with only the relevant information
- The LLM responds in this isolated context (no conversation history!)
- The tool returns a result to the agent

This pattern allows:
- Testable classification (same input = same output)
- Use of smaller/cheaper models for specific tasks
- Clean separation of concerns
- Predictable token costs

Run with: python self_prompting_server.py
"""

import json
import os
import re
import sys
from typing import Optional, Dict, Any, Literal

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from openai import OpenAI
from mcp.server.fastmcp import FastMCP

from database import database, storage

# Load environment variables
load_dotenv()

# Initialize OpenAI client for self-prompting calls
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Create the MCP server
mcp = FastMCP("expense-self-prompting")


def tool_response(data: dict) -> str:
    """Format response as JSON string."""
    return json.dumps(data, indent=2)


# ============================================================================
# SELF-PROMPTING: LLM calls INSIDE the tool
# ============================================================================

async def classify_expense(
    description: str,
    amount: float
) -> Dict[str, Any]:
    """
    This is the core self-prompting function. It makes an LLM call with:
    - A FIXED, focused system prompt (same every time)
    - Only the expense description and amount (no conversation history!)
    - Temperature 0 for consistent results

    The agent never sees this reasoning. It just gets the result.
    """
    print(f'[Self-Prompting] Classifying: "{description}" (${amount})', file=sys.stderr)

    response = openai_client.responses.create(
        model="gpt-4o-mini",  # Can use smaller model for focused task!
        input=[
            {
                "role": "user",
                "content": f'Expense description: "{description}"\nAmount: ${amount}',
            }
        ],
        instructions="""You are an expense classifier. Your job is to categorize expenses into exactly one of these categories:

- meals: Regular meals, snacks, coffee (not with clients or at team events)
- client_entertainment: Meals, entertainment, or gifts for clients, customers, or prospects
- team_meals: Team lunches, celebrations, offsites, department meals
- travel: Flights, hotels, rental cars, trains, rideshares, parking
- supplies: Office supplies, equipment, furniture
- software: Software subscriptions, licenses, SaaS tools

Consider context clues carefully:
- Mentions of company names, "clients", "customers", "prospects" -> client_entertainment
- Mentions of "team", "department", "celebration", "offsite" -> team_meals
- Meal expenses without client/team indicators -> meals

Respond with JSON only:
{
  "category": "one of the categories above",
  "confidence": 0.0-1.0,
  "reasoning": "brief explanation of why this category"
}""",
        temperature=0,  # Deterministic for testing
    )

    # Parse the response
    text = response.output_text or ""

    try:
        # Extract JSON from response (handle potential markdown formatting)
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            result = json.loads(json_match.group())
            print(f"[Self-Prompting] Result: {result['category']} ({result['confidence']})", file=sys.stderr)
            return result
    except Exception as e:
        print(f"[Self-Prompting] Parse error: {e}", file=sys.stderr)

    # Fallback if parsing fails
    return {
        "category": "unknown",
        "confidence": 0.3,
        "reasoning": "Could not parse LLM response",
    }


async def classify_expense_with_fallback(
    description: str,
    amount: float,
    context_hints: Optional[Dict[str, bool]] = None
) -> Dict[str, Any]:
    """
    Layered classification: try cheap deterministic methods first,
    fall back to self-prompting only when needed.
    """
    # LAYER 1: Use context hints from the agent if available
    # These are FREE - no LLM call needed
    if context_hints and context_hints.get("mentions_client"):
        has_food = bool(re.search(r'lunch|dinner|breakfast|meal|restaurant|coffee', description, re.IGNORECASE))
        if has_food:
            print("[Classification] Using context hint: client meal", file=sys.stderr)
            return {
                "category": "client_entertainment",
                "confidence": 0.95,
                "source": "deterministic",
            }

    if context_hints and context_hints.get("mentions_team"):
        has_food = bool(re.search(r'lunch|dinner|breakfast|meal|restaurant|coffee', description, re.IGNORECASE))
        if has_food:
            print("[Classification] Using context hint: team meal", file=sys.stderr)
            return {
                "category": "team_meals",
                "confidence": 0.95,
                "source": "deterministic",
            }

    # LAYER 2: Keyword-based classification for OBVIOUS cases
    # These are FREE - no LLM call needed
    lower_desc = description.lower()

    if re.search(r'\b(flight|airline|hotel|airbnb|uber|lyft|taxi|rental car|train)\b', lower_desc):
        print("[Classification] Keyword match: travel", file=sys.stderr)
        return {"category": "travel", "confidence": 0.95, "source": "deterministic"}

    if re.search(r'\b(software|subscription|license|saas|app)\b', lower_desc):
        print("[Classification] Keyword match: software", file=sys.stderr)
        return {"category": "software", "confidence": 0.90, "source": "deterministic"}

    if re.search(r'\b(supplies|equipment|office|furniture|desk|chair)\b', lower_desc):
        print("[Classification] Keyword match: supplies", file=sys.stderr)
        return {"category": "supplies", "confidence": 0.90, "source": "deterministic"}

    # LAYER 3: Self-prompting for AMBIGUOUS cases
    # This is where the LLM call happens - only when needed!
    print("[Classification] Falling back to LLM self-prompting", file=sys.stderr)
    llm_result = await classify_expense(description, amount)

    return {
        "category": llm_result["category"],
        "confidence": llm_result["confidence"],
        "source": "llm",
    }


# ============================================================================
# MCP Tool Definition
# ============================================================================

class ContextHints(BaseModel):
    """Hints from the conversation that help with classification."""
    mentions_client: Optional[bool] = Field(default=None, description="Did user mention a client?")
    mentions_team: Optional[bool] = Field(default=None, description="Did user mention team/department?")


@mcp.tool()
async def submit_expense(
    amount: float = Field(description="Expense amount in dollars"),
    description: str = Field(description="What was purchased or paid for"),
    context_hints: Optional[ContextHints] = Field(
        default=None,
        description="Hints from the conversation that help with classification"
    ),
    receipt_url: Optional[str] = Field(default=None, description="URL to receipt if already uploaded"),
    approval_id: Optional[str] = Field(default=None, description="Manager approval ID if already obtained"),
) -> str:
    """Submit an expense. The tool uses SELF-PROMPTING to classify ambiguous expenses -
    making its own LLM call with a focused prompt, separate from the main conversation."""

    # Convert ContextHints to dict for the classification function
    hints_dict = None
    if context_hints:
        hints_dict = {
            "mentions_client": context_hints.mentions_client,
            "mentions_team": context_hints.mentions_team,
        }

    # SELF-PROMPTING: Tool classifies the expense using its own LLM call
    classification = await classify_expense_with_fallback(description, amount, hints_dict)

    print(f"[Tool] Classification: {classification['category']} via {classification['source']}", file=sys.stderr)

    # Handle unknown category
    if classification["category"] == "unknown":
        return tool_response({
            "status": "needs_clarification",
            "message": "Could not determine expense category",
            "description_provided": description,
            "classification_confidence": classification["confidence"],
            "hint": "The description is ambiguous. Ask user for more details about what type of expense this is.",
            "tell_user": "I'm not sure how to categorize this expense. Could you tell me more about what it was for?",
        })

    # Handle low confidence - ask for confirmation
    if classification["confidence"] < 0.7:
        return tool_response({
            "status": "needs_clarification",
            "message": "Low confidence in category classification",
            "suggested_category": classification["category"],
            "confidence": classification["confidence"],
            "classification_source": classification["source"],
            "hint": f"The tool thinks this might be \"{classification['category']}\" but isn't confident. Ask user to confirm.",
            "tell_user": f"I think this is a {classification['category']} expense, but I'm not certain. Is that correct?",
        })

    category = classification["category"]

    # Apply business rules (deterministic code)
    rules = database.get_category_rules(category)

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
            "hint": "Amount exceeds category maximum. User may need to split expense or recategorize.",
        })

    # Check receipt requirement
    if amount > rules.receipt_required_over and not receipt_url:
        return tool_response({
            "status": "needs_receipt",
            "message": f"{category} expenses over ${rules.receipt_required_over} require a receipt",
            "category": category,
            "amount": amount,
            "classification_source": classification["source"],
            "next_action": "upload_receipt",
            "next_action_params": {
                "expense_amount": amount,
                "expense_category": category,
            },
            "hint": "Ask user to provide receipt. After upload, retry submit_expense with receipt_url.",
            "tell_user": f"I've categorized this as {category}. I'll need a receipt to complete the submission.",
        })

    # Check approval requirement
    if amount > rules.approval_required_over and not approval_id:
        return tool_response({
            "status": "needs_approval",
            "message": f"{category} expenses over ${rules.approval_required_over} require manager approval",
            "category": category,
            "amount": amount,
            "classification_source": classification["source"],
            "next_action": "request_approval",
            "next_action_params": {
                "amount": amount,
                "category": category,
                "description": description,
                "receipt_url": receipt_url,
            },
            "hint": "Request approval from manager. After approval, retry submit_expense with approval_id.",
            "tell_user": f"This {category} expense needs manager approval. I'll send the request.",
        })

    # Create the expense
    expense = await database.create_expense(
        amount=amount,
        category=category,
        description=description,
        receipt_url=receipt_url,
        approval_id=approval_id,
        status="approved",
        metadata={
            "classification_source": classification["source"],
            "classification_confidence": classification["confidence"],
        },
    )

    return tool_response({
        "status": "success",
        "expense_id": expense.id,
        "expense_number": expense.number,
        "category": category,
        "amount": amount,
        "classification_source": classification["source"],
        "message": f"Expense {expense.number} submitted successfully",
        "tell_user": f"Your {category} expense for ${amount:.2f} has been submitted.",
    })


@mcp.tool()
async def upload_receipt(
    file_data: str = Field(description="Base64 encoded file data"),
    file_type: str = Field(description="File mime type"),
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
        "hint": "Tell user the approval request has been sent. Typical response time is 1-2 business days.",
        "tell_user": f"I've sent the approval request to {approval.approver_name}. This typically takes 1-2 business days.",
    })


# Start the server
if __name__ == "__main__":
    print("Self-Prompting Expense Server running on stdio", file=sys.stderr)
    mcp.run()
