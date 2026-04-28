# server.py（必要部分のみ修正版：リアルタイム共有復活 + placeholder修正）

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

#note:empty:before {
    content: attr(data-placeholder);
    color: #94a3b8;
    pointer-events: none;
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

#introScreen {
    position: fixed;
    inset: 0;
    backdrop-filter: blur(14px);
    background: rgba(2, 6, 23, 0.72);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 9999;
    animation: fadeOutIntro 2.8s ease forwards;
    animation-delay: 1.5s;
}

#introTitle {
    font-size: 52px;
    font-weight: 700;
    letter-spacing: 2px;
    color: white;
    animation: titleFade 1.4s ease;
}

@keyframes fadeOutIntro {
    to {
        opacity: 0;
        visibility: hidden;
    }
}

@keyframes titleFade {
    from {
        opacity: 0;
        transform: translateY(20px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}
</style>
</head>
<body>

<div id="introScreen">
    <div id="introTitle">
        Real note
    </div>
</div>

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

        <div style="display:flex; gap:10px; align-items:center;">
            <button onclick="copyInviteLink()" style="width:auto;">
                招待リンク
            </button>

            <span id="modeLabel"></span>
        </div>
    </div>

    <div
        id="note"
        contenteditable="true"
        data-placeholder="ノートに入室した時に表示されます"
    ></div>

    <div class="typing" id="typing"></div>
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

function connectRoom(room) {
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
            note.innerText = data.text || "";
            isUpdating = false;
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
                text: note.innerText
            }));
        }
    };
}

async function accessRoom() {
    const room = document.getElementById("roomInput").value.trim();
    const type = document.getElementById("roomType").value;

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
            room_type: type,
            username: username
        })
    });

    const result = await res.json();

    if (!result.success) {
        alert(result.message);
        return;
    }

    currentRoomName = room;

    document.getElementById("currentRoom").innerText = "# " + room;
    document.getElementById("modeLabel").innerText = result.label;

    connectRoom(room);
    loadRooms();
}

window.onload = async () => {
    await loadRooms();

    const params = new URLSearchParams(window.location.search);
    const room = params.get("room");

    if (room) {
        document.getElementById("roomInput").value = room;
        accessRoom();
    }
};
</script>

</body>
</html>
"""
