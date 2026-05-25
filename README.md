# Sciqus — Student & Course Management System

> **Sciqus Technical Assessment** | Flask + PostgreSQL + Vanilla JS

A full-stack REST API application for managing students and courses, built with Python Flask and PostgreSQL. Features JWT authentication, role-based access control (Admin/Student), stored procedures, and a responsive frontend dashboard.

---

## 📌 Project Overview

Sciqus is a Student and Course Management System that provides:

- **Authentication**: Register and login with JWT tokens
- **Role-Based Access**: Admins manage everything; students view their own data
- **Course Management**: Create, read, and manage courses
- **Student Management**: Add, update, delete, and view students with course info
- **Stored Procedures**: PostgreSQL functions for safe data operations
- **Frontend Dashboard**: Responsive UI with carousel, stats, modals, and live API integration

---

## 🛠 Tech Stack

| Layer         | Technology                    |
|---------------|-------------------------------|
| Backend       | Python 3.x + Flask            |
| Database      | PostgreSQL 14+                |
| Auth          | Flask-JWT-Extended (JWT)      |
| Passwords     | Flask-Bcrypt (bcrypt)         |
| DB Driver     | psycopg2-binary (raw SQL)     |
| CORS          | Flask-CORS                    |
| Config        | python-dotenv (.env)          |
| Frontend      | HTML5 + CSS3 + Vanilla JS     |
| Fonts         | Google Fonts — Poppins        |

---

## ✅ Prerequisites

Make sure the following are installed:

- Python 3.8+ → `python --version`
- pip → `pip --version`
- PostgreSQL 14+ → `psql --version`
- Git (optional)

---

## 📁 Project Structure

```
sciqus-assessment/
│
├── backend/
│   ├── app.py               ← Main Flask application
│   ├── schema.sql           ← PostgreSQL schema + stored procedures
│   ├── requirements.txt     ← pip dependencies
│   ├── .env.example         ← Template for environment variables
│   └── .env                 ← Your actual credentials (do not commit!)
│
├── frontend/
│   ├── index.html           ← Dashboard + Login page
│   ├── css/
│   │   └── style.css        ← All styles (dark theme, purple palette)
│   └── js/
│       └── script.js        ← All JavaScript (API calls, UI logic)
│
└── README.md
```

---

## 🚀 Setup Instructions

### Step 1 — Create the PostgreSQL Database

Open your terminal and run:

```bash
# Connect to PostgreSQL (replace 'postgres' with your username if different)
psql -U postgres

# Inside psql shell, create the database:
CREATE DATABASE sciqus_db;

# Exit psql
\q
```

### Step 2 — Run the Schema SQL

```bash
# From the project root:
psql -U postgres -d sciqus_db -f backend/schema.sql
```

This creates:
- `courses` table
- `users` table (with default admin user)
- 3 stored procedures (`insert_student`, `update_student`, `delete_student`)

### Step 3 — Configure Environment Variables

```bash
# Copy the example file
cp backend/.env.example backend/.env

# Edit .env with your PostgreSQL credentials:
# (use Notepad on Windows, nano/vim on Linux/Mac)
notepad backend/.env
```

Your `.env` should look like:
```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=sciqus_db
DB_USER=postgres
DB_PASSWORD=your_actual_password
JWT_SECRET_KEY=some-long-random-secret-key
```

### Step 4 — Set Up Python Virtual Environment

```bash
# From the project root
python -m venv venv

# Activate (Windows):
venv\Scripts\activate

# Activate (Mac/Linux):
source venv/bin/activate
```

### Step 5 — Install Dependencies

```bash
pip install -r backend/requirements.txt
```

### Step 6 — Run the Flask App

```bash
# Make sure venv is activated, then:
python backend/app.py
```

You should see:
```
 * Running on http://0.0.0.0:5000
 * Debug mode: on
```

### Step 7 — Open the Frontend

Open `frontend/index.html` directly in your browser, **or** navigate to:
```
http://localhost:5000
```

**Default Admin Login:**
- Email: `admin@sciqus.com`
- Password: `admin123`

---

## 📡 API Endpoints

> All protected routes require: `Authorization: Bearer <your_jwt_token>` header

