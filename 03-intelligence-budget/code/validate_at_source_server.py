"""
Validate at Source Expense Server

This server demonstrates VALIDATE AT SOURCE - where validation happens in the tool,
including SEMANTIC validation using embedded LLM calls (self-prompting).

The validation stack (from cheap to expensive):
1. FORMAT VALIDATION: Schema/type checking (Pydantic) - FREE, instant
2. BUSINESS RULES: Amount limits, date ranges - FREE, instant
3. SEMANTIC VALIDATION: "Is this description meaningful?" - LLM call, ~1 second
4. HUMAN REVIEW: Low-confidence cases flagged - Human time

The key insight: just because validating "asdfasdf" requires understanding that
it's gibberish doesn't mean the AGENT needs to do that check. A self-prompted
LLM call in the tool can make that judgment.

Run with: python validate_at_source_server.py
"""

import json
import os
import re
import sys
from datetime import datetime, timedelta
from typing import Optional, List, Literal, Dict, Any

from dotenv import load_dotenv
from pydantic import Field
from openai import OpenAI
from mcp.server.fastmcp import FastMCP

from database import database, storage

# Load environment variables
load_dotenv()

# Initialize OpenAI client
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Create the MCP server
mcp = FastMCP("expense-validate-at-source")


def tool_response(data: dict) -> str:
    """Format response as JSON string."""
    return json.dumps(data, indent=2)


# ============================================================================
# VALIDATION STACK - Layer 2: Business Rules (FREE)
# ============================================================================

async def validate_business_rules(
    amount: float,
    category: str,
    date: Optional[str] = None
) -> Dict[str, Any]:
    """Validate business rules for an expense."""
    print(f"[Validation L2] Business rules for {category}, ${amount}", file=sys.stderr)

    # Amount limits by category
    category_limits: Dict[str, float] = {
        "meals": 100,
        "team_meals": 500,
        "client_entertainment": 300,
        "travel": 5000,
        "supplies": 500,
        "software": 1000,
    }

    max_amount = category_limits.get(category, 500)
    if amount > max_amount:
        return {
            "valid": False,
            "error": f"{category} expenses are limited to ${max_amount}. This expense of ${amount} exceeds that limit.",
        }

    # Date validation (if provided)
    if date:
        try:
            expense_date = datetime.fromisoformat(date)
            now = datetime.now()
            ninety_days_ago = now - timedelta(days=90)

            if expense_date > now:
                return {
                    "valid": False,
                    "error": "Expense date cannot be in the future.",
                }

            if expense_date < ninety_days_ago:
                return {
                    "valid": False,
                    "error": "Expenses older than 90 days cannot be submitted. Please contact finance for exceptions.",
                }

            # Weekend client entertainment warning
            if category == "client_entertainment":
                day_of_week = expense_date.weekday()
                if day_of_week in (5, 6):  # Saturday = 5, Sunday = 6
                    return {
                        "valid": True,
                        "warning": "weekend_client_entertainment",
                    }
        except ValueError:
            return {
                "valid": False,
                "error": "Invalid date format. Use YYYY-MM-DD.",
            }

    return {"valid": True}


# ============================================================================
# VALIDATION STACK - Layer 3: Semantic Validation (Self-Prompting)
# ============================================================================

