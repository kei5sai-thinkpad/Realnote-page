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
    width: 240px;
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
    transition: 0.2s;
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
        placeholder="new room"
        onkeydown="if(event.key==='Enter') addRoom()"
    >
</div>

<div class="main">

    <div class="header">
        <span id="currentRoom"># general</span>

        <div class="header-buttons">
            <button onclick="highlightText('yellow')">🟨 黄</button>
            <button onclick="highlightText('lightgreen')">🟩 緑</button>
            <button onclick="highlightText('lightblue')">🟦 青</button>

            <button onclick="downloadTXT()">📝 TXT保存</button>
            <button onclick="downloadPDF()">📄 PDF保存</button>
        </div>
    </div>

    <div
        id="note"
        contenteditable="true"
    ></div>

    <div class="typing" id="typing"></div>

</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"></script>

<script>
let ws;
let isUpdating = false;
let username = "User" + Math.floor(Math.random() * 1000);
let rooms = ["general"];


/* ---------- 蛍光ペン ---------- */

function highlightText(color) {
    document.execCommand("hiliteColor", false, color);
}


/* ---------- 部屋一覧 ---------- */

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

    if (rooms.includes(name)) {
        alert("その部屋はすでにあります");
        return;
    }

    rooms.push(name);
    input.value = "";
    renderRooms();
}


/* ---------- 部屋接続 ---------- */

function joinRoom(room) {
    document.getElementById("currentRoom").innerText = "# " + room;
    const note = document.getElementById("note");

    if (ws) {
        ws.close();
    }

    ws = new WebSocket(
        (location.protocol === "https:" ? "wss://" : "ws://")
        + location.host
        + "/ws/"
        + room
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

            clearTimeout(window.typingTimer);
            window.typingTimer = setTimeout(() => {
                typingDiv.innerText = "";
            }, 1200);
        }
    };

    note.oninput = () => {
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


/* ---------- TXT保存 ---------- */

function downloadTXT() {
    const text = document.getElementById("note").innerText;
    const room = document.getElementById("currentRoom").innerText.replace("# ", "");
    const date = new Date().toISOString().slice(0, 10);

    const blob = new Blob([text], {
        type: "text/plain"
    });

    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = room + "_" + date + ".txt";
    a.click();
}


/* ---------- PDF保存 ---------- */

function downloadPDF() {
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF();

    const text = document.getElementById("note").innerText || "空のノート";
    const room = document.getElementById("currentRoom").innerText.replace("# ", "");
    const date = new Date().toISOString().slice(0, 10);

    const lines = doc.splitTextToSize(text, 180);

    doc.setFontSize(12);
    doc.text(lines, 10, 15);

    doc.save(room + "_" + date + ".pdf");
}


/* ---------- 初期化 ---------- */

renderRooms();
joinRoom("general");
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

                for client in clients[room][:]:
                    if client != ws:  # ← 自分には返さない
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
