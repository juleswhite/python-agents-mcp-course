"""
Scripted Orchestration Expense Server

This server demonstrates SCRIPTED ORCHESTRATION - where agents write code that
orchestrates tools, rather than calling each tool step-by-step through the agent loop.

The key insight: instead of the agent manually stepping through each operation and
looking at each result, it writes a script that does the stepping. The script runs
OUTSIDE the agent's context window, processes all data, and returns only the final result.

Benefits:
- Dramatically more token-efficient (intermediate data never touches agent context)
- Deterministic (script does exactly what it says, every time)
- Faster (no round-trips through agent between tool calls)
- Enables parallel operations

Run with: python scripted_orchestration_server.py
"""

import json
import sys
import asyncio
import time
from typing import Optional, Literal, Dict, Any, List

from pydantic import Field
from mcp.server.fastmcp import FastMCP

from database import database, storage

# Create the MCP server
mcp = FastMCP("expense-scripted-orchestration")


def tool_response(data: dict) -> str:
    """Format response as JSON string."""
    return json.dumps(data, indent=2)


# ============================================================================
# Workflow Tools - Available to scripts via the `tools` object
# ============================================================================

class WorkflowTools:
    """
    These are the tools that agent-written scripts can call.
    They're wrapped versions of database operations.
    """

    async def get_expenses(
        self,
        status: Optional[str] = None,
        category: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get all expenses for the current user."""
        print(f"[Workflow] get_expenses({json.dumps({'status': status, 'category': category, 'limit': limit})})", file=sys.stderr)
        expenses = database.get_expenses()

        filtered = expenses
        if status:
            filtered = [e for e in filtered if e.status == status]
        if category:
            filtered = [e for e in filtered if e.category == category]
        if limit:
            filtered = filtered[:limit]

        # Convert to dicts for JSON serialization
        return [
            {
                "id": e.id,
                "number": e.number,
                "amount": e.amount,
                "category": e.category,
                "description": e.description,
                "status": e.status,
                "receipt_url": e.receipt_url,
                "created_at": e.created_at.isoformat(),
            }
            for e in filtered
        ]

    async def get_expense(self, expense_id: str) -> Optional[Dict[str, Any]]:
        """Get a single expense by ID."""
        print(f"[Workflow] get_expense({expense_id})", file=sys.stderr)
        expense = await database.get_expense(expense_id)
        if not expense:
            return None
        return {
            "id": expense.id,
            "number": expense.number,
            "amount": expense.amount,
            "category": expense.category,
            "description": expense.description,
            "status": expense.status,
            "receipt_url": expense.receipt_url,
            "created_at": expense.created_at.isoformat(),
        }

    async def create_expense(
        self,
        amount: float,
        category: str,
        description: str,
        receipt_url: Optional[str] = None,
        approval_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new expense."""
        print(f"[Workflow] create_expense({category}, ${amount})", file=sys.stderr)
        expense = await database.create_expense(
            amount=amount,
            category=category,
            description=description,
            receipt_url=receipt_url,
            approval_id=approval_id,
            status="pending" if not approval_id else "approved",
        )
        return {
            "id": expense.id,
            "number": expense.number,
            "amount": expense.amount,
            "category": expense.category,
            "description": expense.description,
            "status": expense.status,
        }

    async def get_category_rules(self, category: str) -> Dict[str, Any]:
        """Get business rules for a category."""
        print(f"[Workflow] get_category_rules({category})", file=sys.stderr)
        rules = database.get_category_rules(category)
        return {
            "max_amount": rules.max_amount,
            "receipt_required_over": rules.receipt_required_over,
            "approval_required_over": rules.approval_required_over,
        }

    async def get_all_category_rules(self) -> Dict[str, Dict[str, Any]]:
        """Get all category rules."""
        print("[Workflow] get_all_category_rules()", file=sys.stderr)
        all_rules = database.get_all_category_rules()
        return {
            name: {
                "max_amount": rules.max_amount,
                "receipt_required_over": rules.receipt_required_over,
                "approval_required_over": rules.approval_required_over,
            }
            for name, rules in all_rules.items()
        }

    async def request_approval(
        self,
        amount: float,
        category: str,
        description: str
    ) -> Dict[str, Any]:
        """Request approval for an expense."""
        print(f"[Workflow] request_approval({category}, ${amount})", file=sys.stderr)
        approval = await database.create_approval(
            amount=amount,
            category=category,
            description=description,
        )
        return {
            "id": approval.id,
            "status": approval.status,
            "approver_name": approval.approver_name,
        }

    async def upload_receipt(self, file_data: str, file_type: str) -> Dict[str, str]:
        """Upload a receipt."""
        print(f"[Workflow] upload_receipt({file_type})", file=sys.stderr)
        return await storage.upload_receipt(file_data, file_type)

    async def get_expense_stats(self) -> Dict[str, Any]:
        """Get expense statistics."""
        print("[Workflow] get_expense_stats()", file=sys.stderr)
        expenses = database.get_expenses()

        stats: Dict[str, Any] = {
            "total_count": len(expenses),
            "total_amount": sum(e.amount for e in expenses),
            "by_status": {},
            "by_category": {},
        }

        for expense in expenses:
            # By status
            if expense.status not in stats["by_status"]:
                stats["by_status"][expense.status] = {"count": 0, "amount": 0}
            stats["by_status"][expense.status]["count"] += 1
            stats["by_status"][expense.status]["amount"] += expense.amount

            # By category
            if expense.category not in stats["by_category"]:
                stats["by_category"][expense.category] = {"count": 0, "amount": 0}
            stats["by_category"][expense.category]["count"] += 1
            stats["by_category"][expense.category]["amount"] += expense.amount

        return stats


# Singleton instance
workflow_tools = WorkflowTools()


# ============================================================================
# The execute_workflow Tool - Core of Scripted Orchestration
# ============================================================================

@mcp.tool()
async def execute_workflow(
    code: str = Field(description="Python code to execute. Must return a value."),
) -> str:
    """Execute a Python workflow script. The script has access to a 'tools' object
    with these async functions:

    - await tools.get_expenses(status=None, category=None, limit=None) - Get expenses
    - await tools.get_expense(expense_id) - Get single expense
    - await tools.create_expense(amount, category, description, receipt_url=None, approval_id=None) - Create expense
    - await tools.get_category_rules(category) - Get rules for category
    - await tools.get_all_category_rules() - Get all category rules
    - await tools.request_approval(amount, category, description) - Request approval
    - await tools.upload_receipt(file_data, file_type) - Upload receipt
    - await tools.get_expense_stats() - Get expense statistics

    The script runs in a restricted environment with:
    - Full async/await support
    - Access to basic Python built-ins (dict, list, sum, len, etc.)
    - 60 second timeout
    - No access to filesystem, network, or process

    Example workflow:
    ```python
    expenses = await tools.get_expenses(status='pending')
    needs_receipt = [e for e in expenses if e['amount'] > 25 and not e.get('receipt_url')]
    return {
        'pending_count': len(expenses),
        'needs_receipt': len(needs_receipt),
        'expenses_needing_receipt': needs_receipt[:5]
    }
    ```
    """
    print(f"[Execute Workflow] Running script ({len(code)} chars)", file=sys.stderr)
    start_time = time.time()

    # Create a restricted global namespace
    restricted_globals = {
        "__builtins__": {
            # Safe built-ins only
            "len": len,
            "sum": sum,
            "min": min,
            "max": max,
            "abs": abs,
            "round": round,
            "sorted": sorted,
            "reversed": reversed,
            "enumerate": enumerate,
            "zip": zip,
            "map": map,
            "filter": filter,
            "list": list,
            "dict": dict,
            "set": set,
            "tuple": tuple,
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "range": range,
            "print": lambda *args: print("[Script]", *args, file=sys.stderr),
            "True": True,
            "False": False,
            "None": None,
        },
        "tools": workflow_tools,
    }

    # Wrap the code in an async function
    wrapped_code = f"""
async def __workflow__():
{chr(10).join('    ' + line for line in code.split(chr(10)))}

__result__ = __workflow__()
"""

    try:
        # Compile and execute
        compiled = compile(wrapped_code, "<workflow>", "exec")
        local_namespace: Dict[str, Any] = {}
        exec(compiled, restricted_globals, local_namespace)

        # Get the coroutine and run it with timeout
        coro = local_namespace["__result__"]
        result = await asyncio.wait_for(coro, timeout=60.0)

        execution_time = int((time.time() - start_time) * 1000)
        print(f"[Execute Workflow] Completed in {execution_time}ms", file=sys.stderr)

        return tool_response({
            "status": "success",
            "message": "Workflow executed successfully",
            "result": result,
            "execution_time_ms": execution_time,
        })

    except asyncio.TimeoutError:
        execution_time = int((time.time() - start_time) * 1000)
        print(f"[Execute Workflow] Timeout after {execution_time}ms", file=sys.stderr)
        return tool_response({
            "status": "error",
            "message": "Workflow execution timed out after 60 seconds",
            "error": "timeout",
            "execution_time_ms": execution_time,
        })

    except Exception as e:
        execution_time = int((time.time() - start_time) * 1000)
        print(f"[Execute Workflow] Error after {execution_time}ms: {e}", file=sys.stderr)
        return tool_response({
            "status": "error",
            "message": "Workflow execution failed",
            "error": str(e),
            "execution_time_ms": execution_time,
            "hint": "Check the script for syntax errors or invalid tool calls.",
        })


# ============================================================================
# Additional Tools for Direct Use (non-workflow)
# ============================================================================

@mcp.tool()
async def submit_expense(
    amount: float = Field(description="Expense amount in dollars"),
    category: Literal["meals", "travel", "supplies", "software", "client_entertainment", "team_meals"] = Field(
        description="Expense category"
    ),
    description: str = Field(description="What the expense was for"),
    receipt_url: Optional[str] = Field(default=None, description="URL to receipt"),
    approval_id: Optional[str] = Field(default=None, description="Manager approval ID"),
) -> str:
    """Submit a single expense directly (for simple cases where a workflow isn't needed)."""
    rules = database.get_category_rules(category)

    # Validate
    if amount <= 0:
        return tool_response({
            "status": "error",
            "message": "Amount must be greater than zero",
            "error": "invalid_amount",
        })

    if amount > rules.max_amount:
        return tool_response({
            "status": "error",
            "message": f"{category} expenses cannot exceed ${rules.max_amount}",
            "error": "amount_too_high",
        })

    # Check requirements
    if amount > rules.receipt_required_over and not receipt_url:
        return tool_response({
            "status": "error",
            "message": f"{category} expenses over ${rules.receipt_required_over} require a receipt",
            "error": "needs_receipt",
        })

    if amount > rules.approval_required_over and not approval_id:
        return tool_response({
            "status": "error",
            "message": f"{category} expenses over ${rules.approval_required_over} require approval",
            "error": "needs_approval",
        })

    # Create expense
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
        "message": f"Expense {expense.number} submitted",
        "expense_id": expense.id,
        "expense_number": expense.number,
    })


