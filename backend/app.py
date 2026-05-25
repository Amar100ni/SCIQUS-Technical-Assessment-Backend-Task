# =============================================================
# Sciqus Student & Course Management System — Flask Backend
# =============================================================
# File: backend/app.py
# Description: Main Flask application with all API endpoints
#
# Dependencies (install via: pip install -r requirements.txt):
#   flask, flask-bcrypt, flask-jwt-extended, flask-cors,
#   psycopg2-binary, python-dotenv
#
# Run: python app.py
# =============================================================

import os
import psycopg2                          # PostgreSQL adapter (raw SQL, no ORM)
import psycopg2.extras                   # For DictCursor (returns rows as dicts)
from functools import wraps              # For creating decorators properly

from flask import Flask, request, jsonify, send_from_directory
from flask_bcrypt import Bcrypt          # Password hashing
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    jwt_required,
    get_jwt_identity
)
from flask_cors import CORS              # Allow cross-origin requests from frontend
from dotenv import load_dotenv           # Load environment variables from .env file

# ---------------------------------------------------------------
# Load environment variables from .env file
# ---------------------------------------------------------------
load_dotenv()

# ---------------------------------------------------------------
# Initialize Flask App
# ---------------------------------------------------------------
app = Flask(
    __name__,
    static_folder='../frontend',     # Serve frontend static files
    template_folder='../frontend'
)

# ---------------------------------------------------------------
# App Configuration (values pulled from .env)
# ---------------------------------------------------------------
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'fallback-secret-change-me')

# ---------------------------------------------------------------
# Initialize Extensions
# ---------------------------------------------------------------
bcrypt = Bcrypt(app)
jwt    = JWTManager(app)
CORS(app)   # Allow all origins (restrict in production)


# =============================================================
# DATABASE CONNECTION HELPER
# =============================================================

def get_db_connection():
    """
    Creates and returns a new psycopg2 database connection.
    Reads credentials from environment variables (loaded from .env).
    Using DictCursor so rows are returned as dictionaries.
    """
    conn = psycopg2.connect(
        host     = os.getenv('DB_HOST',     'localhost'),
        port     = os.getenv('DB_PORT',     5432),
        dbname   = os.getenv('DB_NAME',     'sciqus_db'),
        user     = os.getenv('DB_USER',     'postgres'),
        password = os.getenv('DB_PASSWORD', '')
    )
    return conn


# =============================================================
# ROLE-BASED ACCESS DECORATOR
# =============================================================

def role_required(required_role):
    """
    A decorator factory that enforces role-based access control.
    Usage: @role_required('admin') or @role_required('student')

    How it works:
    1. Extracts user_id from the JWT token (via get_jwt_identity)
    2. Fetches the user's role from the database
    3. Compares with required_role — returns 403 if mismatch
    """
    def decorator(fn):
        @wraps(fn)            # Preserves the original function's name/docstring
        @jwt_required()       # Must have valid JWT before checking role
        def wrapper(*args, **kwargs):
            current_user_id = get_jwt_identity()  # Get user_id from JWT payload

            conn = None
            try:
                conn   = get_db_connection()
                cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

                # Fetch the role of the current user from DB
                cursor.execute(
                    "SELECT role FROM users WHERE user_id = %s",
                    (current_user_id,)
                )
                user = cursor.fetchone()

                # If user not found in DB (e.g., deleted after token issued)
                if not user:
                    return jsonify({"error": "User not found"}), 404

                # Check role: admin can access anything; student only their own role
                if user['role'] != required_role and user['role'] != 'admin':
                    return jsonify({"error": "Access forbidden: insufficient permissions"}), 403

                # Role check passed — call the actual endpoint function
                return fn(*args, **kwargs)

            except Exception as e:
                return jsonify({"error": f"Authorization error: {str(e)}"}), 500
            finally:
                if conn:
                    conn.close()

        return wrapper
    return decorator


