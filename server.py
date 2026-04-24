from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse

app = FastAPI()

html = """
<!DOCTYPE html>
<html>
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
    width: 260px;
    background: #020617;
    padding: 15px;
    border-right: 1px solid #1e293b;
}

.room {
    padding: 10px;
    border-radius: 10px;
    cursor: pointer;
    margin-bottom: 6px;
    transition: 0.2s;
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

.header-buttons {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
}

#note {
    flex: 1;
    padding: 20px;
    background: #0f172a;
    color: white;
    font-size: 16px;
    line-height: 1.6;
    outline: none;
    overflow: auto;
    white-space: pre-wrap;
}

.typing {
    padding: 10px 20px;
    color: #94a3b8;
    min-height: 24px;
}

button {
    background: #3b82f6;
    border: none;
    padding: 10px 14px;
    border-radius: 10px;
    color: white;
    cursor: pointer;
    font-weight: bold;
}

button:hover {
    background: #2563eb;
}

input {
    width: 100%;
    padding: 10px;
    margin-top: 12px;
    border-radius: 10px;
    border: none;
    outline: none;
    background: #1e293b;
    color: white;
    box-sizing: border-box;
}

h3 {
    margin-top: 0;
}
</style>
</head>
<body>

<div class="sidebar">
    <h3>Rooms</h3>
    <div id="rooms"></div>

    <input
        id="roomInput"
        placeholder="部屋名を入力"
        onkeydown="if(event.key==='Enter') accessRoom()"
    >
</div>

<div class="main">

    <div class="header">
        <span id="currentRoom">未接続</span>

        <div class="header-buttons">
            <button onclick="highlightText('yellow')">🟨 黄</button>
            <button onclick="highlightText('lightgreen')">🟩 緑</button>
            <button onclick="highlightText('lightblue')">🟦 青</button>
        </div>
    </div>

    <div id="note" contenteditable="true"></div>
    <div class="typing" id="typing"></div>

</div>

<script>
let ws;
let username = "User" + Math.floor(Math.random() * 1000);
let rooms = [];
let isUpdating = false;

function highlightText(color) {
    document.execCommand("hiliteColor", false, color);
}

function renderRooms() {
    const container = document.getElementById("rooms");
    container.innerHTML = "";

    rooms.forEach(room => {
        const div = document.createElement("div");
        div.className = "room";
        div.innerText = "# " + room;
        div.onclick = () => accessRoom(room);
        container.appendChild(div);
    });
}

async function loadRooms() {
    const res = await fetch("/rooms");
    rooms = await res.json();
    renderRooms();
}

async function accessRoom(clickedRoom = null) {
    let room = clickedRoom || document.getElementById("roomInput").value.trim();

    if (!room) return;

    let password = prompt("パスワードを入力してください");

    if (!password) return;

    const res = await fetch("/join-room", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            room: room,
            password: password
        })
    });

    const result = await res.json();

    if (!result.success) {
        alert(result.message);
        return;
    }

    joinRoom(room);
    loadRooms();
}

function joinRoom(room) {
    document.getElementById("currentRoom").innerText = "# " + room;
    const note = document.getElementById("note");

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
            const typingDiv = document.getElementById("typing");
            typingDiv.innerText = data.user + " が入力中...";
            setTimeout(() => typingDiv.innerText = "", 1000);
        }
    };

    note.oninput = () => {
        if (ws && ws.readyState === WebSocket.OPEN && !isUpdating) {
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

clients = {}
notes = {}
room_passwords = {}

from pydantic import BaseModel

class RoomData(BaseModel):
    room: str
    password: str


@app.get("/")
async def get():
    return HTMLResponse(html)


@app.get("/rooms")
async def get_rooms():
    return list(room_passwords.keys())


@app.post("/join-room")
async def join_room(data: RoomData):
    room = data.room.strip()
    password = data.password.strip()

    if not room or not password:
        return {
            "success": False,
            "message": "部屋名とパスワードを入力してください"
        }

    if room not in room_passwords:
        room_passwords[room] = password
        notes[room] = ""
        clients[room] = []

        return {
            "success": True,
            "message": "新しい部屋を作成しました"
        }

    if room_passwords[room] != password:
        return {
            "success": False,
            "message": "パスワードが違います"
        }

    return {
        "success": True,
        "message": "入室成功"
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
