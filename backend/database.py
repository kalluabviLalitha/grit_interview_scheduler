
import sqlite3
from pathlib import Path

DATABASE_PATH = Path(__file__).with_name("grit.db")


def get_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db():
    connection = get_connection()

    connection.executescript("""
    CREATE TABLE IF NOT EXISTS students (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        eligible INTEGER NOT NULL DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS interviewers (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE
    );

    CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL
        CHECK(role IN ('student', 'interviewer', 'admin')),
    active INTEGER NOT NULL DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS slots (
        id TEXT PRIMARY KEY,
        interviewer_id TEXT NOT NULL,
        start_at TEXT NOT NULL,
        duration INTEGER NOT NULL DEFAULT 30,
        status TEXT NOT NULL DEFAULT 'Open'
            CHECK(status IN ('Open', 'Booked', 'Blocked')),
        FOREIGN KEY(interviewer_id) REFERENCES interviewers(id),
        UNIQUE(interviewer_id, start_at)
    );

    CREATE TABLE IF NOT EXISTS bookings (
        id TEXT PRIMARY KEY,
        student_id TEXT NOT NULL,
        slot_id TEXT NOT NULL UNIQUE,
        status TEXT NOT NULL DEFAULT 'Booked'
            CHECK(status IN ('Booked', 'Cancelled', 'Completed')),
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(student_id) REFERENCES students(id),
        FOREIGN KEY(slot_id) REFERENCES slots(id)
    );

    CREATE UNIQUE INDEX IF NOT EXISTS
    one_active_booking_per_student
    ON bookings(student_id)
    WHERE status = 'Booked';

    CREATE TABLE IF NOT EXISTS interview_results (
        id TEXT PRIMARY KEY,
        booking_id TEXT NOT NULL UNIQUE,
        result TEXT NOT NULL
            CHECK(result IN ('Pass', 'Fail', 'Retake')),
        feedback TEXT DEFAULT '',
        recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(booking_id) REFERENCES bookings(id)
    );
    """)

    connection.commit()
    connection.close()


if __name__ == "__main__":
    init_db()
    print("GRIT database created successfully!")
