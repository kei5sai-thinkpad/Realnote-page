import sqlite3
import sqlite3
import os

DB = os.path.join(os.path.dirname(__file__), "app.db")
DB = "app.db"

def init_db():
    conn = sqlite3.connect(DB)
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

# ===== user =====
def create_user(user_id, name, icon):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute("""
    INSERT OR IGNORE INTO users VALUES (?, ?, ?)
    """, (user_id, name, icon))

    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute("SELECT * FROM users WHERE id=?", (user_id,))
    user = cur.fetchone()

    conn.close()
    return user

# ===== rooms =====
def get_rooms():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute("SELECT name, type FROM rooms")
    rows = cur.fetchall()

    conn.close()

    return [
        {"name": r[0], "label": "閲覧専用" if r[1]=="readonly" else "共有"}
        for r in rows
    ]

def join_or_create_room(name, password, room_type):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute("SELECT password, type FROM rooms WHERE name=?", (name,))
    room = cur.fetchone()

    if room:
        if room[0] != password:
            return {"success": False, "message": "パスワード違う"}

        return {
            "success": True,
            "can_edit": room[1] == "shared",
            "label": "閲覧専用" if room[1]=="readonly" else "共有"
        }

    cur.execute("INSERT INTO rooms VALUES (?, ?, ?)", (name, password, room_type))
    cur.execute("INSERT INTO notes VALUES (?, ?)", (name, ""))

    conn.commit()
    conn.close()

    return {
        "success": True,
        "can_edit": room_type == "shared",
        "label": "閲覧専用" if room_type=="readonly" else "共有"
    }

# ===== notes =====
def get_note(room):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute("SELECT content FROM notes WHERE room=?", (room,))
    row = cur.fetchone()

    conn.close()

    return row[0] if row else ""

def save_note(room, text):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute("UPDATE notes SET content=? WHERE room=?", (text, room))

    conn.commit()
    conn.close()
