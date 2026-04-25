# server.py（SQLite完全接続版）

from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from database import (
    create_room,
    get_room,
    save_note,
    get_note,
    get_all_rooms
)

app = FastAPI()

# WebSocket接続中ユーザー
clients = {}


# ----------------------------
# HTML
# ----------------------------

html = """
<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<title>NoteCord</title>

<style>
body {
    margin: 0;
    font-family: sans-serif;
    background: #0f172a;
    color: white;
    display: flex;
    height: 100vh;
}

.sidebar {
    width: 280px;
    background: #020617;
    padding: 15px;
    border-right: 1px solid #1e293b;
}

.room {
    padding: 10px;
    border-radius: 10px;
    cursor: pointer;
    margin-bottom: 6px;
    background: #111827;
}

.room:hover {
    background: #1e293b;
}

.main {
    flex: 1;
    display: flex;
    flex-direction: column;
}

.header {
    padding: 15px 20px;
    background: #020617;
    border-bottom: 1px solid #1e293b;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

#note {
    flex: 1;
    padding: 20px;
    outline: none;
    overflow: auto;
    white-space: pre-wrap;
    font-size: 16px;
    line-height: 1.6;
}

.typing {
    padding: 10px 20px;
    color: #94a3b8;
    min-height: 24px;
}

input, button, select {
    width: 100%;
    padding: 10px;
    margin-top: 10px;
    border-radius: 10px;
    border: none;
    box-sizing: border-box;
}

button {
    background: #3b82f6;
    color: white;
    cursor: pointer;
}

button:hover {
    background: #2563eb;
}
</style>
</head>
<body>

<div class="sidebar">
    <h2>Rooms</h2>

    <div id="rooms"></div>

    <input id="roomInput" placeholder="部屋名">

    <select id="roomType">
        <option value="shared">共有ノート</option>
        <option value="readonly">閲覧専用ノート</option>
    </select>

    <button onclick="accessRoom()">入室 / 作成</button>
</div>

<div class="main">
    <div class="header">
        <span id="currentRoom">未接続</span>
        <span id="modeLabel"></span>
    </div>

    <div id="note" contenteditable="true"></div>
    <div class="typing" id="typing"></div>
</div>

<script>
let ws;
let isUpdating = false;

/* ユーザー名 */

let username = localStorage.getItem("notecord_username");

if (!username) {
    username = prompt("ユーザー名を入力してください");

    if (!username || username.trim() === "") {
        username = "User" + Math.floor(Math.random() * 1000);
    }

    localStorage.setItem("notecord_username", username);
}


/* HTMLエスケープ */

function escapeHtml(text) {
    const div = document.createElement("div");
    div.innerText = text;
    return div.innerHTML;
}


/* コード自動認識 */

function formatCodeBlocks(text) {
    return text.replace(
        /```(\\w+)?\\n([\\s\\S]*?)```/g,
        function(match, lang, code) {
            return `
                <div style="
                    background:#111827;
                    border:1px solid #334155;
                    border-radius:14px;
                    margin:14px 0;
                    overflow:hidden;
                ">
                    <div style="
                        background:#0b1220;
                        padding:10px 14px;
                        border-bottom:1px solid #334155;
                        font-size:13px;
                        font-weight:bold;
                        color:#cbd5e1;
                    ">
                        ${lang || "code"}
                    </div>

                    <pre style="
                        margin:0;
                        padding:16px;
                        font-family:Consolas, monospace;
                        font-size:14px;
                        line-height:1.7;
                        white-space:pre-wrap;
                        overflow-x:auto;
                        color:white;
                    ">${escapeHtml(code)}</pre>
                </div>
            `;
        }
    );
}


/* 部屋一覧 */

async function loadRooms() {
    const res = await fetch("/rooms");
    const rooms = await res.json();

    const container = document.getElementById("rooms");
    container.innerHTML = "";

    rooms.forEach(room => {
        const div = document.createElement("div");
        div.className = "room";
        div.innerText = room.name + " (" + room.label + ")";
        div.onclick = () => quickJoin(room.name);
        container.appendChild(div);
    });
}

function quickJoin(name) {
    document.getElementById("roomInput").value = name;
    accessRoom();
}


/* 入室 / 作成 */

async function accessRoom() {
    const room = document.getElementById("roomInput").value.trim();
    const type = document.getElementById("roomType").value;

    if (!room) {
        alert("部屋名を入力してください");
        return;
    }

    const password = prompt("パスワード（空でもOK）を入力してください") || "";

    const res = await fetch("/join-room", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            room: room,
            password: password,
            room_type: type,
            username: username
        })
    });

    const result = await res.json();

    if (!result.success) {
        alert(result.message);
        return;
    }

    connectRoom(room, result.can_edit, result.label);
    loadRooms();
}


/* 接続 */

function connectRoom(room, canEdit, label) {
    document.getElementById("currentRoom").innerText = "# " + room;
    document.getElementById("modeLabel").innerText = label;

    const note = document.getElementById("note");

    note.contentEditable = canEdit ? "true" : "false";

    if (ws) ws.close();

    ws = new WebSocket(
        (location.protocol === "https:" ? "wss://" : "ws://")
        + location.host + "/ws/" + room
    );

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);

        if (data.type === "init" || data.type === "update") {
            isUpdating = true;
            note.innerHTML = formatCodeBlocks(data.text);
            isUpdating = false;
        }

        if (data.type === "typing") {
            const typing = document.getElementById("typing");
            typing.innerText = data.user + " が入力中...";
            setTimeout(() => typing.innerText = "", 1000);
        }
    };

    note.oninput = () => {
        if (!canEdit) return;

        if (
            ws &&
            ws.readyState === WebSocket.OPEN &&
            !isUpdating
        ) {
            ws.send(JSON.stringify({
                type: "update",
                text: note.innerText
            }));

            ws.send(JSON.stringify({
                type: "typing",
                user: username
            }));
        }
    };
}

loadRooms();
</script>

</body>
</html>
"""


