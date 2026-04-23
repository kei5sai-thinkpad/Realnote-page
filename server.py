# Realnote-pagefrom fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse

app = FastAPI()

html = """
<!DOCTYPE html>
<html>
<head>
    <title>共有ノート</title>
</head>
<body>
    <h1>リアルタイムノート</h1>

    <input id="room" placeholder="ルーム名を入力" />
    <button onclick="joinRoom()">参加</button>

    <br><br>
    <textarea id="note" style="width:100%;height:300px;"></textarea>

    <script>
        let ws;
        let currentRoom = "";

        function joinRoom() {
            const room = document.getElementById("room").value;
            currentRoom = room;

            if (ws) {
                ws.close();
            }

            ws = new WebSocket(`ws://localhost:8000/ws/${room}`);
            const note = document.getElementById("note");

            ws.onmessage = (event) => {
                note.value = event.data;
            };

            note.addEventListener("input", () => {
                ws.send(note.value);
            });
        }
    </script>
</body>
</html>
"""

clients = {}  # {room: [WebSocket,...]}
notes = {}    # {room: text}

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

    # 現在のノート送信
    await ws.send_text(notes[room])

    try:
        while True:
            data = await ws.receive_text()
            notes[room] = data

            for client in clients[room]:
                await client.send_text(notes[room])

    except:
        clients[room].remove(ws)