### Authentication

| Method | Endpoint          | Auth Required | Description                |
|--------|-------------------|---------------|----------------------------|
| POST   | `/auth/register`  | No            | Register a new user        |
| POST   | `/auth/login`     | No            | Login and get JWT token    |

**POST /auth/register** — Request Body:
```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "password": "securepassword",
  "role": "student"
}
```
Response `201`:
```json
{ "msg": "Registered successfully" }
```

**POST /auth/login** — Request Body:
```json
{
  "email": "admin@sciqus.com",
  "password": "admin123"
}
```
Response `200`:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "role": "admin"
}
```

---

### Courses

| Method | Endpoint                         | Auth     | Role     | Description                  |
|--------|----------------------------------|----------|----------|------------------------------|
| POST   | `/courses`                       | JWT      | Admin    | Create a new course          |
| GET    | `/courses`                       | JWT      | Any      | List all courses             |
| GET    | `/courses/<id>`                  | JWT      | Any      | Get a single course          |
| GET    | `/courses/<id>/students`         | JWT      | Admin    | Get all students in a course |

**POST /courses** — Request Body:
```json
{
  "course_name": "Full Stack Web Development",
  "course_code": "FSWD202",
  "course_duration": 6
}
```
Response `201`:
```json
{ "msg": "Course created", "course_id": 1 }
```

**GET /courses** — Response `200`:
```json
[
  {
    "course_id": 1,
    "course_name": "Full Stack Web Development",
    "course_code": "FSWD202",
    "course_duration": 6
  }
]
```

---

### Students

| Method | Endpoint               | Auth | Role              | Description                         |
|--------|------------------------|------|-------------------|-------------------------------------|
| POST   | `/students`            | JWT  | Admin             | Add a new student (via procedure)   |
| GET    | `/students`            | JWT  | Admin / Student   | List students (role-filtered)       |
| GET    | `/students/<id>`       | JWT  | Admin / Own self  | Get a student's details             |
| PUT    | `/students/<id>`       | JWT  | Admin             | Update student (via procedure)      |
| DELETE | `/students/<id>`       | JWT  | Admin             | Delete student (via procedure)      |

**POST /students** — Request Body:
```json
{
  "name": "Priya Patel",
  "email": "priya@example.com",
  "password": "student123",
  "course_id": 1
}
```
Response `201`:
```json
{ "msg": "Student added", "student_id": 2 }
```

**GET /students** — Response `200`:
```json
[
  {
    "user_id": 2,
    "name": "Priya Patel",
    "email": "priya@example.com",
    "created_at": "2024-01-15 10:30:00",
    "course": {
      "course_id": 1,
      "course_name": "Full Stack Web Development",
      "course_code": "FSWD202",
      "course_duration": 6
    }
  }
]
```

**PUT /students/<id>** — Request Body (all fields optional):
```json
{
  "name": "Priya Sharma",
  "email": "priya.new@example.com",
  "course_id": 2
}
```
Response `200`:
```json
{ "msg": "Student updated" }
```

**DELETE /students/<id>** — Response `200`:
```json
{ "msg": "Student deleted" }
```

---

## 🧪 Testing with Postman

### Step-by-Step Guide

**1. Import Collection (or create manually)**

Open Postman and create a new Collection called "Sciqus API".

**2. Set Base URL Variable**

In Collection settings → Variables:
- Variable: `BASE_URL`
- Value: `http://localhost:5000`

**3. Login First**

- Method: `POST`
- URL: `{{BASE_URL}}/auth/login`
- Body → raw → JSON:
  ```json
  { "email": "admin@sciqus.com", "password": "admin123" }
  ```
- Copy the `access_token` from the response.

**4. Set Authorization**

For all protected requests:
- Tab: Authorization → Bearer Token
- Token: paste your `access_token`

**Or use a Collection-level script** to auto-save the token:

In your Login request → Tests tab, add:
```javascript
const data = pm.response.json();
pm.collectionVariables.set("TOKEN", data.access_token);
```

Then in all other requests, set Header:
- `Authorization`: `Bearer {{TOKEN}}`

**5. Test Sequence (recommended order)**

