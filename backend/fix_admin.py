"""
fix_admin.py — Resets the admin user with a freshly generated bcrypt hash.
Run this once: python backend/fix_admin.py
"""
import os
import psycopg2
from flask_bcrypt import Bcrypt
from flask import Flask
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))

app   = Flask(__name__)
bcrypt = Bcrypt(app)

# Generate a proper bcrypt hash for "admin123"
password_hash = bcrypt.generate_password_hash("admin123").decode('utf-8')
print(f"Generated hash: {password_hash}")

conn = psycopg2.connect(
    host     = os.getenv('DB_HOST',     'localhost'),
    port     = os.getenv('DB_PORT',     5432),
    dbname   = os.getenv('DB_NAME',     'sciqus_db'),
    user     = os.getenv('DB_USER',     'postgres'),
    password = os.getenv('DB_PASSWORD', '')
)

cursor = conn.cursor()

# Remove the broken admin if it exists
cursor.execute("DELETE FROM users WHERE email = 'admin@sciqus.com';")

# Insert fresh admin with correct bcrypt hash
cursor.execute(
    """
    INSERT INTO users (name, email, password_hash, role)
    VALUES (%s, %s, %s, %s)
    """,
    ('Super Admin', 'admin@sciqus.com', password_hash, 'admin')
)

conn.commit()
conn.close()

print("[OK] Admin user reset successfully!")
print("   Email:    admin@sciqus.com")
print("   Password: admin123")
