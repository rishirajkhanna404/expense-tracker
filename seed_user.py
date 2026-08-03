"""Seed a single realistic Indian user into spendwise.db.

Generates a random Indian first + last name, derives an email with a
2-3 digit numeric suffix, and inserts the user via the same get_db()
pattern used by database/db.py. Regenerates until the email is unique.
"""
import random
from datetime import datetime

from werkzeug.security import generate_password_hash

from database.db import get_db, init_db


# Common Indian first + last names spanning regions.
FIRST_NAMES = [
    "Rahul", "Priya", "Amit", "Sneha", "Vikram", "Anjali",
    "Arjun", "Pooja", "Rohan", "Kavya", "Aditya", "Neha",
    "Karthik", "Meera", "Sandeep", "Divya", "Rohit", "Ananya",
    "Suresh", "Lakshmi", "Manoj", "Shreya", "Naveen", "Ishita",
]
LAST_NAMES = [
    "Sharma", "Verma", "Patel", "Reddy", "Iyer", "Nair",
    "Gupta", "Khan", "Joshi", "Mehta", "Bose", "Rao",
    "Chatterjee", "Banerjee", "Kulkarni", "Pillai", "Menon", "Saxena",
]


def generate_user():
    """Return (first, last, email) for a random Indian user."""
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    suffix = random.randint(10, 999)
    email = f"{first.lower()}.{last.lower()}{suffix}@gmail.com"
    return first, last, email


def main():
    # Ensure the schema exists before inserting.
    init_db()

    conn = get_db()
    cur = conn.cursor()

    # Regenerate until the email is unique in the users table.
    while True:
        first, last, email = generate_user()
        cur.execute("SELECT 1 FROM users WHERE email = ?", (email,))
        if cur.fetchone() is None:
            break

    password_hash = generate_password_hash("password123")
    cur.execute(
        "INSERT INTO users (name, email, password_hash, created_at) "
        "VALUES (?, ?, ?, ?)",
        (
            f"{first} {last}",
            email,
            password_hash,
            datetime.now().isoformat(sep=" ", timespec="seconds"),
        ),
    )
    conn.commit()

    user_id = cur.lastrowid
    full_name = f"{first} {last}"
    conn.close()

    print("Seeded user:")
    print(f"  id:    {user_id}")
    print(f"  name:  {full_name}")
    print(f"  email: {email}")


if __name__ == "__main__":
    main()
