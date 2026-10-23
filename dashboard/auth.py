
import sqlite3
import hashlib
import hmac
import secrets
from pathlib import Path

DB_PATH = Path(__file__).with_name("users.db")


def get_connection():
    return sqlite3.connect(DB_PATH)


def create_users_table():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL
            )
        """)


def hash_password(password, salt):
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt),
        600_000,
    ).hex()


def signup(email, password):
    email = email.strip().lower()

    if not email or "@" not in email:
        return False, "Enter a valid email address."

    if len(password) < 8:
        return False, "Password must contain at least 8 characters."

    salt = secrets.token_bytes(16).hex()
    password_hash = hash_password(password, salt)

    try:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO users (email, password_hash, salt)
                VALUES (?, ?, ?)
                """,
                (email, password_hash, salt),
            )
        return True, "Account created successfully. You can log in."
    except sqlite3.IntegrityError:
        return False, "An account with this email already exists."


def login(email, password):
    email = email.strip().lower()

    with get_connection() as conn:
        user = conn.execute(
            """
            SELECT password_hash, salt
            FROM users
            WHERE email = ?
            """,
            (email,),
        ).fetchone()

    if user is None:
        return False

    stored_hash, salt = user
    entered_hash = hash_password(password, salt)

    return hmac.compare_digest(stored_hash, entered_hash)


create_users_table()
