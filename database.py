import sqlite3

DB_NAME = "app.db"


def get_conn():
    return sqlite3.connect(DB_NAME)


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    # ユーザー
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        name TEXT,
        icon TEXT
    )
    """)

    # ルーム
    cur.execute("""
    CREATE TABLE IF NOT EXISTS rooms (
        name TEXT PRIMARY KEY,
        password TEXT,
        type TEXT,
        owner TEXT
    )
    """)

    # ノート
    cur.execute("""
    CREATE TABLE IF NOT EXISTS notes (
        room TEXT PRIMARY KEY,
        content TEXT
    )
    """)

    conn.commit()
    conn.close()


# ---------- user ----------
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

    cur.execute("SELECT id, name, icon FROM users WHERE id=?", (user_id,))
    row = cur.fetchone()

    conn.close()
    return row


# ---------- room ----------
def create_room(room, password, room_type, owner):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO rooms VALUES (?, ?, ?, ?)
    """, (room, password, room_type, owner))

    conn.commit()
    conn.close()


def get_room(room):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT * FROM rooms WHERE name=?", (room,))
    row = cur.fetchone()

    conn.close()
    return row


def get_all_rooms():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT name, type FROM rooms")
    rows = cur.fetchall()

    conn.close()
    return rows


# ---------- note ----------
def save_note(room, text):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    INSERT OR REPLACE INTO notes (room, content)
    VALUES (?, ?)
    """, (room, text))

    conn.commit()
    conn.close()


def get_note(room):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT content FROM notes WHERE room=?", (room,))
    row = cur.fetchone()

    conn.close()

    return row[0] if row else ""