```
1. POST /auth/login          → Get token
2. POST /courses             → Create a course (note course_id)
3. GET  /courses             → Verify course was created
4. POST /students            → Add a student to the course
5. GET  /students            → View all students
6. GET  /students/<id>       → View specific student
7. PUT  /students/<id>       → Update student
8. GET  /courses/<id>/students → View all students in a course
9. DELETE /students/<id>     → Delete student
```

**6. Expected HTTP Status Codes**

| Scenario                | Code |
|-------------------------|------|
| Success (read)          | 200  |
| Success (created)       | 201  |
| Bad input               | 400  |
| Wrong credentials       | 401  |
| Insufficient permission | 403  |
| Not found               | 404  |
| Duplicate email/code    | 409  |
| Server error            | 500  |

---

## 🗄 Database Schema

```
┌─────────────────────────────────────────────┐
│                   COURSES                    │
├──────────────┬───────────────┬──────────────┤
│  course_id   │  SERIAL PK    │ Auto-increment│
│  course_name │  VARCHAR(255) │ NOT NULL      │
│  course_code │  VARCHAR(50)  │ UNIQUE        │
│ course_duration│ INTEGER     │ months        │
└──────────────┴───────────────┴──────────────┘
                        │
                        │ FK: course_id (ON DELETE SET NULL)
                        │
┌─────────────────────────────────────────────┐
│                    USERS                     │
├──────────────┬───────────────┬──────────────┤
│  user_id     │  SERIAL PK    │ Auto-increment│
│  name        │  VARCHAR(255) │ NOT NULL      │
│  email       │  VARCHAR(255) │ UNIQUE        │
│ password_hash│  VARCHAR(255) │ bcrypt hash   │
│  role        │  VARCHAR(20)  │ admin|student │
│  course_id   │  INTEGER      │ FK → courses  │
│  created_at  │  TIMESTAMP    │ DEFAULT NOW() │
└──────────────┴───────────────┴──────────────┘
```

**Relationships:**
- One course → many students (one-to-many)
- One student → one course (or NULL if unenrolled)
- If a course is deleted, enrolled students get `course_id = NULL` (SET NULL)

---

## 🔧 Stored Procedures

Three PostgreSQL functions handle critical data operations:

### 1. `insert_student(name, email, password_hash, course_id)`
- **Purpose**: Validates that `course_id` exists, then inserts a new student
- **Returns**: The new `user_id` (INTEGER)
- **Called by**: `POST /students`
- **Raises exception**: If course_id doesn't exist

### 2. `update_student(user_id, name, email, course_id)`
- **Purpose**: Updates student fields using `COALESCE` (keeps old value if NULL passed)
- **Returns**: VOID
- **Called by**: `PUT /students/<id>`
- **Raises exception**: If student_id not found, or new course_id doesn't exist

### 3. `delete_student(user_id)`
- **Purpose**: Confirms the student exists, then deletes them
- **Returns**: VOID
- **Called by**: `DELETE /students/<id>`
- **Raises exception**: If student_id not found

**Why stored procedures?**
- Centralize business logic in the database layer
- Prevent invalid states (e.g., enrolling in a non-existent course)
- Demonstrate PL/pgSQL skills clearly
- Can be called from any client, not just Flask

---

## 🎨 Running the Frontend

The frontend is served by Flask at `http://localhost:5000/`.

Or open `frontend/index.html` directly in your browser (note: API calls need CORS, which Flask-CORS handles).

**Features:**
- 🔐 Login page with JWT auth
- 📊 Live stats (students, courses, enrollments)
- 🎠 Auto-advancing banner carousel
- 📚 Horizontal course slider
- ➕ Modals to add students & courses (calls API)
- ⚡ Animated activity feed
- 📱 Fully responsive (hamburger menu on mobile)

---

## 🔐 Security Notes

- Passwords are **never stored in plain text** — always bcrypt-hashed
- All SQL queries use **parameterized queries** (no string interpolation) to prevent SQL injection
- JWT tokens expire after the configured time (default: 1 hour)
- The `.env` file contains secrets — **never commit it to version control**
- Add `.env` to your `.gitignore` file

---

*Built for the Sciqus Technical Internship Assessment*
