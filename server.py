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

/* サイドバー */
.sidebar {
    width: 220px;
    background: #020617;
    padding: 15px;
    box-sizing: border-box;
}

.sidebar h2 {
    font-size: 16px;
    margin-bottom: 10px;
}

.room {
    padding: 8px;
    border-radius: 8px;
    cursor: pointer;
    margin-bottom: 5px;
}

.room:hover {
    background: #1e293b;
}

/* メイン */
.main {
    flex: 1;
    display: flex;
    flex-direction: column;
}

/* ヘッダー */
.header {
    padding: 15px;
    background: #020617;
    border-bottom: 1px solid #1e293b;
}

/* ノート */
textarea {
    flex: 1;
    border: none;
    padding: 20px;
    background: #0f172a;
    color: white;
    font-size: 16px;
    resize: none;
}

textarea:focus {
    outline: none;
}

/* 入力 */
.add-room {
    display: flex;
    gap: 5px;
    margin-top: 10px;
}

input {
    flex: 1;
    padding: 8px;
    border-radius: 8px;
    border: none;
    background: #1e293b;
    color: white;
}

button {
    padding: 8px 10px;
    border: none;
    border-radius: 8px;
    background: #3b82f6;
    color: white;
    cursor: pointer;
}
</style>
</head>

<body>

<div class="sidebar">
    <h2>📁 Rooms</h2>
    <div id="rooms"></div>

    <div class="add-room">
        <input id="roomInput" placeholder="new room">
        <button onclick="addRoom()">＋</button>
    </div>
</div>

<div class="main">
    <div class="header">
        <span id="currentRoom">未接続</span>
    </div>

    <textarea id="note" placeholder="ここに入力..."></textarea>
</div>

<script>
let ws;
let isUpdating = false;
let rooms = ["general"];

function renderRooms() {
    const container = document.getElementById("rooms");
    container.innerHTML = "";

    rooms.forEach(room => {
        const div = document.createElement("div");
        div.className = "room";
        div.innerText = "# " + room;
        div.onclick = () => joinRoom(room);
        container.appendChild(div);
    });
}

function addRoom() {
    const input = document.getElementById("roomInput");
    const name = input.value.trim();
    if (!name) return;

    rooms.push(name);
    input.value = "";
    renderRooms();
}

function joinRoom(room) {
    document.getElementById("currentRoom").innerText = "# " + room;
    const note = document.getElementById("note");

    if (ws) {
        ws.close();
    }

    ws = new WebSocket(
        (location.protocol === "https:" ? "wss://" : "ws://")
        + location.host + "/ws/" + room
    );

    ws.onmessage = (event) => {
        isUpdating = true;
        note.value = event.data;
        isUpdating = false;
    };

    note.oninput = () => {
        if (ws && ws.readyState === WebSocket.OPEN && !isUpdating) {
            ws.send(note.value);
        }
    };
}

renderRooms();
</script>

</body>
</html>
"""

clients = {}
notes = {}

@app.get("/")
async def get():
    return HTMLResponse(html)

@app.websocket("/ws/{room}")
async def websocket(ws: WebSocket, room: str):
    await ws.accept()

    if room not in clients:
        clients[room] = []
        notes[room] = ""

    clients[room].append(ws)

    await ws.send_text(notes[room])

    try:
        while True:
            data = await ws.receive_text()
            notes[room] = data

            # 全員に送信
            for client in clients[room]:
                await client.send_text(notes[room])

    except:
        clients[room].remove(ws)