async def validate_semantics(
    description: str,
    category: str,
    amount: float,
    flags: Optional[Dict[str, bool]] = None
) -> Dict[str, Any]:
    """
    Semantic validation uses SELF-PROMPTING to determine if the expense
    description is meaningful and appropriate.

    This is where we catch:
    - Gibberish like "asdfasdf"
    - Vague descriptions like "stuff"
    - Category mismatches like "dinner" under "software"
    - Suspicious amounts like $500 for "coffee"
    """
    print(f'[Validation L3] Semantic check for "{description}"', file=sys.stderr)

    # QUICK DETERMINISTIC CHECKS (no LLM needed)
    # These catch obvious garbage before spending tokens

    # Check for gibberish patterns
    gibberish_patterns = [
        r'^[a-z]{5,}$',  # Random letters like "asdfgh"
        r'^[\d\s]+$',     # Just numbers and spaces
        r'(.)\1{4,}',     # Repeated characters like "aaaaa"
        r'^test$',        # Test entries
        r'^xxx+$',        # Placeholder
    ]

    description_stripped = description.strip()
    for pattern in gibberish_patterns:
        if re.match(pattern, description_stripped, re.IGNORECASE):
            print("[Validation L3] Gibberish detected (pattern match)", file=sys.stderr)
            return {
                "valid": False,
                "confidence": 0.95,
                "issues": ["Description appears to be placeholder or test text"],
                "suggestions": ["Provide a meaningful description of what this expense was for"],
            }

    # Check minimum meaningful content
    words = description_stripped.split()
    if len(words) < 2:
        print(f"[Validation L3] Too brief ({len(words)} words)", file=sys.stderr)
        return {
            "valid": False,
            "confidence": 0.9,
            "issues": ["Description is too brief for audit purposes"],
            "suggestions": ["Include what the expense was for and any relevant context"],
        }

    # FOR GENUINELY AMBIGUOUS CASES: Use self-prompting
    print("[Validation L3] Using LLM for semantic check", file=sys.stderr)

    weekend_note = ""
    if flags and flags.get("weekend_entertainment"):
        weekend_note = "Note: This is weekend client entertainment."

    response = openai_client.responses.create(
        model="gpt-4o-mini",
        input=[
            {
                "role": "user",
                "content": f"""Category: {category}
Amount: ${amount}
Description: "{description}"
{weekend_note}""",
            }
        ],
        instructions="""You validate expense report descriptions. Check for:

1. MEANINGFULNESS: Is this a real expense description or placeholder text?
   - "asdfgh" = NOT meaningful
   - "Lunch at downtown cafe" = meaningful

2. CATEGORY MATCH: Does the description match the stated category?
   - meals: Food purchases for individual work meals
   - client_entertainment: Meals/events with clients, customers, prospects
   - team_meals: Team lunches, celebrations, department events
   - travel: Transportation, lodging, related expenses
   - supplies: Office supplies and equipment
   - software: Software subscriptions and licenses

3. REASONABLENESS: Is the amount reasonable for what's described?
   - $500 coffee -> suspicious
   - $15 lunch -> reasonable
   - $200 team dinner for 10 people -> reasonable

4. POLICY FLAGS: Any concerns?
   - Mentions of alcohol in large amounts
   - Luxury items not clearly justified
   - Vague descriptions for large amounts

Respond with JSON only:
{
  "valid": true/false,
  "confidence": 0.0-1.0,
  "issues": ["list of problems, empty array if valid"],
  "suggestions": ["how to fix, empty array if valid"]
}""",
        temperature=0,
    )

    # Parse response
    text = response.output_text or ""
    try:
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            result = json.loads(json_match.group())
            print(f"[Validation L3] LLM result: valid={result.get('valid')}, confidence={result.get('confidence')}", file=sys.stderr)
            return {
                "valid": result.get("valid", True),
                "confidence": result.get("confidence", 0.8),
                "issues": result.get("issues", []),
                "suggestions": result.get("suggestions", []),
            }
    except Exception as e:
        print(f"[Validation L3] Parse error: {e}", file=sys.stderr)

    # Fallback: assume valid if LLM response is unparseable
    return {
        "valid": True,
        "confidence": 0.6,
        "issues": [],
        "suggestions": [],
    }


# ============================================================================
# MCP Tool with Full Validation Stack
# ============================================================================

