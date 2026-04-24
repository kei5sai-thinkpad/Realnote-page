import sqlite3

# ----------------------------
# DB接続
# ----------------------------

conn = sqlite3.connect("notecord.db", check_same_thread=False)
cursor = conn.cursor()


# ----------------------------
# rooms テーブル作成
# ----------------------------

cursor.execute("""
CREATE TABLE IF NOT EXISTS rooms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_name TEXT UNIQUE,
    password TEXT DEFAULT '',
    room_type TEXT DEFAULT 'shared',
    owner TEXT
)
""")


# ----------------------------
# notes テーブル作成
# ----------------------------

cursor.execute("""
CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_name TEXT UNIQUE,
    content TEXT DEFAULT '',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

conn.commit()


# ----------------------------
# 部屋作成
# ----------------------------

def create_room(room, password="", room_type="shared", owner="User"):
    cursor.execute("""
        INSERT INTO rooms (room_name, password, room_type, owner)
        VALUES (?, ?, ?, ?)
    """, (room, password, room_type, owner))

    cursor.execute("""
        INSERT INTO notes (room_name, content)
        VALUES (?, ?)
    """, (room, ""))

    conn.commit()


# ----------------------------
# 部屋取得
# ----------------------------

def get_room(room):
    cursor.execute("""
        SELECT room_name, password, room_type, owner
        FROM rooms
        WHERE room_name = ?
    """, (room,))

    return cursor.fetchone()


# ----------------------------
# ノート保存
# ----------------------------

def save_note(room, text):
    cursor.execute("""
        UPDATE notes
        SET content = ?, updated_at = CURRENT_TIMESTAMP
        WHERE room_name = ?
    """, (text, room))

    conn.commit()


# ----------------------------
# ノート取得
# ----------------------------

def get_note(room):
    cursor.execute("""
        SELECT content
        FROM notes
        WHERE room_name = ?
    """, (room,))

    result = cursor.fetchone()

    if result:
        return result[0]

    return ""


# ----------------------------
# 部屋一覧取得
# ----------------------------

def get_all_rooms():
    cursor.execute("""
        SELECT room_name, room_type
        FROM rooms
        ORDER BY id DESC
    """)

    return cursor.fetchall()


# ----------------------------
# テスト
# ----------------------------

if __name__ == "__main__":
    if not get_room("general"):
        create_room(
            room="general",
            password="",
            room_type="shared",
            owner="Rei"
        )

    save_note("general", "SQLite保存成功！")

    print(get_room("general"))
    print(get_note("general"))
    print(get_all_rooms())
