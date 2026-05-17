"""Seed data and tool implementations. Do not modify."""
from datetime import datetime, timedelta

CURRENT_SESSION = 2 # Flip to 2 before running Session 2

_SESSION_DATES = {1: "2025-11-03", 2: "2025-11-06"}

_ALL_TRANSACTIONS = [
    # October food delivery — ₹13,000 total across 16 orders
    {"date": "2025-10-02", "category": "food_delivery", "merchant": "Swiggy",      "amount_inr": 650},
    {"date": "2025-10-04", "category": "food_delivery", "merchant": "Zomato",      "amount_inr": 480},
    {"date": "2025-10-07", "category": "food_delivery", "merchant": "Swiggy",      "amount_inr": 920},
    {"date": "2025-10-09", "category": "food_delivery", "merchant": "Zomato",      "amount_inr": 340},
    {"date": "2025-10-11", "category": "food_delivery", "merchant": "Swiggy",      "amount_inr": 780},
    {"date": "2025-10-14", "category": "food_delivery", "merchant": "Dunzo",       "amount_inr": 1500},
    {"date": "2025-10-16", "category": "food_delivery", "merchant": "Swiggy",      "amount_inr": 620},
    {"date": "2025-10-17", "category": "food_delivery", "merchant": "Zomato",      "amount_inr": 560},
    {"date": "2025-10-19", "category": "food_delivery", "merchant": "Swiggy",      "amount_inr": 890},
    {"date": "2025-10-21", "category": "food_delivery", "merchant": "Zomato",      "amount_inr": 1100},
    {"date": "2025-10-24", "category": "food_delivery", "merchant": "Swiggy",      "amount_inr": 730},
    {"date": "2025-10-26", "category": "food_delivery", "merchant": "Zomato",      "amount_inr": 640},
    {"date": "2025-10-28", "category": "food_delivery", "merchant": "Swiggy",      "amount_inr": 980},
    {"date": "2025-10-30", "category": "food_delivery", "merchant": "Zomato",      "amount_inr": 1250},
    {"date": "2025-10-31", "category": "food_delivery", "merchant": "Swiggy",      "amount_inr": 810},
    {"date": "2025-10-31", "category": "food_delivery", "merchant": "Zomato",      "amount_inr": 750},
    # Nov 1–5 food delivery (current month; Nov 3–5 visible only in Session 2 with days=35)
    {"date": "2025-11-01", "category": "food_delivery", "merchant": "Swiggy",      "amount_inr": 640},
    {"date": "2025-11-02", "category": "food_delivery", "merchant": "Zomato",      "amount_inr": 480},
    # Nov 3–5 food delivery (visible only in Session 2 with days=35)
    {"date": "2025-11-03", "category": "food_delivery", "merchant": "Swiggy",      "amount_inr": 680},
    {"date": "2025-11-04", "category": "food_delivery", "merchant": "Zomato",      "amount_inr": 420},
    {"date": "2025-11-05", "category": "food_delivery", "merchant": "Swiggy",      "amount_inr": 580},
    # Groceries
    {"date": "2025-10-06", "category": "groceries",     "merchant": "BigBasket",   "amount_inr": 3200},
    {"date": "2025-10-20", "category": "groceries",     "merchant": "BigBasket",   "amount_inr": 2600},
    {"date": "2025-11-01", "category": "groceries",     "merchant": "D-Mart",      "amount_inr": 1400},
    # Fuel
    {"date": "2025-10-08", "category": "fuel",          "merchant": "BPCL",        "amount_inr": 1500},
    {"date": "2025-10-22", "category": "fuel",          "merchant": "BPCL",        "amount_inr": 1500},
    {"date": "2025-11-02", "category": "fuel",          "merchant": "Uber",        "amount_inr": 650},
    # Entertainment
    {"date": "2025-10-12", "category": "entertainment", "merchant": "BookMyShow",  "amount_inr": 800},
    {"date": "2025-10-25", "category": "entertainment", "merchant": "Netflix",     "amount_inr": 649},
    # Utilities
    {"date": "2025-10-15", "category": "utilities",     "merchant": "Bescom",      "amount_inr": 1800},
    # Shopping
    {"date": "2025-10-18", "category": "shopping",      "merchant": "Amazon",      "amount_inr": 2400},
    {"date": "2025-10-29", "category": "shopping",      "merchant": "Myntra",      "amount_inr": 1600},
]

_BALANCES = {
    # Session 1: salary just credited Nov 3
    1: {"checking": 145000, "savings": 48000, "house_fund": 22000, "mutual_funds": 125000},
    # Session 2: rent of ₹25,000 paid Nov 5; house fund transfer not yet made
    2: {"checking": 120000, "savings": 48000, "house_fund": 22000, "mutual_funds": 125000},
}

_BILLS = {
    1: [
        {"description": "Rent",                    "amount_inr": 25000, "due_date": "2025-11-05"},
        {"description": "Car EMI",                 "amount_inr": 12000, "due_date": "2025-11-10"},
        {"description": "Health Insurance",        "amount_inr": 3500,  "due_date": "2025-11-15"},
        {"description": "Gym Membership",          "amount_inr": 2000,  "due_date": "2025-11-20"},
        {"description": "Credit Card (min due)",   "amount_inr": 4000,  "due_date": "2025-11-22"},
    ],
    2: [  # Rent already paid
        {"description": "Car EMI",                 "amount_inr": 12000, "due_date": "2025-11-10"},
        {"description": "Health Insurance",        "amount_inr": 3500,  "due_date": "2025-11-15"},
        {"description": "Gym Membership",          "amount_inr": 2000,  "due_date": "2025-11-20"},
        {"description": "Credit Card (min due)",   "amount_inr": 4000,  "due_date": "2025-11-22"},
    ],
}


def get_recent_transactions(days: int) -> list:
    today = datetime.strptime(_SESSION_DATES[CURRENT_SESSION], "%Y-%m-%d")
    cutoff = today - timedelta(days=days)
    return [t for t in _ALL_TRANSACTIONS if datetime.strptime(t["date"], "%Y-%m-%d") >= cutoff]


def get_account_balance() -> dict:
    return _BALANCES[CURRENT_SESSION]


def get_upcoming_bills(days: int = 30) -> list:
    today = datetime.strptime(_SESSION_DATES[CURRENT_SESSION], "%Y-%m-%d")
    cutoff = today + timedelta(days=days)
    return [b for b in _BILLS[CURRENT_SESSION] if datetime.strptime(b["due_date"], "%Y-%m-%d") <= cutoff]


def set_reminder(date: str, content: str) -> dict:
    rid = f"rem_{abs(hash(date + content)) % 10000:04d}"
    return {"status": "success", "reminder_id": rid, "message": f"Reminder set for {date}: {content}"}


TOOLS = {
    "get_recent_transactions": get_recent_transactions,
    "get_account_balance": get_account_balance,
    "get_upcoming_bills": get_upcoming_bills,
    "set_reminder": set_reminder,
}
