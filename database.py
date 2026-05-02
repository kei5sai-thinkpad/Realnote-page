import sqlite3
import os

# 💥 絶対パス（ここが超重要）
DB = os.path.abspath(os.path.join(os.path.dirname(__file__), "app.db"))

# ================= 接続 =================
def get_conn():
    return sqlite3.connect(DB, check_same_thread=False)

# ================= 初期化 =================
def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        name TEXT,
        icon TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS rooms (
        name TEXT PRIMARY KEY,
        password TEXT DEFAULT "",
        type TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS notes (
        room TEXT PRIMARY KEY,
        content TEXT DEFAULT ""
    )
    """)

    conn.commit()
    conn.close()

# ================= users =================
def create_user(user_id, name, icon):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    INSERT OR REPLACE INTO users (id, name, icon)
    VALUES (?, ?, ?)
    """, (user_id, name, icon))

    conn.commit()
    conn.close()

def get_user(user_id):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT * FROM users WHERE id=?", (user_id,))
    user = cur.fetchone()

    conn.close()
    return user

# ================= rooms =================
def get_rooms():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT name, type FROM rooms")
    rows = cur.fetchall()

    conn.close()

    return [
        {
            "name": r[0],
            "label": "閲覧専用" if r[1] == "readonly" else "共有"
        }
        for r in rows
    ]

# ================= join / create =================
def join_or_create_room(name, password, room_type):
    conn = get_conn()
    cur = conn.cursor()

    try:
        cur.execute(
            "SELECT password, type FROM rooms WHERE name=?",
            (name,)
        )
        room = cur.fetchone()

        # ================= 既存 =================
        if room:
            saved_password, saved_type = room

            if saved_password and saved_password != (password or ""):
                return {
                    "success": False,
                    "message": "パスワードが違います"
                }

            return {
                "success": True,
                "can_edit": saved_type == "shared",
                "label": "閲覧専用" if saved_type == "readonly" else "共有"
            }

        # ================= 新規 =================
        cur.execute("""
        INSERT INTO rooms (name, password, type)
        VALUES (?, ?, ?)
        """, (name, password or "", room_type))

        cur.execute("""
        INSERT INTO notes (room, content)
        VALUES (?, ?)
        """, (name, ""))

        conn.commit()

        return {
            "success": True,
            "can_edit": room_type == "shared",
            "label": "閲覧専用" if room_type == "readonly" else "共有"
        }

    except Exception as e:
        conn.rollback()
        return {
            "success": False,
            "message": str(e)
        }

    finally:
        conn.close()

# ================= notes =================
def get_note(room):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT content FROM notes WHERE room=?", (room,))
    row = cur.fetchone()

    conn.close()
    return row[0] if row else ""

def save_note(room, text):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    INSERT OR REPLACE INTO notes (room, content)
    VALUES (?, ?)
    """, (room, text))

    conn.commit()
    conn.close()
