"""
Mock database for expense examples
In a real system, this would be a proper database connection
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List, Literal
import time


@dataclass
class Expense:
    id: str
    number: str
    amount: float
    category: str
    description: str
    status: str
    created_at: datetime
    date: Optional[str] = None
    receipt_url: Optional[str] = None
    approval_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class CategoryRules:
    max_amount: float
    receipt_required_over: float
    approval_required_over: float


@dataclass
class Approval:
    id: str
    amount: float
    category: str
    description: str
    status: Literal["pending", "approved", "denied"]
    approver_id: str
    approver_name: str
    created_at: datetime


class MockDatabase:
    def __init__(self):
        self._expenses: Dict[str, Expense] = {}
        self._approvals: Dict[str, Approval] = {}
        self._expense_counter = 1
        self._approval_counter = 1

        self._category_rules: Dict[str, CategoryRules] = {
            "meals": CategoryRules(
                max_amount=150,
                receipt_required_over=25,
                approval_required_over=100,
            ),
            "client_entertainment": CategoryRules(
                max_amount=500,
                receipt_required_over=25,
                approval_required_over=150,
            ),
            "team_meals": CategoryRules(
                max_amount=300,
                receipt_required_over=50,
                approval_required_over=200,
            ),
            "travel": CategoryRules(
                max_amount=5000,
                receipt_required_over=50,
                approval_required_over=500,
            ),
            "supplies": CategoryRules(
                max_amount=1000,
                receipt_required_over=100,
                approval_required_over=500,
            ),
            "software": CategoryRules(
                max_amount=2000,
                receipt_required_over=0,
                approval_required_over=500,
            ),
        }

    async def create_expense(
        self,
        amount: float,
        category: str,
        description: str,
        status: str,
        date: Optional[str] = None,
        receipt_url: Optional[str] = None,
        approval_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Expense:
        expense_id = f"exp_{self._expense_counter}"
        self._expense_counter += 1
        number = f"EXP-{str(self._expense_counter).zfill(6)}"

        expense = Expense(
            id=expense_id,
            number=number,
            amount=amount,
            category=category,
            description=description,
            status=status,
            created_at=datetime.now(),
            date=date,
            receipt_url=receipt_url,
            approval_id=approval_id,
            metadata=metadata,
        )

        self._expenses[expense_id] = expense
        return expense

    async def get_expense(self, expense_id: str) -> Optional[Expense]:
        return self._expenses.get(expense_id)

    def get_expenses(self) -> List[Expense]:
        return list(self._expenses.values())

    def get_category_rules(self, category: str) -> CategoryRules:
        return self._category_rules.get(
            category,
            CategoryRules(
                max_amount=1000,
                receipt_required_over=100,
                approval_required_over=500,
            ),
        )

    def get_all_category_rules(self) -> Dict[str, CategoryRules]:
        return dict(self._category_rules)

    async def create_approval(
        self,
        amount: float,
        category: str,
        description: str,
        approver_name: Optional[str] = None,
    ) -> Approval:
        approval_id = f"apr_{self._approval_counter}"
        self._approval_counter += 1

        approval = Approval(
            id=approval_id,
            amount=amount,
            category=category,
            description=description,
            status="pending",
            approver_id="mgr_001",
            approver_name=approver_name or "Jane Smith",
            created_at=datetime.now(),
        )

        self._approvals[approval_id] = approval
        return approval

    async def get_approval(self, approval_id: str) -> Optional[Approval]:
        return self._approvals.get(approval_id)

    async def approve_approval(self, approval_id: str) -> Optional[Approval]:
        approval = self._approvals.get(approval_id)
        if approval:
            approval.status = "approved"
        return approval


# Singleton instance
database = MockDatabase()


# Mock receipt storage
class Storage:
    async def upload_receipt(self, file_data: str, file_type: str) -> Dict[str, str]:
        receipt_id = f"rcpt_{int(time.time() * 1000)}"
        url = f"https://storage.example.com/receipts/{receipt_id}"
        return {"url": url, "id": receipt_id}


storage = Storage()
