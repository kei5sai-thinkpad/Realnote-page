from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse

app = FastAPI()

html = """
<!DOCTYPE html>
<html>
<body>
<h2>リアルタイム共有ノート</h2>

<input id="room" placeholder="ルーム名">
<button onclick="joinRoom()">参加</button>

<br><br>
<textarea id="note" style="width:100%;height:300px;"></textarea>

<script>
let ws;

function joinRoom() {
    const room = document.getElementById("room").value;
    const note = document.getElementById("note");

    ws = new WebSocket(
        (location.protocol === "https:" ? "wss://" : "ws://")
        + location.host + "/ws/" + room
    );

    ws.onmessage = (event) => {
        note.value = event.data;
    };

    note.oninput = () => {
        if (ws && ws.readyState === WebSocket.OPEN) {
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

    # 初期データ送信
    await ws.send_text(notes[room])

    try:
        while True:
            data = await ws.receive_text()
            notes[room] = data

            for client in clients[room]:
                await client.send_text(notes[room])

    except:
        clients[room].remove(ws)
