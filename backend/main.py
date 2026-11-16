
import os
import secrets
from uuid import uuid4
from typing import Optional

import psycopg
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import get_connection, init_db

from auth import (
    verify_password,
    hash_password,
    create_access_token,
    get_current_user,
    require_role,
)


app = FastAPI(
    title="GRIT Interview Scheduler",
    description="Student interview scheduling API",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()


# ---------- Request models ----------

class StudentInput(BaseModel):
    name: str
    email: str
    eligible: bool = False


class InterviewerInput(BaseModel):
    name: str
    email: str


class SlotInput(BaseModel):
    interviewer_id: str
    start_at: str
    duration: int = 30


class BookingInput(BaseModel):
    student_id: Optional[str] = None
    slot_id: str


class ResultInput(BaseModel):
    result: str
    feedback: str = ""


class LoginInput(BaseModel):
    email: str
    password: str


class AdminSetupInput(BaseModel):
    name: str
    email: str
    password: str
    setup_key: str


# ---------- Helpers ----------

def fetch_all(query, params=()):
    connection = get_connection()
    try:
        rows = connection.execute(query, params).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


# ---------- One-time admin setup ----------

@app.post("/setup/admin")
def setup_admin(data: AdminSetupInput):
    setup_key = os.getenv("ADMIN_SETUP_KEY")

    if not setup_key:
        raise HTTPException(
            503,
            "Admin setup is not configured",
        )

    if not secrets.compare_digest(data.setup_key, setup_key):
        raise HTTPException(
            403,
            "Invalid setup key",
        )

    if len(data.password) < 12:
        raise HTTPException(
            400,
            "Admin password must contain at least 12 characters",
        )

    connection = get_connection()

    try:
        existing_admin = connection.execute(
            "SELECT id FROM users WHERE role = 'admin' LIMIT 1"
        ).fetchone()

        if existing_admin:
            raise HTTPException(
                409,
                "An admin account already exists",
            )

        user_id = "USR-" + uuid4().hex[:8].upper()

        connection.execute(
            """
            INSERT INTO users
            (id, name, email, password_hash, role, active)
            VALUES (%s, %s, %s, %s, 'admin', 1)
            """,
            (
                user_id,
                data.name.strip(),
                data.email.lower().strip(),
                hash_password(data.password),
            ),
        )

        connection.commit()

        return {
            "message": "Admin account created successfully",
            "email": data.email.lower().strip(),
        }

    except psycopg.IntegrityError:
        connection.rollback()
        raise HTTPException(
            409,
            "An account with this email already exists",
        )

    finally:
        connection.close()


# ---------- Home and health ----------

@app.get("/")
def home():
    return {
        "message": "Welcome to GRIT Interview Scheduler API"
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


# ---------- Students ----------

@app.post("/students")
def create_student(
    data: StudentInput,
    user=Depends(require_role("admin")),
):
    connection = get_connection()

    try:
        student_id = "STU-" + uuid4().hex[:8].upper()

        connection.execute(
            """
            INSERT INTO students (id, name, email, eligible)
            VALUES (%s, %s, %s, %s)
            """,
            (
                student_id,
                data.name,
                data.email.lower().strip(),
                int(data.eligible),
            ),
        )

        connection.commit()

        return {
            "message": "Student created",
            "student_id": student_id,
        }

    except psycopg.IntegrityError:
        connection.rollback()
        raise HTTPException(409, "Email already exists")

    finally:
        connection.close()


@app.get("/students")
def get_students(user=Depends(require_role("admin"))):
    return fetch_all(
        "SELECT * FROM students ORDER BY name"
    )


# ---------- Interviewers ----------

@app.post("/interviewers")
def create_interviewer(
    data: InterviewerInput,
    user=Depends(require_role("admin")),
):
    connection = get_connection()

    try:
        interviewer_id = "INT-" + uuid4().hex[:8].upper()

        connection.execute(
            """
            INSERT INTO interviewers (id, name, email)
            VALUES (%s, %s, %s)
            """,
            (
                interviewer_id,
                data.name,
                data.email.lower().strip(),
            ),
        )

        connection.commit()

        return {
            "message": "Interviewer created",
            "interviewer_id": interviewer_id,
        }

    except psycopg.IntegrityError:
        connection.rollback()
        raise HTTPException(409, "Email already exists")

    finally:
        connection.close()


@app.get("/interviewers")
def get_interviewers(user=Depends(require_role("admin"))):
    return fetch_all(
        "SELECT * FROM interviewers ORDER BY name"
    )


# ---------- Interview slots ----------

@app.post("/slots")
def create_slot(
    data: SlotInput,
    user=Depends(get_current_user),
):
    if user["role"] not in ("interviewer", "admin"):
        raise HTTPException(
            403,
            "Only interviewers or admins can create slots",
        )

    if data.duration not in (30, 45, 60):
        raise HTTPException(
            400,
            "Duration must be 30, 45 or 60 minutes",
        )

    if (
        user["role"] == "interviewer"
        and data.interviewer_id != user["id"]
    ):
        raise HTTPException(
            403,
            "You can create slots only for your own account",
        )

    connection = get_connection()

    try:
        interviewer = connection.execute(
            "SELECT id FROM interviewers WHERE id = %s",
            (data.interviewer_id,),
        ).fetchone()

        if not interviewer:
            raise HTTPException(404, "Interviewer not found")

        slot_id = "SL-" + uuid4().hex[:8].upper()

        connection.execute(
            """
            INSERT INTO slots
            (id, interviewer_id, start_at, duration)
            VALUES (%s, %s, %s, %s)
            """,
            (
                slot_id,
                data.interviewer_id,
                data.start_at,
                data.duration,
            ),
        )

        connection.commit()

        return {
            "message": "Slot created",
            "slot_id": slot_id,
        }

    except psycopg.IntegrityError:
        connection.rollback()
        raise HTTPException(409, "Slot already exists")

    finally:
        connection.close()


@app.get("/slots")
def get_slots(
    status: str = "Open",
    user=Depends(get_current_user),
):
    connection = get_connection()

    try:
        if user["role"] == "student":
            rows = connection.execute(
                """
                SELECT slots.*,
                       interviewers.name AS interviewer_name
                FROM slots
                JOIN interviewers
                    ON slots.interviewer_id = interviewers.id
                WHERE slots.status = 'Open'
                ORDER BY slots.start_at
                """
            ).fetchall()

        elif user["role"] == "interviewer":
            rows = connection.execute(
                """
                SELECT slots.*,
                       interviewers.name AS interviewer_name
                FROM slots
                JOIN interviewers
                    ON slots.interviewer_id = interviewers.id
                WHERE slots.interviewer_id = %s
                  AND slots.status = %s
                ORDER BY slots.start_at
                """,
                (user["id"], status),
            ).fetchall()

        elif user["role"] == "admin":
            rows = connection.execute(
                """
                SELECT slots.*,
                       interviewers.name AS interviewer_name
                FROM slots
                JOIN interviewers
                    ON slots.interviewer_id = interviewers.id
                WHERE slots.status = %s
                ORDER BY slots.start_at
                """,
                (status,),
            ).fetchall()

        else:
            raise HTTPException(403, "Role is not permitted")

        return [dict(row) for row in rows]

    finally:
        connection.close()


@app.get("/student/available-slots")
def get_student_available_slots(
    user=Depends(require_role("student")),
):
    return fetch_all(
        """
        SELECT slots.id,
               slots.start_at,
               slots.duration,
               slots.interviewer_id,
               interviewers.name AS interviewer_name
        FROM slots
        JOIN interviewers
            ON slots.interviewer_id = interviewers.id
        WHERE slots.status = 'Open'
        ORDER BY slots.start_at
        """
    )


# ---------- Bookings ----------

@app.post("/bookings")
def create_booking(
    data: BookingInput,
    user=Depends(require_role("student")),
):
    student_id = user["id"]
    connection = get_connection()

    try:
        with connection.transaction():
            student = connection.execute(
                """
                SELECT * FROM students
                WHERE id = %s
                """,
                (student_id,),
            ).fetchone()

            if not student:
                raise HTTPException(
                    404,
                    "Student profile not found for this account",
                )

            if not student["eligible"]:
                raise HTTPException(
                    403,
                    "Student is not eligible",
                )

            existing = connection.execute(
                """
                SELECT id FROM bookings
                WHERE student_id = %s
                  AND status = 'Booked'
                """,
                (student_id,),
            ).fetchone()

            if existing:
                raise HTTPException(
                    409,
                    "Student already has an active booking",
                )

            slot = connection.execute(
                """
                SELECT * FROM slots
                WHERE id = %s
                FOR UPDATE
                """,
                (data.slot_id,),
            ).fetchone()

            if not slot:
                raise HTTPException(404, "Slot not found")

            if slot["status"] != "Open":
                raise HTTPException(
                    409,
                    "Slot is no longer available",
                )

            booking_id = "BK-" + uuid4().hex[:8].upper()

            connection.execute(
                """
                INSERT INTO bookings
                (id, student_id, slot_id, status)
                VALUES (%s, %s, %s, 'Booked')
                """,
                (booking_id, student_id, data.slot_id),
            )

            connection.execute(
                """
                UPDATE slots
                SET status = 'Booked'
                WHERE id = %s
                """,
                (data.slot_id,),
            )

        return {
            "message": "Interview booked successfully",
            "booking_id": booking_id,
        }

    except psycopg.IntegrityError:
        connection.rollback()
        raise HTTPException(
            409,
            "Booking conflict. Try another slot.",
        )

    finally:
        connection.close()


@app.get("/bookings")
def get_bookings(user=Depends(require_role("admin"))):
    return fetch_all(
        """
        SELECT bookings.*,
               students.name AS student_name,
               slots.start_at,
               interviewers.name AS interviewer_name,
               interview_results.result,
               interview_results.feedback
        FROM bookings
        JOIN students
            ON bookings.student_id = students.id
        JOIN slots
            ON bookings.slot_id = slots.id
        JOIN interviewers
            ON slots.interviewer_id = interviewers.id
        LEFT JOIN interview_results
            ON bookings.id = interview_results.booking_id
        ORDER BY bookings.created_at DESC
        """
    )


# ---------- Cancellation ----------

@app.post("/bookings/{booking_id}/cancel")
def cancel_booking(
    booking_id: str,
    user=Depends(get_current_user),
):
    if user["role"] not in ("student", "admin"):
        raise HTTPException(
            403,
            "Only the booking student or an admin can cancel",
        )

    connection = get_connection()

    try:
        with connection.transaction():
            booking = connection.execute(
                """
                SELECT * FROM bookings
                WHERE id = %s
                  AND status = 'Booked'
                FOR UPDATE
                """,
                (booking_id,),
            ).fetchone()

            if not booking:
                raise HTTPException(
                    404,
                    "Active booking not found",
                )

            if (
                user["role"] == "student"
                and booking["student_id"] != user["id"]
            ):
                raise HTTPException(
                    403,
                    "You can cancel only your own booking",
                )

            connection.execute(
                """
                UPDATE bookings
                SET status = 'Cancelled'
                WHERE id = %s
                """,
                (booking_id,),
            )

            connection.execute(
                """
                UPDATE slots
                SET status = 'Open'
                WHERE id = %s
                """,
                (booking["slot_id"],),
            )

        return {
            "message": "Booking cancelled successfully"
        }

    finally:
        connection.close()


# ---------- Interview results ----------

@app.post("/bookings/{booking_id}/result")
def record_result(
    booking_id: str,
    data: ResultInput,
    user=Depends(get_current_user),
):
    if user["role"] not in ("interviewer", "admin"):
        raise HTTPException(
            403,
            "Only the assigned interviewer or an admin can record results",
        )

    if data.result not in ("Pass", "Fail", "Retake"):
        raise HTTPException(
            400,
            "Result must be Pass, Fail or Retake",
        )

    connection = get_connection()

    try:
        with connection.transaction():
            booking = connection.execute(
                """
                SELECT bookings.*,
                       slots.interviewer_id
                FROM bookings
                JOIN slots
                    ON bookings.slot_id = slots.id
                WHERE bookings.id = %s
                FOR UPDATE OF bookings
                """,
                (booking_id,),
            ).fetchone()

            if not booking or booking["status"] != "Booked":
                raise HTTPException(
                    404,
                    "Active booking not found",
                )

            if (
                user["role"] == "interviewer"
                and booking["interviewer_id"] != user["id"]
            ):
                raise HTTPException(
                    403,
                    "You can record results only for your assigned interviews",
                )

            result_id = "RES-" + uuid4().hex[:8].upper()

            connection.execute(
                """
                INSERT INTO interview_results
                (id, booking_id, result, feedback)
                VALUES (%s, %s, %s, %s)
                """,
                (
                    result_id,
                    booking_id,
                    data.result,
                    data.feedback,
                ),
            )

            connection.execute(
                """
                UPDATE bookings
                SET status = 'Completed'
                WHERE id = %s
                """,
                (booking_id,),
            )

        return {
            "message": "Interview result saved",
            "result": data.result,
        }

    except psycopg.IntegrityError:
        connection.rollback()
        raise HTTPException(
            409,
            "Result already recorded",
        )

    finally:
        connection.close()


# ---------- Authentication ----------

@app.post("/auth/login")
def login(data: LoginInput):
    connection = get_connection()

    try:
        user = connection.execute(
            """
            SELECT id,
                   name,
                   email,
                   password_hash,
                   role,
                   active
            FROM users
            WHERE email = %s
            """,
            (data.email.lower().strip(),),
        ).fetchone()

    finally:
        connection.close()

    if not user or not verify_password(
        data.password,
        user["password_hash"],
    ):
        raise HTTPException(
            401,
            "Incorrect email or password",
        )

    if not user["active"]:
        raise HTTPException(
            403,
            "Account is inactive",
        )

    token = create_access_token(
        user["id"],
        user["role"],
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
        },
    }


@app.get("/auth/me")
def my_profile(user=Depends(get_current_user)):
    return user


# ---------- Protected dashboards ----------

@app.get("/dashboard/student")
def student_dashboard(
    user=Depends(require_role("student")),
):
    return {
        "message": "Welcome to your student dashboard",
        "user": user,
    }


@app.get("/dashboard/interviewer")
def interviewer_dashboard(
    user=Depends(require_role("interviewer")),
):
    return {
        "message": "Welcome to your interviewer dashboard",
        "user": user,
    }


@app.get("/dashboard/admin")
def admin_dashboard(
    user=Depends(require_role("admin")),
):
    return {
        "message": "Welcome to the GRIT admin dashboard",
        "user": user,
    }


# ---------- Personal bookings ----------

@app.get("/me/bookings")
def my_bookings(user=Depends(get_current_user)):
    connection = get_connection()

    try:
        if user["role"] == "student":
            rows = connection.execute(
                """
                SELECT bookings.id AS booking_id,
                       bookings.status,
                       slots.start_at,
                       slots.duration,
                       interviewers.name AS interviewer_name,
                       interview_results.result,
                       interview_results.feedback
                FROM bookings
                JOIN slots
                    ON bookings.slot_id = slots.id
                JOIN interviewers
                    ON slots.interviewer_id = interviewers.id
                LEFT JOIN interview_results
                    ON bookings.id = interview_results.booking_id
                WHERE bookings.student_id = %s
                ORDER BY slots.start_at DESC
                """,
                (user["id"],),
            ).fetchall()

        elif user["role"] == "interviewer":
            rows = connection.execute(
                """
                SELECT bookings.id AS booking_id,
                       bookings.status,
                       students.name AS student_name,
                       slots.start_at,
                       slots.duration,
                       interview_results.result,
                       interview_results.feedback
                FROM bookings
                JOIN slots
                    ON bookings.slot_id = slots.id
                JOIN students
                    ON bookings.student_id = students.id
                LEFT JOIN interview_results
                    ON bookings.id = interview_results.booking_id
                WHERE slots.interviewer_id = %s
                ORDER BY slots.start_at DESC
                """,
                (user["id"],),
            ).fetchall()

        elif user["role"] == "admin":
            rows = connection.execute(
                """
                SELECT bookings.id AS booking_id,
                       bookings.status,
                       students.name AS student_name,
                       slots.start_at,
                       interviewers.name AS interviewer_name,
                       interview_results.result
                FROM bookings
                JOIN students
                    ON bookings.student_id = students.id
                JOIN slots
                    ON bookings.slot_id = slots.id
                JOIN interviewers
                    ON slots.interviewer_id = interviewers.id
                LEFT JOIN interview_results
                    ON bookings.id = interview_results.booking_id
                ORDER BY slots.start_at DESC
                """
            ).fetchall()

        else:
            raise HTTPException(
                403,
                "Role is not permitted",
            )

        return [dict(row) for row in rows]

    finally:
        connection.close()
