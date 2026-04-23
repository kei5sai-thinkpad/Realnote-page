from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse

app = FastAPI()

html = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>共有ノート</title>
</head>
<body>

<h2>リアルタイム共有ノート</h2>

<input id="room" placeholder="ルーム名">
<button onclick="joinRoom()">参加</button>

<br><br>
<textarea id="note" style="width:100%;height:300px;"></textarea>

<script>
let ws;
let isUpdating = false;

function joinRoom() {
    const room = document.getElementById("room").value;
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