# =============================================================
# AUTH ENDPOINTS
# =============================================================

@app.route('/auth/register', methods=['POST'])
def register():
    """
    POST /auth/register
    Registers a new user (admin or student).

    Request body (JSON):
        { "name": "...", "email": "...", "password": "...", "role": "student" }

    Returns:
        201: { "msg": "Registered successfully" }
        400: Validation error
        409: Email already exists
    """
    data = request.get_json()  # Parse JSON body

    # --- Input Validation ---
    required_fields = ['name', 'email', 'password']
    for field in required_fields:
        if not data or not data.get(field):
            return jsonify({"error": f"'{field}' is required"}), 400

    name     = data['name'].strip()
    email    = data['email'].strip().lower()
    password = data['password']
    role     = data.get('role', 'student')  # Default role is 'student'

    # Validate role value
    if role not in ('admin', 'student'):
        return jsonify({"error": "Role must be 'admin' or 'student'"}), 400

    # Hash the password using bcrypt (never store plain text passwords!)
    password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    conn = None
    try:
        conn   = get_db_connection()
        cursor = conn.cursor()

        # Insert new user into DB using parameterized query (safe from SQL injection)
        cursor.execute(
            """
            INSERT INTO users (name, email, password_hash, role)
            VALUES (%s, %s, %s, %s)
            """,
            (name, email, password_hash, role)
        )
        conn.commit()  # Commit the transaction
        return jsonify({"msg": "Registered successfully"}), 201

    except psycopg2.errors.UniqueViolation:
        # Email already exists in the database
        conn.rollback()
        return jsonify({"error": "Email already registered"}), 409

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": f"Registration failed: {str(e)}"}), 500

    finally:
        if conn:
            conn.close()


@app.route('/auth/login', methods=['POST'])
def login():
    """
    POST /auth/login
    Authenticates a user and returns a JWT access token.

    Request body (JSON):
        { "email": "...", "password": "..." }

    Returns:
        200: { "access_token": "...", "role": "admin/student" }
        400: Missing fields
        401: Invalid credentials
    """
    data = request.get_json()

    # --- Input Validation ---
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({"error": "Email and password are required"}), 400

    email    = data['email'].strip().lower()
    password = data['password']

    conn = None
    try:
        conn   = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # Fetch user by email
        cursor.execute(
            "SELECT user_id, password_hash, role FROM users WHERE email = %s",
            (email,)
        )
        user = cursor.fetchone()

        # Verify user exists and password matches
        if not user or not bcrypt.check_password_hash(user['password_hash'], password):
            return jsonify({"error": "Invalid email or password"}), 401

        # Create JWT token — identity is the user_id (stored as string in JWT)
        access_token = create_access_token(identity=str(user['user_id']))

        return jsonify({
            "access_token": access_token,
            "role":         user['role']
        }), 200

    except Exception as e:
        return jsonify({"error": f"Login failed: {str(e)}"}), 500

    finally:
        if conn:
            conn.close()


# =============================================================
# COURSE ENDPOINTS
# =============================================================

@app.route('/courses', methods=['POST'])
@role_required('admin')
def create_course():
    """
    POST /courses  [Admin only]
    Creates a new course.

    Request body (JSON):
        { "course_name": "...", "course_code": "...", "course_duration": 6 }

    Returns:
        201: { "msg": "Course created", "course_id": X }
        400: Validation error or duplicate code
    """
    data = request.get_json()

    # --- Input Validation ---
    required = ['course_name', 'course_code', 'course_duration']
    for field in required:
        if not data or data.get(field) is None:
            return jsonify({"error": f"'{field}' is required"}), 400

    course_name     = data['course_name'].strip()
    course_code     = data['course_code'].strip().upper()
    course_duration = data['course_duration']

    # Validate duration is a positive integer
    if not isinstance(course_duration, int) or course_duration <= 0:
        return jsonify({"error": "course_duration must be a positive integer (months)"}), 400

    conn = None
    try:
        conn   = get_db_connection()
        cursor = conn.cursor()

        # Insert course and return the generated course_id
        cursor.execute(
            """
            INSERT INTO courses (course_name, course_code, course_duration)
            VALUES (%s, %s, %s)
            RETURNING course_id
            """,
            (course_name, course_code, course_duration)
        )
        new_course_id = cursor.fetchone()[0]
        conn.commit()

        return jsonify({"msg": "Course created", "course_id": new_course_id}), 201

    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        return jsonify({"error": f"Course code '{course_code}' already exists"}), 409

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": f"Failed to create course: {str(e)}"}), 500

    finally:
        if conn:
            conn.close()


