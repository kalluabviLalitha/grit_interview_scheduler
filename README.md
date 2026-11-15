# GRIT Interview Scheduling System

## 1. Project Overview

The GRIT Interview Scheduling System is a web-based application designed to simplify and manage the interview scheduling process between students and interviewers.

The system provides three types of user accounts:

- **Student:** Can view available interview slots, book interviews, view booking history, and cancel bookings.
- **Interviewer:** Can create interview slots, view assigned bookings, and record interview results and feedback.
- **Admin:** Can view and manage student, interviewer, and booking information.

The application uses authentication and role-based access control to ensure that users can access only the features permitted for their roles.

## 2. Technologies Used

### Backend
- Python
- FastAPI
- SQLite
- JWT Authentication
- Argon2 Password Hashing

### Frontend
- HTML
- CSS
- JavaScript

### Development Tools
- Visual Studio Code
- Swagger UI
- Python Virtual Environment

## 3. Project Folder Structure

```text
grit_interview_scheduler/
│
├── backend/
│   ├── .venv/
│   ├── auth.py
│   ├── create_user.py
│   ├── database.py
│   ├── grit.db
│   ├── main.py
│   └── requirements.txt
│
├── frontend/
│   ├── index.html
│   ├── login.html
│   ├── dashboard.html
│   ├── student.html
│   ├── interviewer.html
│   ├── admin.html
│   └── api.js
│
└── README.md
```

## 4. Backend Installation and Setup

### Step 1: Open the backend folder

Open the terminal in VS Code and navigate to the backend directory:

```powershell
cd backend
```

### Step 2: Activate the virtual environment

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks script execution, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Then activate the virtual environment again.

### Step 3: Set the secret key

```powershell
$env:GRIT_SECRET_KEY = python -c "import secrets; print(secrets.token_urlsafe(48))"
```

### Step 4: Install dependencies

```powershell
pip install -r requirements.txt
```

### Step 5: Start the backend server

```powershell
python -m uvicorn main:app --reload
```

The backend will run at:

http://127.0.0.1:8000

Swagger API documentation:

http://127.0.0.1:8000/docs

## 5. Frontend Setup

1. Open the `frontend` folder in Visual Studio Code.
2. Open `index.html` or `login.html` using the Live Server extension.
3. The application will open in your browser.
4. Ensure the backend server is running while using the frontend.

The frontend communicates with the backend at:

```text
http://127.0.0.1:8000
```

## 6. Application Features

### Student Module
- Student login and authentication.
- View available interview slots.
- Book an interview slot.
- View personal booking history.
- Cancel eligible bookings.

### Interviewer Module
- Interviewer login and authentication.
- Create interview slots.
- View assigned student bookings.
- Record interview results.
- Add interview feedback.

### Admin Module
- Admin login and authentication.
- View student information.
- View interviewer information.
- View booking information.

### Authentication and Security
- JWT-based authentication.
- Password hashing using Argon2.
- Role-based access control.
- Restricted access to protected API endpoints.

## 7. API Endpoints

| HTTP Method | Endpoint | Description |
|---|---|---|
| POST | `/auth/login` | User login |
| GET | `/auth/me` | Get logged-in user details |
| GET | `/students` | Retrieve student records |
| POST | `/students` | Create a student |
| GET | `/interviewers` | Retrieve interviewer records |
| POST | `/interviewers` | Create an interviewer |
| GET | `/slots` | Retrieve interview slots |
| POST | `/slots` | Create an interview slot |
| GET | `/student/available-slots` | Retrieve available slots for students |
| POST | `/bookings` | Book an interview |
| GET | `/bookings` | Retrieve all bookings |
| GET | `/me/bookings` | Retrieve personal bookings |
| POST | `/bookings/{id}/cancel` | Cancel a booking |
| POST | `/bookings/{id}/result` | Record interview results |

## 8. Testing and Verification

The following functionality and access-control checks were verified during development:

| Test Case | Expected Result | Status |
|---|---|---|
| Access protected endpoint without login | 401 Unauthorized | Passed |
| Student accesses admin-only student list | 403 Forbidden | Passed |
| Interviewer accesses admin-only student list | 403 Forbidden | Passed |
| Admin accesses student list | 200 OK | Passed |
| Admin accesses interviewer list | 200 OK | Passed |
| Student login and dashboard | Successful | Verified |
| Interviewer login and dashboard | Successful | Verified |
| Admin login and dashboard | Successful | Verified |
| Interview booking workflow | Booking created | Verified |
| Interview result workflow | Result recorded | Verified |

## 9. Conclusion

The GRIT Interview Scheduling System provides a centralized web-based platform for managing student interviews.

It simplifies interview slot creation, booking, cancellation, and interview result management while providing authentication and role-based access control.

The project demonstrates the integration of a FastAPI backend, SQLite database, and HTML, CSS, and JavaScript frontend to develop a functional interview scheduling application.