@mcp.tool()
async def get_workflow_examples() -> str:
    """Get example workflow scripts for common tasks."""
    examples = [
        {
            "name": "Summarize pending expenses",
            "description": "Get a summary of all pending expenses by category",
            "code": """expenses = await tools.get_expenses(status='pending')

by_category = {}
for e in expenses:
    if e['category'] not in by_category:
        by_category[e['category']] = {'count': 0, 'total': 0}
    by_category[e['category']]['count'] += 1
    by_category[e['category']]['total'] += e['amount']

return {
    'total_pending': len(expenses),
    'total_amount': sum(e['amount'] for e in expenses),
    'by_category': by_category
}""",
        },
        {
            "name": "Find expenses needing receipts",
            "description": "Find all expenses over the receipt threshold without receipts",
            "code": """expenses = await tools.get_expenses()
all_rules = await tools.get_all_category_rules()

needs_receipt = []
for e in expenses:
    rules = all_rules.get(e['category'], {})
    if e['amount'] > rules.get('receipt_required_over', 100) and not e.get('receipt_url'):
        needs_receipt.append({
            'id': e['id'],
            'category': e['category'],
            'amount': e['amount'],
            'description': e['description']
        })

return {
    'count': len(needs_receipt),
    'expenses': needs_receipt
}""",
        },
        {
            "name": "Batch expense submission",
            "description": "Submit multiple small expenses at once",
            "code": """expenses = [
    {'amount': 12, 'category': 'meals', 'description': 'Coffee meeting'},
    {'amount': 8, 'category': 'meals', 'description': 'Lunch snack'},
    {'amount': 15, 'category': 'supplies', 'description': 'Notebooks'}
]

results = []
for e in expenses:
    created = await tools.create_expense(
        amount=e['amount'],
        category=e['category'],
        description=e['description']
    )
    results.append({
        'id': created['id'],
        'number': created['number'],
        'amount': e['amount']
    })

return {
    'submitted': len(results),
    'expenses': results,
    'total_amount': sum(e['amount'] for e in expenses)
}""",
        },
        {
            "name": "Expense analysis report",
            "description": "Generate a comprehensive expense analysis",
            "code": """stats = await tools.get_expense_stats()
all_rules = await tools.get_all_category_rules()

analysis = {
    'overview': {
        'total_expenses': stats['total_count'],
        'total_spent': stats['total_amount']
    },
    'by_category': {},
    'recommendations': []
}

for category, data in stats.get('by_category', {}).items():
    rules = all_rules.get(category, {})
    avg_amount = data['amount'] / data['count'] if data['count'] > 0 else 0

    analysis['by_category'][category] = {
        'count': data['count'],
        'total': data['amount'],
        'average': round(avg_amount, 2),
        'max_allowed': rules.get('max_amount', 1000)
    }

    if avg_amount > rules.get('max_amount', 1000) * 0.8:
        analysis['recommendations'].append(
            f"{category} expenses are averaging near the limit"
        )

return analysis""",
        },
    ]

    return tool_response({
        "message": "Example workflow scripts",
        "examples": examples,
        "hint": "Copy and modify these scripts for your needs, then call execute_workflow with the code.",
    })


# Start the server
if __name__ == "__main__":
    print("Scripted Orchestration Expense Server running on stdio", file=sys.stderr)
    mcp.run()