@app.route('/courses', methods=['GET'])
@jwt_required()
def get_all_courses():
    """
    GET /courses  [All logged-in users]
    Returns a list of all courses.
    """
    conn = None
    try:
        conn   = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cursor.execute(
            "SELECT course_id, course_name, course_code, course_duration FROM courses ORDER BY course_id"
        )
        courses = cursor.fetchall()

        # Convert rows (DictRow objects) to plain Python dicts for JSON serialization
        return jsonify([dict(c) for c in courses]), 200

    except Exception as e:
        return jsonify({"error": f"Failed to fetch courses: {str(e)}"}), 500

    finally:
        if conn:
            conn.close()


@app.route('/courses/<int:course_id>', methods=['GET'])
@jwt_required()
def get_course(course_id):
    """
    GET /courses/<course_id>  [All logged-in users]
    Returns details of a single course by ID.
    """
    conn = None
    try:
        conn   = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cursor.execute(
            "SELECT course_id, course_name, course_code, course_duration FROM courses WHERE course_id = %s",
            (course_id,)
        )
        course = cursor.fetchone()

        if not course:
            return jsonify({"error": f"Course with ID {course_id} not found"}), 404

        return jsonify(dict(course)), 200

    except Exception as e:
        return jsonify({"error": f"Failed to fetch course: {str(e)}"}), 500

    finally:
        if conn:
            conn.close()


@app.route('/courses/<int:course_id>/students', methods=['GET'])
@role_required('admin')
def get_students_by_course(course_id):
    """
    GET /courses/<course_id>/students  [Admin only]
    Returns all students enrolled in a specific course.
    """
    conn = None
    try:
        conn   = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # First verify the course exists
        cursor.execute("SELECT course_id FROM courses WHERE course_id = %s", (course_id,))
        if not cursor.fetchone():
            return jsonify({"error": f"Course with ID {course_id} not found"}), 404

        # Fetch all students in this course
        cursor.execute(
            """
            SELECT user_id, name, email, created_at
            FROM users
            WHERE course_id = %s AND role = 'student'
            ORDER BY name
            """,
            (course_id,)
        )
        students = cursor.fetchall()

        # Convert datetime to string for JSON serialization
        result = []
        for s in students:
            row = dict(s)
            row['created_at'] = str(row['created_at'])
            result.append(row)

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": f"Failed to fetch students: {str(e)}"}), 500

    finally:
        if conn:
            conn.close()


# =============================================================
# STUDENT ENDPOINTS
# =============================================================

