
import getpass
from uuid import uuid4

import psycopg

from database import get_connection, init_db
from auth import hash_password

print("\n=== GRIT Account Setup ===")

role = input(
    "Choose role (student/interviewer/admin): "
).strip().lower()

if role not in ["student", "interviewer", "admin"]:
    raise SystemExit("Invalid role.")

name = input("Enter full name: ").strip()
email = input("Enter email: ").strip().lower()
password = getpass.getpass("Enter password (minimum 12 characters): ")

if not name or "@" not in email:
    raise SystemExit("Enter a valid name and email.")

if len(password) < 12:
    raise SystemExit("Password must contain at least 12 characters.")

init_db()
connection = get_connection()

try:
    if role == "student":
        linked = connection.execute(
            "SELECT id, name FROM students WHERE email = %s",
            (email,)
        ).fetchone()

    elif role == "interviewer":
        linked = connection.execute(
            "SELECT id, name FROM interviewers WHERE email = %s",
            (email,)
        ).fetchone()

    else:
        linked = None

    if role in ["student", "interviewer"] and not linked:
        raise SystemExit(
            "No matching student/interviewer record found. "
            "Create that record first."
        )

    user_id = (
        linked["id"]
        if linked
        else "USR-" + uuid4().hex[:8].upper()
    )

    connection.execute(
        """
        INSERT INTO users
        (id, name, email, password_hash, role, active)
        VALUES (%s, %s, %s, %s, %s, 1)
        """,
        (user_id, name, email, hash_password(password), role)
    )

    connection.commit()

    print("\nAccount created successfully!")
    print("User ID:", user_id)
    print("Role:", role)

except psycopg.IntegrityError:
    connection.rollback()
    print("An account with this email or ID already exists.")

finally:
    connection.close()
