# expenses.py — FLOAT AI Desktop Assistant
# Manages local expense tracking via expenses.json

import json
import logging
from datetime import datetime
from pathlib import Path
from config import BASE_DIR

logger = logging.getLogger("FLOAT.expenses")
EXPENSES_FILE = BASE_DIR / "expenses.json"

def _load_expenses() -> list:
    if EXPENSES_FILE.exists():
        try:
            with open(EXPENSES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Expense load error: {e}")
    return []

def _save_expenses(expenses: list) -> None:
    try:
        with open(EXPENSES_FILE, "w", encoding="utf-8") as f:
            json.dump(expenses, f, indent=2)
    except Exception as e:
        logger.error(f"Expense save error: {e}")

def add_expense(amount: float, category: str) -> str:
    """Add a new expense record."""
    expenses = _load_expenses()
    record = {
        "amount": amount,
        "category": category.lower(),
        "date": datetime.now().isoformat()
    }
    expenses.append(record)
    _save_expenses(expenses)
    
    currency = "rupees" if amount > 0 else ""
    return f"Added {amount} {currency} to your {category} expenses."

def get_summary(period: str = "month") -> str:
    """Summarize expenses for the given period (month/today/total)."""
    expenses = _load_expenses()
    if not expenses:
        return "You have no recorded expenses."

    now = datetime.now()
    total = 0.0
    category_totals = {}

    for exp in expenses:
        exp_date = datetime.fromisoformat(exp["date"])
        
        # Filter by period
        if period == "today" and exp_date.date() != now.date():
            continue
        if period == "month" and (exp_date.month != now.month or exp_date.year != now.year):
            continue
            
        amt = exp.get("amount", 0.0)
        cat = exp.get("category", "other")
        total += amt
        category_totals[cat] = category_totals.get(cat, 0.0) + amt

    if total == 0:
        return f"You haven't spent anything this {period}."

    # Format summary
    summary = f"You have spent a total of {total} rupees this {period}. "
    if category_totals:
        top_cats = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)[:3]
        cat_str = ", ".join([f"{amt} on {c}" for c, amt in top_cats])
        summary += f"Mainly: {cat_str}."
        
    return summary
