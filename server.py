from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app = FastAPI()

# ----------------------------
# データ保存
# ----------------------------
clients = {}
notes = {}
room_passwords = {}
room_types = {}      # shared / readonly
room_owners = {}     # 作成者 username


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
let currentRoom = "";
let isUpdating = false;

/* ----------------------------
ユーザー名
---------------------------- */

let username = localStorage.getItem("notecord_username");

if (!username) {
    username = prompt("ユーザー名を入力してください");

    if (!username || username.trim() === "") {
        username = "User" + Math.floor(Math.random() * 1000);
    }

    localStorage.setItem("notecord_username", username);
}


/* ----------------------------
部屋一覧
---------------------------- */

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


/* ----------------------------
入室 / 作成
---------------------------- */

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


/* ----------------------------
接続
---------------------------- */

function connectRoom(room, canEdit, label) {
    currentRoom = room;

    document.getElementById("currentRoom").innerText = "# " + room;
    document.getElementById("modeLabel").innerText = label;

    const note = document.getElementById("note");

    note.contentEditable = canEdit ? "true" : "false";

    if (!canEdit) {
        note.style.opacity = "0.9";
        note.style.border = "2px solid #334155";
    } else {
        note.style.opacity = "1";
        note.style.border = "none";
    }

    if (ws) ws.close();

    ws = new WebSocket(
        (location.protocol === "https:" ? "wss://" : "ws://")
        + location.host + "/ws/" + room
    );

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);

        if (data.type === "init" || data.type === "update") {
            isUpdating = true;
            note.innerHTML = data.text;
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
                text: note.innerHTML
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
    result = []

    for room in room_passwords:
        t = room_types.get(room, "shared")

        result.append({
            "name": room,
            "label": "閲覧専用" if t == "readonly" else "共有"
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

    # 初回作成
    if room not in room_passwords:
        room_passwords[room] = password  # 空文字でも保存
        room_types[room] = room_type
        room_owners[room] = username
        notes[room] = ""
        clients[room] = []

        return {
            "success": True,
            "can_edit": True,
            "label": "作成者"
        }

    saved_password = room_passwords.get(room, "")

    # パスワード付き部屋 → 一致必須
    if saved_password != "":
        if saved_password != password:
            return {
                "success": False,
                "message": "パスワードが違います"
            }

    # パスワードなし部屋 → 誰でも入れる
    is_owner = room_owners.get(room) == username
    is_readonly = room_types.get(room) == "readonly"

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

    if room not in notes:
        notes[room] = ""

    clients[room].append(ws)

    await ws.send_json({
        "type": "init",
        "text": notes[room]
    })

    try:
        while True:
            data = await ws.receive_json()

            if data["type"] == "update":
                notes[room] = data["text"]

                for client in clients[room][:]:
                    if client != ws:
                        try:
                            await client.send_json({
                                "type": "update",
                                "text": notes[room]
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
