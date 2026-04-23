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
    width: 220px;
    background: #020617;
    padding: 15px;
}

.room {
    padding: 8px;
    border-radius: 8px;
    cursor: pointer;
}
.room:hover { background: #1e293b; }

.main {
    flex: 1;
    display: flex;
    flex-direction: column;
}

.header {
    padding: 15px;
    background: #020617;
    border-bottom: 1px solid #1e293b;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

textarea {
    flex: 1;
    border: none;
    padding: 20px;
    background: #0f172a;
    color: white;
    font-size: 16px;
}

.typing {
    padding: 10px;
    color: #94a3b8;
}

button {
    background: #3b82f6;
    border: none;
    padding: 8px 12px;
    border-radius: 8px;
    color: white;
    cursor: pointer;
}

input {
    width: 100%;
    padding: 8px;
    margin-top: 10px;
    border-radius: 8px;
    border: none;
    background: #1e293b;
    color: white;
}
</style>
</head>

<body>

<div class="sidebar">
    <h3>Rooms</h3>
    <div id="rooms"></div>
    <input id="roomInput" placeholder="new room" onkeydown="if(event.key==='Enter') addRoom()">
</div>

<div class="main">
    <div class="header">
        <span id="currentRoom">未接続</span>
        <button onclick="downloadPDF()">📄 PDF保存</button>
    </div>

    <textarea id="note"></textarea>
    <div class="typing" id="typing"></div>
</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"></script>

<script>
let ws;
let isUpdating = false;
let username = "User" + Math.floor(Math.random()*1000);
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

    if (ws) ws.close();

    ws = new WebSocket(
        (location.protocol === "https:" ? "wss://" : "ws://")
        + location.host + "/ws/" + room
    );

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);

        if (data.type === "init" || data.type === "update") {
            isUpdating = true;
            note.value = data.text;
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
                text: note.value
            }));

            ws.send(JSON.stringify({
                type: "typing",
                user: username
            }));
        }
    };
}

// PDF保存
function downloadPDF() {
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF();

    const text = document.getElementById("note").value;
    const room = document.getElementById("currentRoom").innerText;

    const lines = doc.splitTextToSize(text, 180);

    doc.text(lines, 10, 10);

    const date = new Date().toISOString().slice(0,10);
    doc.save(room + "_" + date + ".pdf");
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

    await ws.send_json({
        "type": "init",
        "text": notes[room]
    })

    try:
        while True:
            data = await ws.receive_json()

            if data["type"] == "update":
                notes[room] = data["text"]
                for client in clients[room]:
                    await client.send_json({
                        "type": "update",
                        "text": notes[room]
                    })

            if data["type"] == "typing":
                for client in clients[room]:
                    if client != ws:
                        await client.send_json({
                            "type": "typing",
                            "user": data["user"]
                        })

    except:
        clients[room].remove(ws)