@app.route('/students', methods=['POST'])
@role_required('admin')
def add_student():
    """
    POST /students  [Admin only]
    Adds a new student using the stored procedure (insert_student).

    Request body (JSON):
        { "name": "...", "email": "...", "password": "...", "course_id": 1 }

    Returns:
        201: { "msg": "Student added", "student_id": X }
    """
    data = request.get_json()

    # --- Input Validation ---
    required = ['name', 'email', 'password', 'course_id']
    for field in required:
        if not data or data.get(field) is None:
            return jsonify({"error": f"'{field}' is required"}), 400

    name      = data['name'].strip()
    email     = data['email'].strip().lower()
    password  = data['password']
    course_id = data['course_id']

    if not isinstance(course_id, int) or course_id <= 0:
        return jsonify({"error": "course_id must be a positive integer"}), 400

    # Hash the password
    password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    conn = None
    try:
        conn   = get_db_connection()
        cursor = conn.cursor()

        # Call the stored procedure — it validates course_id and inserts the student
        # SELECT is used because PostgreSQL functions that RETURN a value need SELECT
        cursor.execute(
            "SELECT insert_student(%s, %s, %s, %s)",
            (name, email, password_hash, course_id)
        )
        new_student_id = cursor.fetchone()[0]
        conn.commit()

        return jsonify({"msg": "Student added", "student_id": new_student_id}), 201

    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        return jsonify({"error": "Email already registered"}), 409

    except psycopg2.errors.RaiseException as e:
        # Catches RAISE EXCEPTION from stored procedure (e.g., invalid course)
        conn.rollback()
        return jsonify({"error": str(e).split('\n')[0]}), 400

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": f"Failed to add student: {str(e)}"}), 500

    finally:
        if conn:
            conn.close()


@app.route('/students', methods=['GET'])
@jwt_required()
def get_students():
    """
    GET /students
    - Admin: Returns all students with their course information (JOIN query)
    - Student: Returns only their own profile with course info

    Each student object:
        { user_id, name, email, course: { course_id, course_name, course_code, course_duration } }
    """
    current_user_id = get_jwt_identity()  # Get user_id from JWT

    conn = None
    try:
        conn   = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # Fetch the role of the requesting user
        cursor.execute("SELECT role FROM users WHERE user_id = %s", (current_user_id,))
        user = cursor.fetchone()

        if not user:
            return jsonify({"error": "User not found"}), 404

        # Common SELECT query — JOINs users with courses to get course details
        base_query = """
            SELECT
                u.user_id,
                u.name,
                u.email,
                u.created_at,
                c.course_id,
                c.course_name,
                c.course_code,
                c.course_duration
            FROM users u
            LEFT JOIN courses c ON u.course_id = c.course_id
            WHERE u.role = 'student'
        """

        if user['role'] == 'admin':
            # Admin sees all students
            cursor.execute(base_query + " ORDER BY u.name")
        else:
            # Student sees only their own record
            cursor.execute(base_query + " AND u.user_id = %s", (current_user_id,))

        rows = cursor.fetchall()

        # Format the result — nest course details inside a 'course' object
        result = []
        for row in rows:
            student = {
                "user_id":    row['user_id'],
                "name":       row['name'],
                "email":      row['email'],
                "created_at": str(row['created_at']),
                "course": {
                    "course_id":       row['course_id'],
                    "course_name":     row['course_name'],
                    "course_code":     row['course_code'],
                    "course_duration": row['course_duration']
                } if row['course_id'] else None  # None if student has no course
            }
            result.append(student)

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": f"Failed to fetch students: {str(e)}"}), 500

    finally:
        if conn:
            conn.close()


@app.route('/students/<int:student_id>', methods=['GET'])
@jwt_required()
def get_student(student_id):
    """
    GET /students/<student_id>
    - Admin: Can view any student
    - Student: Can only view their own profile (403 otherwise)
    """
    current_user_id = get_jwt_identity()

    conn = None
    try:
        conn   = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # Get the requesting user's role
        cursor.execute("SELECT role FROM users WHERE user_id = %s", (current_user_id,))
        requester = cursor.fetchone()

        if not requester:
            return jsonify({"error": "Unauthorized"}), 401

        # Students can only view their own profile
        if requester['role'] == 'student' and str(student_id) != current_user_id:
            return jsonify({"error": "Access forbidden: you can only view your own profile"}), 403

        # Fetch the student with course info
        cursor.execute(
            """
            SELECT
                u.user_id, u.name, u.email, u.created_at,
                c.course_id, c.course_name, c.course_code, c.course_duration
            FROM users u
            LEFT JOIN courses c ON u.course_id = c.course_id
            WHERE u.user_id = %s AND u.role = 'student'
            """,
            (student_id,)
        )
        row = cursor.fetchone()

        if not row:
            return jsonify({"error": f"Student with ID {student_id} not found"}), 404

        # Format the response
        student = {
            "user_id":    row['user_id'],
            "name":       row['name'],
            "email":      row['email'],
            "created_at": str(row['created_at']),
            "course": {
                "course_id":       row['course_id'],
                "course_name":     row['course_name'],
                "course_code":     row['course_code'],
                "course_duration": row['course_duration']
            } if row['course_id'] else None
        }

        return jsonify(student), 200

    except Exception as e:
        return jsonify({"error": f"Failed to fetch student: {str(e)}"}), 500

    finally:
        if conn:
            conn.close()


