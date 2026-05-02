import sqlite3
import os

DB = os.path.abspath(os.path.join(os.path.dirname(__file__), "app.db"))

def get_conn():
    return sqlite3.connect(DB, check_same_thread=False)

def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        name TEXT,
        icon TEXT,
        refresh_token TEXT
    )
    """)

    conn.commit()
    conn.close()

def create_user(user_id, name, icon, refresh_token=None):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    INSERT OR REPLACE INTO users (id, name, icon, refresh_token)
    VALUES (?, ?, ?, COALESCE(?, refresh_token))
    """, (user_id, name, icon, refresh_token))

    conn.commit()
    conn.close()

def get_user(user_id):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT * FROM users WHERE id=?", (user_id,))
    user = cur.fetchone()

    conn.close()
    return user

def get_user_by_token(token):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT * FROM users WHERE refresh_token=?", (token,))
    user = cur.fetchone()

    conn.close()
    return user
