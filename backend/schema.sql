-- =============================================================
-- Sciqus Student & Course Management System — Database Schema
-- =============================================================
-- Run this file after creating the database:
--   psql -U postgres -d sciqus_db -f schema.sql
-- =============================================================


-- ---------------------------------------------------------------
-- TABLE 1: courses
-- Stores all available courses in the system
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS courses (
    course_id       SERIAL PRIMARY KEY,                  -- Auto-increment primary key
    course_name     VARCHAR(255) NOT NULL,               -- Full name of the course
    course_code     VARCHAR(50)  NOT NULL UNIQUE,        -- Unique short code (e.g., "CS101")
    course_duration INTEGER      NOT NULL                -- Duration in months
);


-- ---------------------------------------------------------------
-- TABLE 2: users
-- Stores both admin and student accounts in a single table.
-- Role is differentiated by the 'role' column ('admin'|'student')
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    user_id         SERIAL PRIMARY KEY,
    name            VARCHAR(255) NOT NULL,
    email           VARCHAR(255) NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,               -- Bcrypt hashed password
    role            VARCHAR(20)  NOT NULL DEFAULT 'student',  -- 'admin' or 'student'
    course_id       INTEGER      NULL,                   -- NULL means not enrolled
    created_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,

    -- Foreign key: if a course is deleted, enrollment is set to NULL
    CONSTRAINT fk_course FOREIGN KEY (course_id)
        REFERENCES courses(course_id)
        ON DELETE SET NULL
);


-- ---------------------------------------------------------------
-- DEFAULT ADMIN USER
-- Password is a bcrypt hash of "admin123".
-- IMPORTANT: Change this password via the /auth/register endpoint
-- in production or update the hash here with a secure password.
-- Bcrypt hash below corresponds to plain text: admin123
-- ---------------------------------------------------------------
INSERT INTO users (name, email, password_hash, role)
VALUES (
    'Super Admin',
    'admin@sciqus.com',
    '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW',
    'admin'
)
ON CONFLICT (email) DO NOTHING;
-- ON CONFLICT ensures this INSERT is idempotent (safe to re-run)


-- =============================================================
-- STORED PROCEDURES (PostgreSQL Functions)
-- PostgreSQL uses PL/pgSQL for stored procedures / functions.
-- We define three procedures:
--   1. insert_student   — Adds a new student with course validation
--   2. update_student   — Updates student name, email, and/or course
--   3. delete_student   — Safely removes a student
-- =============================================================


-- ---------------------------------------------------------------
-- PROCEDURE 1: insert_student
-- Inserts a new student after validating that the course exists.
-- Raises an exception if the course_id is not found.
-- Returns the new user_id of the inserted student.
-- ---------------------------------------------------------------
CREATE OR REPLACE FUNCTION insert_student(
    p_name          VARCHAR(255),
    p_email         VARCHAR(255),
    p_password_hash VARCHAR(255),
    p_course_id     INTEGER
)
RETURNS INTEGER          -- Returns the newly created user_id
LANGUAGE plpgsql
AS $$
DECLARE
    v_course_exists BOOLEAN;  -- Flag to check if course exists
    v_new_user_id   INTEGER;  -- Will hold the new user's ID
BEGIN
    -- Step 1: Validate that the course_id exists in the courses table
    SELECT EXISTS(
        SELECT 1 FROM courses WHERE course_id = p_course_id
    ) INTO v_course_exists;

    -- Step 2: If course not found, raise an error (triggers rollback in caller)
    IF NOT v_course_exists THEN
        RAISE EXCEPTION 'Course with ID % does not exist', p_course_id;
    END IF;

    -- Step 3: Insert the new student and capture the generated user_id
    INSERT INTO users (name, email, password_hash, role, course_id)
    VALUES (p_name, p_email, p_password_hash, 'student', p_course_id)
    RETURNING user_id INTO v_new_user_id;

    -- Step 4: Return the new user_id to the caller
    RETURN v_new_user_id;
END;
$$;


-- ---------------------------------------------------------------
-- PROCEDURE 2: update_student
-- Updates a student's name, email, and/or course.
-- Validates that the new course_id exists (if provided).
-- Raises an exception if student not found or course invalid.
-- ---------------------------------------------------------------
CREATE OR REPLACE FUNCTION update_student(
    p_user_id    INTEGER,
    p_name       VARCHAR(255),
    p_email      VARCHAR(255),
    p_course_id  INTEGER       -- Pass NULL to keep existing course
)
RETURNS VOID
LANGUAGE plpgsql
AS $$
DECLARE
    v_student_exists BOOLEAN;
    v_course_exists  BOOLEAN;
BEGIN
    -- Step 1: Verify the student exists
    SELECT EXISTS(
        SELECT 1 FROM users WHERE user_id = p_user_id AND role = 'student'
    ) INTO v_student_exists;

    IF NOT v_student_exists THEN
        RAISE EXCEPTION 'Student with ID % not found', p_user_id;
    END IF;

    -- Step 2: If a new course_id is provided, validate it exists
    IF p_course_id IS NOT NULL THEN
        SELECT EXISTS(
            SELECT 1 FROM courses WHERE course_id = p_course_id
        ) INTO v_course_exists;

        IF NOT v_course_exists THEN
            RAISE EXCEPTION 'Course with ID % does not exist', p_course_id;
        END IF;
    END IF;

    -- Step 3: Perform the update
    -- COALESCE keeps the old value if the new one is NULL
    UPDATE users
    SET
        name      = COALESCE(p_name,      name),
        email     = COALESCE(p_email,     email),
        course_id = COALESCE(p_course_id, course_id)
    WHERE user_id = p_user_id AND role = 'student';
END;
$$;


-- ---------------------------------------------------------------
-- PROCEDURE 3: delete_student
-- Safely removes a student from the users table.
-- Raises an exception if the student does not exist.
-- ---------------------------------------------------------------
CREATE OR REPLACE FUNCTION delete_student(
    p_user_id INTEGER
)
RETURNS VOID
LANGUAGE plpgsql
AS $$
DECLARE
    v_student_exists BOOLEAN;
BEGIN
    -- Step 1: Confirm the student exists before attempting delete
    SELECT EXISTS(
        SELECT 1 FROM users WHERE user_id = p_user_id AND role = 'student'
    ) INTO v_student_exists;

    IF NOT v_student_exists THEN
        RAISE EXCEPTION 'Student with ID % not found', p_user_id;
    END IF;

    -- Step 2: Delete the student record
    DELETE FROM users WHERE user_id = p_user_id AND role = 'student';
END;
$$;


-- =============================================================
-- SAMPLE DATA (optional — useful for testing)
-- Uncomment these lines to insert sample courses
-- =============================================================

-- INSERT INTO courses (course_name, course_code, course_duration)
-- VALUES
--     ('Bachelor of Computer Science', 'BCS101', 36),
--     ('Full Stack Web Development',   'FSWD202', 6),
--     ('Data Science & ML',            'DSML303', 12)
-- ON CONFLICT (course_code) DO NOTHING;
