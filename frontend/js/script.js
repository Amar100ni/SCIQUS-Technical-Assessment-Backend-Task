// =============================================================
// Sciqus — Frontend JavaScript
// File: frontend/js/script.js
//
// This file handles:
//   1. Login / Logout
//   2. Loading students and courses into tables
//   3. Add Student modal (admin only)
//   4. Add Course modal (admin only)
//   5. Delete Student (admin only)
//
// The Flask backend is expected at BASE_URL.
// JWT token and user role are stored in localStorage.
// =============================================================

const BASE_URL = 'http://127.0.0.1:5000';

// Keys used in localStorage
const TOKEN_KEY = 'token';
const ROLE_KEY  = 'role';

// =============================================================
// HELPERS
// =============================================================

/** Get the stored JWT token */
function getToken() {
    return localStorage.getItem(TOKEN_KEY);
}

/** Get the stored user role ('admin' or 'student') */
function getRole() {
    return localStorage.getItem(ROLE_KEY);
}

/**
 * Build the Authorization header object for fetch() calls.
 * Every protected API call must include this header.
 */
function authHeader() {
    return {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${getToken()}`
    };
}

/**
 * Show a message inside a given element.
 * @param {string} elementId - ID of the message <div>
 * @param {string} text      - Message text to show
 * @param {'error'|'success'} type - Visual style
 */
function showMsg(elementId, text, type = 'error') {
    const el = document.getElementById(elementId);
    if (!el) return;
    el.textContent = text;
    el.className = `msg msg-${type}`;
    el.classList.remove('hidden');
}

/** Hide a message element */
function hideMsg(elementId) {
    const el = document.getElementById(elementId);
    if (el) el.classList.add('hidden');
}

/**
 * Set a button into loading state (disabled + text change).
 * @param {HTMLButtonElement} btn
 * @param {boolean} isLoading
 * @param {string} originalText - Text to restore when not loading
 */
function setLoading(btn, isLoading, originalText) {
    btn.disabled = isLoading;
    btn.textContent = isLoading ? 'Please wait…' : originalText;
}

// =============================================================
// APP INITIALIZATION
// =============================================================

/**
 * Called on page load.
 * Checks if a token exists — if yes, show dashboard; if no, show login.
 */
function init() {
    if (getToken()) {
        showDashboard();
    } else {
        showLogin();
    }
}

// =============================================================
// LOGIN
// =============================================================

/** Show the login page, hide dashboard */
function showLogin() {
    document.getElementById('login-page').classList.remove('hidden');
    document.getElementById('dashboard-page').classList.add('hidden');
}

/**
 * Handle the login form submission.
 * Calls POST /auth/login, stores token + role, then shows dashboard.
 */
async function handleLogin(e) {
    e.preventDefault();

    const email    = document.getElementById('login-email').value.trim();
    const password = document.getElementById('login-password').value;
    const btn      = document.getElementById('login-btn');

    hideMsg('login-error');
    setLoading(btn, true, 'Login');

    try {
        const res  = await fetch(`${BASE_URL}/auth/login`, {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ email, password })
        });

        const data = await res.json();

        if (res.ok) {
            // Save token and role to localStorage
            localStorage.setItem(TOKEN_KEY, data.access_token);
            localStorage.setItem(ROLE_KEY,  data.role);
            showDashboard();
        } else {
            showMsg('login-error', data.error || 'Login failed. Check your credentials.');
        }

    } catch (err) {
        showMsg('login-error', 'Cannot connect to server. Is Flask running on port 5000?');
    } finally {
        setLoading(btn, false, 'Login');
    }
}

// =============================================================
// LOGOUT
// =============================================================

/**
 * Clear stored credentials and return to login page.
 */
function handleLogout() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(ROLE_KEY);
    showLogin();
}

// =============================================================
// DASHBOARD
// =============================================================

/**
 * Show the dashboard page.
 * Applies role-based visibility and loads data from the API.
 */
function showDashboard() {
    document.getElementById('login-page').classList.add('hidden');
    document.getElementById('dashboard-page').classList.remove('hidden');

    applyRoleVisibility();
    loadStudents();
    loadCourses();
}

/**
 * If the user is an admin, show all .admin-only elements.
 * If the user is a student, keep them hidden.
 */
function applyRoleVisibility() {
    const isAdmin = getRole() === 'admin';
    document.querySelectorAll('.admin-only').forEach(el => {
        if (isAdmin) {
            el.classList.remove('hidden');
        } else {
            el.classList.add('hidden');
        }
    });
}

// =============================================================
// STUDENTS TABLE
// =============================================================

/**
 * Fetch all students from GET /students and render them in the table.
 * Admins see all students; students see only their own record
 * (the backend handles this automatically based on the JWT token).
 */
async function loadStudents() {
    const tbody  = document.getElementById('students-tbody');
    const isAdmin = getRole() === 'admin';
    tbody.innerHTML = '<tr><td colspan="4" class="table-loading">Loading…</td></tr>';
    hideMsg('students-error');

    try {
        const res  = await fetch(`${BASE_URL}/students`, {
            headers: authHeader()
        });
        const data = await res.json();

        if (!res.ok) {
            showMsg('students-error', data.error || 'Failed to load students.');
            tbody.innerHTML = '<tr><td colspan="4" class="table-empty">Could not load students.</td></tr>';
            return;
        }

        if (data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="table-empty">No students found.</td></tr>';
            return;
        }

        // Build a table row for each student
        tbody.innerHTML = data.map(student => `
            <tr data-id="${student.user_id}">
                <td>${escapeHtml(student.name)}</td>
                <td>${escapeHtml(student.email)}</td>
                <td>${student.course ? escapeHtml(student.course.course_name) : '<span style="color:#9ca3af">Not enrolled</span>'}</td>
                ${isAdmin ? `
                <td class="admin-only">
                    <button
                        class="btn btn-danger"
                        onclick="deleteStudent(${student.user_id})"
                        aria-label="Delete ${escapeHtml(student.name)}"
                    >Delete</button>
                </td>` : '<td class="admin-only hidden"></td>'}
            </tr>
        `).join('');

    } catch (err) {
        showMsg('students-error', 'Network error — is Flask running?');
        tbody.innerHTML = '<tr><td colspan="4" class="table-empty">Connection failed.</td></tr>';
    }
}

/**
 * Delete a student by ID.
 * Calls DELETE /students/<id> with admin JWT.
 * @param {number} studentId
 */
async function deleteStudent(studentId) {
    if (!confirm('Are you sure you want to delete this student?')) return;

    try {
        const res  = await fetch(`${BASE_URL}/students/${studentId}`, {
            method:  'DELETE',
            headers: authHeader()
        });
        const data = await res.json();

        if (res.ok) {
            // Reload the table to reflect the deletion
            loadStudents();
        } else {
            showMsg('students-error', data.error || 'Failed to delete student.');
        }

    } catch (err) {
        showMsg('students-error', 'Network error during delete.');
    }
}

// =============================================================
// COURSES TABLE
// =============================================================

/**
 * Fetch all courses from GET /courses and render them in the table.
 */
async function loadCourses() {
    const tbody = document.getElementById('courses-tbody');
    tbody.innerHTML = '<tr><td colspan="3" class="table-loading">Loading…</td></tr>';
    hideMsg('courses-error');

    try {
        const res  = await fetch(`${BASE_URL}/courses`, {
            headers: authHeader()
        });
        const data = await res.json();

        if (!res.ok) {
            showMsg('courses-error', data.error || 'Failed to load courses.');
            tbody.innerHTML = '<tr><td colspan="3" class="table-empty">Could not load courses.</td></tr>';
            return;
        }

        if (data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="3" class="table-empty">No courses yet. Add one above!</td></tr>';
            return;
        }

        // Build a table row for each course
        tbody.innerHTML = data.map(course => `
            <tr>
                <td>${escapeHtml(course.course_name)}</td>
                <td><code style="background:#f3f4f6; padding:2px 6px; border-radius:4px;">${escapeHtml(course.course_code)}</code></td>
                <td>${course.course_duration} months</td>
            </tr>
        `).join('');

    } catch (err) {
        showMsg('courses-error', 'Network error — is Flask running?');
        tbody.innerHTML = '<tr><td colspan="3" class="table-empty">Connection failed.</td></tr>';
    }
}

// =============================================================
// ADD STUDENT MODAL
// =============================================================

/** Open the Add Student modal and populate the course dropdown */
function openStudentModal() {
    hideMsg('student-msg');
    document.getElementById('student-form').reset();
    document.getElementById('student-modal').classList.remove('hidden');
    populateCourseDropdown();
}

/** Close the Add Student modal */
function closeStudentModal() {
    document.getElementById('student-modal').classList.add('hidden');
}

/**
 * Populate the course <select> dropdown in the Add Student form.
 * Fetches courses from GET /courses.
 */
async function populateCourseDropdown() {
    const select = document.getElementById('s-course');
    select.innerHTML = '<option value="">Loading courses…</option>';

    try {
        const res  = await fetch(`${BASE_URL}/courses`, { headers: authHeader() });
        const data = await res.json();

        if (!res.ok || data.length === 0) {
            select.innerHTML = '<option value="">No courses available — add one first</option>';
            return;
        }

        select.innerHTML = '<option value="">— Select a course —</option>' +
            data.map(c => `<option value="${c.course_id}">${escapeHtml(c.course_name)} (${escapeHtml(c.course_code)})</option>`).join('');

    } catch (err) {
        select.innerHTML = '<option value="">Failed to load courses</option>';
    }
}

/**
 * Handle the Add Student form submission.
 * Calls POST /students with the admin JWT token.
 */
async function handleAddStudent(e) {
    e.preventDefault();

    const name     = document.getElementById('s-name').value.trim();
    const email    = document.getElementById('s-email').value.trim();
    const password = document.getElementById('s-password').value;
    const courseId = parseInt(document.getElementById('s-course').value);
    const btn      = document.getElementById('student-submit-btn');

    hideMsg('student-msg');

    // Basic validation
    if (!name || !email || !password || !courseId) {
        showMsg('student-msg', 'All fields are required.', 'error');
        return;
    }

    setLoading(btn, true, 'Add Student');

    try {
        const res  = await fetch(`${BASE_URL}/students`, {
            method:  'POST',
            headers: authHeader(),
            body:    JSON.stringify({ name, email, password, course_id: courseId })
        });
        const data = await res.json();

        if (res.ok) {
            showMsg('student-msg', `Student added successfully! (ID: ${data.student_id})`, 'success');
            document.getElementById('student-form').reset();
            loadStudents(); // Refresh the students table
        } else {
            showMsg('student-msg', data.error || 'Failed to add student.', 'error');
        }

    } catch (err) {
        showMsg('student-msg', 'Network error — is Flask running?', 'error');
    } finally {
        setLoading(btn, false, 'Add Student');
    }
}

// =============================================================
// ADD COURSE MODAL
// =============================================================

/** Open the Add Course modal */
function openCourseModal() {
    hideMsg('course-msg');
    document.getElementById('course-form').reset();
    document.getElementById('course-modal').classList.remove('hidden');
}

/** Close the Add Course modal */
function closeCourseModal() {
    document.getElementById('course-modal').classList.add('hidden');
}

/**
 * Handle the Add Course form submission.
 * Calls POST /courses with the admin JWT token.
 */
async function handleAddCourse(e) {
    e.preventDefault();

    const courseName     = document.getElementById('c-name').value.trim();
    const courseCode     = document.getElementById('c-code').value.trim().toUpperCase();
    const courseDuration = parseInt(document.getElementById('c-duration').value);
    const btn            = document.getElementById('course-submit-btn');

    hideMsg('course-msg');

    // Basic validation
    if (!courseName || !courseCode || !courseDuration || courseDuration <= 0) {
        showMsg('course-msg', 'All fields are required and duration must be positive.', 'error');
        return;
    }

    setLoading(btn, true, 'Add Course');

    try {
        const res  = await fetch(`${BASE_URL}/courses`, {
            method:  'POST',
            headers: authHeader(),
            body:    JSON.stringify({
                course_name:     courseName,
                course_code:     courseCode,
                course_duration: courseDuration
            })
        });
        const data = await res.json();

        if (res.ok) {
            showMsg('course-msg', `Course added successfully! (ID: ${data.course_id})`, 'success');
            document.getElementById('course-form').reset();
            loadCourses(); // Refresh the courses table
        } else {
            showMsg('course-msg', data.error || 'Failed to add course.', 'error');
        }

    } catch (err) {
        showMsg('course-msg', 'Network error — is Flask running?', 'error');
    } finally {
        setLoading(btn, false, 'Add Course');
    }
}

// =============================================================
// SECURITY HELPER
// =============================================================

/**
 * Escape HTML special characters to prevent XSS when inserting
 * user-provided data into innerHTML.
 * @param {string} str
 * @returns {string}
 */
function escapeHtml(str) {
    if (str == null) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

// =============================================================
// EVENT LISTENERS — Wire up all buttons and forms
// =============================================================
document.addEventListener('DOMContentLoaded', function () {

    // Login form
    document.getElementById('login-form').addEventListener('submit', handleLogin);

    // Logout button
    document.getElementById('logout-btn').addEventListener('click', handleLogout);

    // Add Student button & modal
    document.getElementById('add-student-btn').addEventListener('click', openStudentModal);
    document.getElementById('student-modal-close').addEventListener('click', closeStudentModal);
    document.getElementById('student-cancel-btn').addEventListener('click', closeStudentModal);
    document.getElementById('student-form').addEventListener('submit', handleAddStudent);

    // Close student modal if clicking outside the box
    document.getElementById('student-modal').addEventListener('click', function (e) {
        if (e.target === this) closeStudentModal();
    });

    // Add Course button & modal
    document.getElementById('add-course-btn').addEventListener('click', openCourseModal);
    document.getElementById('course-modal-close').addEventListener('click', closeCourseModal);
    document.getElementById('course-cancel-btn').addEventListener('click', closeCourseModal);
    document.getElementById('course-form').addEventListener('submit', handleAddCourse);

    // Close course modal if clicking outside the box
    document.getElementById('course-modal').addEventListener('click', function (e) {
        if (e.target === this) closeCourseModal();
    });

    // Start the app
    init();
});