@mcp.tool()
async def submit_expense(
    amount: float = Field(gt=0, description="Amount must be positive"),
    description: str = Field(min_length=1, max_length=500, description="Description required"),
    category: Literal["meals", "travel", "supplies", "software", "client_entertainment", "team_meals"] = Field(
        description="Expense category"
    ),
    date: Optional[str] = Field(default=None, description="Date must be YYYY-MM-DD"),
    receipt_url: Optional[str] = Field(default=None, description="URL to receipt"),
    approval_id: Optional[str] = Field(default=None, description="Manager approval ID"),
) -> str:
    """Submit an expense with comprehensive validation.

    The tool validates at multiple layers:
    1. FORMAT: Schema validation (automatic via Pydantic)
    2. BUSINESS RULES: Amount limits, date ranges
    3. SEMANTIC: Is the description meaningful? Does it match the category?
    4. HUMAN REVIEW: Low-confidence cases are flagged

    The agent never needs to validate - the tool handles everything and returns
    either success or a clear error with guidance.
    """
    print(f"\n[Submit] Starting validation for ${amount} {category}", file=sys.stderr)

    # LAYER 1: Format validation already happened via Pydantic schema
    print("[Validation L1] Format: PASSED (Pydantic)", file=sys.stderr)

    # LAYER 2: Business rules
    business_check = await validate_business_rules(amount, category, date)

    if not business_check["valid"]:
        print("[Validation L2] Business rules: FAILED", file=sys.stderr)
        return tool_response({
            "status": "rejected",
            "validation_layer": "business_rules",
            "message": business_check["error"],
            "tell_user": business_check["error"],
        })
    print("[Validation L2] Business rules: PASSED", file=sys.stderr)

    # LAYER 3: Semantic validation
    semantic_check = await validate_semantics(
        description, category, amount,
        {"weekend_entertainment": business_check.get("warning") == "weekend_client_entertainment"}
    )

    if not semantic_check["valid"]:
        print("[Validation L3] Semantic: REJECTED", file=sys.stderr)
        issues_text = " ".join(semantic_check.get("issues", []))
        suggestions_text = " ".join(semantic_check.get("suggestions", []))
        return tool_response({
            "status": "rejected",
            "validation_layer": "semantic",
            "message": "Description validation failed",
            "issues": semantic_check.get("issues", []),
            "suggestions": semantic_check.get("suggestions", []),
            "tell_user": f"{issues_text} {suggestions_text}",
        })
    print(f"[Validation L3] Semantic: PASSED (confidence: {semantic_check['confidence']})", file=sys.stderr)

    # LAYER 4: Flag low-confidence for human review
    if semantic_check["confidence"] < 0.75:
        print("[Validation L4] Flagging for human review (low confidence)", file=sys.stderr)

        expense = await database.create_expense(
            amount=amount,
            category=category,
            description=description,
            date=date,
            receipt_url=receipt_url,
            approval_id=approval_id,
            status="pending_review",
            metadata={
                "review_reason": "low_validation_confidence",
                "validation_confidence": semantic_check["confidence"],
            },
        )

        return tool_response({
            "status": "pending_review",
            "validation_layer": "human_review",
            "expense_id": expense.id,
            "expense_number": expense.number,
            "confidence": semantic_check["confidence"],
            "message": "Expense submitted but flagged for manual review",
            "tell_user": "I've submitted your expense, but it's been flagged for manual review due to some uncertainty. You'll be notified once it's processed.",
        })

    # ALL VALIDATION PASSED - Check operational requirements
    rules = database.get_category_rules(category)

    # Need receipt?
    if amount > rules.receipt_required_over and not receipt_url:
        return tool_response({
            "status": "needs_receipt",
            "validation_layer": "passed",
            "category": category,
            "amount": amount,
            "message": f"{category} expenses over ${rules.receipt_required_over} require a receipt",
            "next_action": "upload_receipt",
            "next_action_params": {
                "expense_amount": amount,
                "expense_category": category,
            },
            "tell_user": f"Validation passed! This {category} expense of ${amount} requires a receipt. Please upload one to complete the submission.",
        })

    # Need approval?
    if amount > rules.approval_required_over and not approval_id:
        return tool_response({
            "status": "needs_approval",
            "validation_layer": "passed",
            "category": category,
            "amount": amount,
            "message": f"{category} expenses over ${rules.approval_required_over} require approval",
            "next_action": "request_approval",
            "next_action_params": {
                "amount": amount,
                "category": category,
                "description": description,
                "receipt_url": receipt_url,
            },
            "tell_user": f"Validation passed! This {category} expense needs manager approval.",
        })

    # CREATE THE EXPENSE
    expense = await database.create_expense(
        amount=amount,
        category=category,
        description=description,
        date=date,
        receipt_url=receipt_url,
        approval_id=approval_id,
        status="approved",
        metadata={
            "validation_confidence": semantic_check["confidence"],
        },
    )

    print(f"[Submit] SUCCESS: {expense.number}", file=sys.stderr)

    return tool_response({
        "status": "success",
        "validation_layer": "all_passed",
        "expense_id": expense.id,
        "expense_number": expense.number,
        "category": category,
        "amount": amount,
        "validation_confidence": semantic_check["confidence"],
        "message": f"Expense {expense.number} submitted successfully",
        "tell_user": f"Your {category} expense of ${amount} has been validated and submitted.",
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
        "message": "Receipt uploaded successfully",
        "receipt_url": receipt["url"],
        "receipt_id": receipt["id"],
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
        "message": f"Approval request sent to {approval.approver_name}",
        "approval_id": approval.id,
        "approval_status": approval.status,
        "approver": approval.approver_name,
        "next_action": "wait",
        "hint": "Tell user the approval request has been sent.",
        "tell_user": f"I've sent the approval request to {approval.approver_name}. This typically takes 1-2 business days.",
    })


# ============================================================================
# Demo Tool: Test Validation
# ============================================================================

@mcp.tool()
async def test_validation(
    descriptions: List[str] = Field(description="List of descriptions to test"),
    category: Literal["meals", "travel", "supplies", "software", "client_entertainment", "team_meals"] = Field(
        description="Category to test against"
    ),
    amount: float = Field(description="Amount to test"),
) -> str:
    """Test the validation stack with sample descriptions.
    Returns how each description would be validated without actually creating expenses."""
    results = []

    for desc in descriptions:
        print(f'\n[Test] Validating: "{desc}"', file=sys.stderr)

        # Business rules (always pass for this test)
        business_result = await validate_business_rules(amount, category)

        # Semantic validation
        semantic_result = await validate_semantics(desc, category, amount)

        results.append({
            "description": desc,
            "business_valid": business_result["valid"],
            "semantic_valid": semantic_result["valid"],
            "confidence": semantic_result["confidence"],
            "issues": semantic_result.get("issues", []),
            "suggestions": semantic_result.get("suggestions", []),
            "would_be_flagged": semantic_result["confidence"] < 0.75,
        })

    return tool_response({
        "category": category,
        "amount": amount,
        "results": results,
        "summary": {
            "tested": len(results),
            "would_pass": len([r for r in results if r["semantic_valid"] and not r["would_be_flagged"]]),
            "would_be_flagged": len([r for r in results if r["would_be_flagged"]]),
            "would_fail": len([r for r in results if not r["semantic_valid"]]),
        },
    })


# Start the server
if __name__ == "__main__":
    print("Validate at Source Expense Server running on stdio", file=sys.stderr)
    mcp.run()
