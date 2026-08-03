"""Seed <count> realistic expenses for a user, spread across the past <months> months.

Usage: python seed_expenses.py <user_id> <count> <months>
"""
import random
import sys
from datetime import datetime, timedelta

from database.db import get_db, init_db


# Category -> (min_amount, max_amount, weighted_share). Food is most common;
# Health and Entertainment are rarest. Shares are relative weights, not %.
# Weights chosen so distribution feels right for a typical personal budget.
CATEGORIES = [
    ("Food",          50,  800,  28),
    ("Transport",     20,  500,  18),
    ("Bills",         200, 3000, 14),
    ("Shopping",      200, 5000, 12),
    ("Other",         50,  1000, 12),
    ("Entertainment", 100, 1500,  8),
    ("Health",        100, 2000,  8),
]

# Realistic Indian descriptions per category.
DESCRIPTIONS = {
    "Food": [
        "Groceries — weekly run",
        "Chai and samosa",
        "Lunch at office canteen",
        "Dinner with friends",
        "Breakfast at local stall",
        "Swiggy order",
        "Zomato order",
        "Vegetable vendor",
        "Dairy — milk and curd",
        "Sunday biryani",
    ],
    "Transport": [
        "Metro card top-up",
        "Auto rickshaw",
        "Uber ride",
        "Ola ride",
        "Rapido bike",
        "Petrol refill",
        "Diesel for car",
        "State bus ticket",
        "Parking fee",
        "Cab to airport",
    ],
    "Bills": [
        "Electricity bill",
        "Mobile recharge",
        "Broadband bill",
        "Gas cylinder",
        "Water bill",
        "DTH recharge",
        "Insurance premium",
        "Society maintenance",
    ],
    "Shopping": [
        "New running shoes",
        "Clothes from local market",
        "Amazon order",
        "Flipkart order",
        "Myntra order",
        "Electronics accessory",
        "Books",
        "Home essentials",
    ],
    "Health": [
        "Pharmacy",
        "Doctor consultation",
        "Lab tests",
        "Gym membership",
        "Yoga class",
        "Vitamins and supplements",
        "Dental checkup",
    ],
    "Entertainment": [
        "Movie tickets",
        "Netflix subscription",
        "Spotify Premium",
        "OTT rental",
        "Concert tickets",
        "Weekend outing",
        "Board game cafe",
    ],
    "Other": [
        "Gift for friend",
        "Household supplies",
        "Stationery",
        "Donation",
        "Miscellaneous",
        "Courier charges",
        "Salon visit",
    ],
}


def generate_one(user_id, months):
    """Return a single random expense tuple for the given user."""
    category, lo, hi, _weight = random.choices(
        CATEGORIES, weights=[c[3] for c in CATEGORIES], k=1
    )[0]
    amount = round(random.uniform(lo, hi), 2)
    description = random.choice(DESCRIPTIONS[category])

    # Spread across the past <months> months (inclusive of current month).
    today = datetime.now()
    earliest = today - timedelta(days=months * 30)
    delta_seconds = int((today - earliest).total_seconds())
    random_seconds = random.randint(0, delta_seconds)
    date = (earliest + timedelta(seconds=random_seconds)).date().isoformat()

    return (user_id, amount, category, date, description)


def main():
    if len(sys.argv) != 4:
        print("Usage: /seed-expenses <user_id> <count> <months>")
        print("Example: /seed-expenses 1 50 6")
        sys.exit(1)

    try:
        user_id = int(sys.argv[1])
        count = int(sys.argv[2])
        months = int(sys.argv[3])
    except ValueError:
        print("Usage: /seed-expenses <user_id> <count> <months>")
        print("Example: /seed-expenses 1 50 6")
        sys.exit(1)

    if count <= 0 or months <= 0:
        print("count and months must be positive integers.")
        sys.exit(1)

    # Schema + user existence check.
    init_db()
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT 1 FROM users WHERE id = ?", (user_id,))
    if cur.fetchone() is None:
        conn.close()
        print(f"No user found with id {user_id}.")
        sys.exit(1)

    # Generate all rows first, then insert in a single transaction.
    rows = [generate_one(user_id, months) for _ in range(count)]

    try:
        cur.executemany(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            rows,
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        conn.close()
        print(f"Insert failed, rolled back: {e}")
        sys.exit(1)

    # Summary stats.
    dates = [row[3] for row in rows]
    min_date, max_date = min(dates), max(dates)

    # Fetch the inserted rows back so we can sample real ids.
    cur.execute(
        "SELECT id, amount, category, date, description FROM expenses "
        "WHERE user_id = ? ORDER BY id DESC LIMIT 5",
        (user_id,),
    )
    sample = cur.fetchall()
    conn.close()

    print(f"\nInserted {count} expenses for user {user_id}.")
    print(f"Date range: {min_date} to {max_date}")
    print(f"Sample (most recent 5):")
    for row in sample:
        print(f"  id={row['id']}  {row['date']}  ₹{row['amount']:>7.2f}  "
              f"{row['category']:<14} {row['description']}")


if __name__ == "__main__":
    main()