@app.route('/students/<int:student_id>', methods=['PUT'])
@role_required('admin')
def update_student(student_id):
    """
    PUT /students/<student_id>  [Admin only]
    Updates student name, email, and/or course using the stored procedure.

    Request body (JSON):
        { "name": "...", "email": "...", "course_id": 2 }
        (All fields optional — only provided fields are updated)

    Returns:
        200: { "msg": "Student updated" }
    """
    data = request.get_json()

    if not data:
        return jsonify({"error": "Request body is required"}), 400

    # Extract fields — all are optional for update
    name      = data.get('name',      None)
    email     = data.get('email',     None)
    course_id = data.get('course_id', None)

    # Validate course_id type if provided
    if course_id is not None and (not isinstance(course_id, int) or course_id <= 0):
        return jsonify({"error": "course_id must be a positive integer"}), 400

    if name:
        name = name.strip()
    if email:
        email = email.strip().lower()

    conn = None
    try:
        conn   = get_db_connection()
        cursor = conn.cursor()

        # Call the stored procedure to update student
        cursor.execute(
            "SELECT update_student(%s, %s, %s, %s)",
            (student_id, name, email, course_id)
        )
        conn.commit()

        return jsonify({"msg": "Student updated"}), 200

    except psycopg2.errors.RaiseException as e:
        conn.rollback()
        return jsonify({"error": str(e).split('\n')[0]}), 400

    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        return jsonify({"error": "Email already in use by another user"}), 409

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": f"Failed to update student: {str(e)}"}), 500

    finally:
        if conn:
            conn.close()


@app.route('/students/<int:student_id>', methods=['DELETE'])
@role_required('admin')
def delete_student(student_id):
    """
    DELETE /students/<student_id>  [Admin only]
    Deletes a student using the stored procedure (delete_student).

    Returns:
        200: { "msg": "Student deleted" }
    """
    conn = None
    try:
        conn   = get_db_connection()
        cursor = conn.cursor()

        # Call the stored procedure to safely delete the student
        cursor.execute("SELECT delete_student(%s)", (student_id,))
        conn.commit()

        return jsonify({"msg": "Student deleted"}), 200

    except psycopg2.errors.RaiseException as e:
        conn.rollback()
        return jsonify({"error": str(e).split('\n')[0]}), 404

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": f"Failed to delete student: {str(e)}"}), 500

    finally:
        if conn:
            conn.close()


# =============================================================
# FRONTEND ROUTES — Serve static files from ../frontend/
# =============================================================

@app.route('/')
def serve_frontend():
    """Serves the main frontend index.html"""
    return send_from_directory('../frontend', 'index.html')


@app.route('/<path:filename>')
def serve_static(filename):
    """Serves any other static file (CSS, JS, images) from the frontend folder"""
    return send_from_directory('../frontend', filename)


# =============================================================
# RUN THE APP
# =============================================================

if __name__ == '__main__':
    # debug=True enables auto-reload on code changes (disable in production)
    app.run(debug=True, host='0.0.0.0', port=5000)
