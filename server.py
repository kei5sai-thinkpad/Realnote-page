# server.py（招待リンクでパスワード不要版）

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

clients = {}

html = """
<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<title>NoteCord</title>
</head>
<body>

<div class="main">
    <div class="header">
        <span id="currentRoom">未接続</span>
        <button onclick="copyInviteLink()">招待リンク</button>
        <span id="modeLabel"></span>
    </div>

    <div id="note" contenteditable="true">
        ノートに入室した時に表示されます
    </div>
</div>

<script>
let ws;
let isUpdating = false;
let currentRoomName = "";
let username = localStorage.getItem("notecord_username");

if (!username) {
    username = prompt("ユーザー名を入力してください");

    if (!username || username.trim() === "") {
        username = "User" + Math.floor(Math.random() * 1000);
    }

    localStorage.setItem("notecord_username", username);
}

function copyInviteLink() {
    if (!currentRoomName) {
        alert("先に部屋へ入室してください");
        return;
    }

    const inviteLink =
        location.origin
        + "/?room="
        + encodeURIComponent(currentRoomName)
        + "&invite=1";

    navigator.clipboard.writeText(inviteLink)
        .then(() => {
            alert("招待リンクをコピーしました");
        })
        .catch(() => {
            alert("コピーに失敗しました");
        });
}

async function accessRoom() {
    const room = document.getElementById("roomInput").value.trim();

    if (!room) {
        alert("部屋名を入力してください");
        return;
    }

    const params = new URLSearchParams(window.location.search);
    const isInvite = params.get("invite") === "1";

    let password = "";

    if (!isInvite) {
        password = prompt("パスワード（空でもOK）を入力してください") || "";
    }

    const res = await fetch("/join-room", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            room: room,
            password: password,
            room_type: "shared",
            username: username
        })
    });

    const result = await res.json();

    if (!result.success) {
        alert(result.message);
        return;
    }

    connectRoom(room, result.can_edit, result.label);
}

function connectRoom(room, canEdit, label) {
    currentRoomName = room;

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
            note.innerText = data.text;
            isUpdating = false;
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
        }
    };
}

window.onload = () => {
    const params = new URLSearchParams(window.location.search);
    const room = params.get("room");

    if (room) {
        const hiddenInput = document.createElement("input");
        hiddenInput.id = "roomInput";
        hiddenInput.value = room;
        hiddenInput.style.display = "none";
        document.body.appendChild(hiddenInput);

        accessRoom();
    }
};
</script>

</body>
</html>
"""


class RoomData(BaseModel):
    room: str
    password: str = ""
    room_type: str
    username: str


@app.get("/")
async def home():
    return HTMLResponse(html)


@app.post("/join-room")
async def join_room(data: RoomData):
    room = data.room.strip()
    password = data.password.strip()
    room_type = data.room_type
    username = data.username

    room_data = get_room(room)

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

    return {
        "success": True,
        "can_edit": True,
        "label": "共有ノート"
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

    except:
        if ws in clients[room]:
            clients[room].remove(ws)
