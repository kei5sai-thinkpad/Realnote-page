import sqlite3
import os

DB = os.path.join(os.path.dirname(__file__), "app.db")

def get_conn():
    return sqlite3.connect(DB, check_same_thread=False)

# ================= init =================
def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS rooms (
        name TEXT PRIMARY KEY,
        password TEXT,
        type TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS notes (
        room TEXT PRIMARY KEY,
        content TEXT
    )
    """)

    conn.commit()
    conn.close()

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

# ================= join/create =================
def join_or_create_room(name, password, room_type):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT password, type FROM rooms WHERE name=?", (name,))
    room = cur.fetchone()

    # 既存
    if room:
        saved_password, saved_type = room

        if saved_password and saved_password != password:
            conn.close()
            return {"success": False, "message": "パスワード違う"}

        conn.close()
        return {
            "success": True,
            "can_edit": saved_type == "shared",
            "label": "閲覧専用" if saved_type == "readonly" else "共有"
        }

    # 新規
    cur.execute(
        "INSERT INTO rooms VALUES (?, ?, ?)",
        (name, password, room_type)
    )

    cur.execute(
        "INSERT INTO notes VALUES (?, ?)",
        (name, "")
    )

    conn.commit()
    conn.close()

    return {
        "success": True,
        "can_edit": room_type == "shared",
        "label": "閲覧専用" if room_type == "readonly" else "共有"
    }

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
