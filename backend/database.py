
import os
import psycopg
from psycopg.rows import dict_row

DATABASE_URL = os.getenv("DATABASE_URL")


def get_connection():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not configured")

    return psycopg.connect(
        DATABASE_URL,
        row_factory=dict_row,
        sslmode="require"
    )


def init_db():
    connection = get_connection()

    statements = [
        """
        CREATE TABLE IF NOT EXISTS students (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            eligible INTEGER NOT NULL DEFAULT 0
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS interviewers (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL
                CHECK(role IN ('student', 'interviewer', 'admin')),
            active INTEGER NOT NULL DEFAULT 1
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS slots (
            id TEXT PRIMARY KEY,
            interviewer_id TEXT NOT NULL,
            start_at TEXT NOT NULL,
            duration INTEGER NOT NULL DEFAULT 30,
            status TEXT NOT NULL DEFAULT 'Open'
                CHECK(status IN ('Open', 'Booked', 'Blocked')),
            FOREIGN KEY(interviewer_id) REFERENCES interviewers(id),
            UNIQUE(interviewer_id, start_at)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS bookings (
            id TEXT PRIMARY KEY,
            student_id TEXT NOT NULL,
            slot_id TEXT NOT NULL UNIQUE,
            status TEXT NOT NULL DEFAULT 'Booked'
                CHECK(status IN ('Booked', 'Cancelled', 'Completed')),
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(student_id) REFERENCES students(id),
            FOREIGN KEY(slot_id) REFERENCES slots(id)
        )
        """,
        """
        CREATE UNIQUE INDEX IF NOT EXISTS
            one_active_booking_per_student
        ON bookings(student_id)
        WHERE status = 'Booked'
        """,
        """
        CREATE TABLE IF NOT EXISTS interview_results (
            id TEXT PRIMARY KEY,
            booking_id TEXT NOT NULL UNIQUE,
            result TEXT NOT NULL
                CHECK(result IN ('Pass', 'Fail', 'Retake')),
            feedback TEXT DEFAULT '',
            recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(booking_id) REFERENCES bookings(id)
        )
        """
    ]

    try:
        with connection.cursor() as cursor:
            for statement in statements:
                cursor.execute(statement)

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


if __name__ == "__main__":
    init_db()
    print("GRIT PostgreSQL database initialized successfully!")