# ----------------------------
# API
# ----------------------------

class RoomData(BaseModel):
    room: str
    password: str = ""
    room_type: str
    username: str


@app.get("/")
async def home():
    return HTMLResponse(html)


@app.get("/rooms")
async def get_rooms():
    rows = get_all_rooms()

    result = []
    for room_name, room_type in rows:
        result.append({
            "name": room_name,
            "label": "閲覧専用" if room_type == "readonly" else "共有"
        })

    return result


@app.post("/join-room")
async def join_room(data: RoomData):
    room = data.room.strip()
    password = data.password.strip()
    room_type = data.room_type
    username = data.username

    if not room:
        return {
            "success": False,
            "message": "部屋名を入力してください"
        }

    room_data = get_room(room)

    # 新規作成
    if not room_data:
        create_room(
            room=room,
            password=password,
            room_type=room_type,
            owner=username
        )

        return {
            "success": True,
            "can_edit": True,
            "label": "作成者"
        }

    saved_room, saved_password, saved_type, saved_owner = room_data

    if saved_password != "" and saved_password != password:
        return {
            "success": False,
            "message": "パスワードが違います"
        }

    is_owner = saved_owner == username
    is_readonly = saved_type == "readonly"

    can_edit = True
    label = "共有ノート"

    if is_readonly and not is_owner:
        can_edit = False
        label = "閲覧専用"

    if is_owner:
        label = "作成者"

    return {
        "success": True,
        "can_edit": can_edit,
        "label": label
    }


@app.websocket("/ws/{room}")
async def websocket(ws: WebSocket, room: str):
    await ws.accept()

    if room not in clients:
        clients[room] = []

    clients[room].append(ws)

    await ws.send_json({
        "type": "init",
        "text": get_note(room)
    })

    try:
        while True:
            data = await ws.receive_json()

            if data["type"] == "update":
                save_note(room, data["text"])

                for client in clients[room][:]:
                    if client != ws:
                        try:
                            await client.send_json({
                                "type": "update",
                                "text": data["text"]
                            })
                        except:
                            pass

            if data["type"] == "typing":
                for client in clients[room][:]:
                    if client != ws:
                        try:
                            await client.send_json({
                                "type": "typing",
                                "user": data["user"]
                            })
                        except:
                            pass

    except:
        if ws in clients[room]:
            clients[room].remove(ws)
