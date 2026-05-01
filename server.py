from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth

from database import *

init_db()

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="kokokaifvjpavioarivjhoia")

clients = {}

# ===== OAuth設定（GitHub）=====
oauth = OAuth()

oauth.register(
    name="github",
    client_id="Ov23liEVy4XOFTYLuyTM",
    client_secret="17a3ff75aa684e88b2121fbf3aa1528d1cb2c6aa",
    access_token_url="https://github.com/login/oauth/access_token",
    authorize_url="https://github.com/login/oauth/authorize",
    api_base_url="https://api.github.com/",
    client_kwargs={"scope": "user:email"},
)

# ===== ログイン =====
@app.get("/login")
async def login(request: Request):
    redirect_uri = request.url_for("auth_callback")
    return await oauth.github.authorize_redirect(request, redirect_uri)

# ===== コールバック =====
@app.get("/auth/callback")
async def auth_callback(request: Request):
    token = await oauth.github.authorize_access_token(request)
    resp = await oauth.github.get("user", token=token)
    user = resp.json()

    user_id = str(user["id"])
    name = user["login"]
    icon = user["avatar_url"]

    create_user(user_id, name, icon)

    request.session["user"] = user_id

    return RedirectResponse("/")

# ===== ホーム =====
@app.get("/")
async def home(request: Request):
    user_id = request.session.get("user")

    if not user_id:
        return HTMLResponse("""
        <h2>ログインしてください</h2>
        <a href="/login">GitHubでログイン</a>
        """)

    user = get_user(user_id)

    return HTMLResponse(f"""
    <h3>ようこそ {user[1]}</h3>
    <img src="{user[2]}" width="50" style="border-radius:50%"><br><br>

    <a href="/app">ノートへ</a>
    """)

# ===== ノートUI（ここに今のHTMLそのまま入れる）=====
@app.get("/app")
async def app_page(request: Request):
    user_id = request.session.get("user")

    if not user_id:
        return RedirectResponse("/")

    return HTMLResponse("""
    
let username = localStorage.getItem("notecord_username");

if (!username) {
    username = prompt("ユーザー名を入力してください");

    if (!username || username.trim() === "") {
        username = "User" + Math.floor(Math.random() * 1000);
    }

    localStorage.setItem("notecord_username", username);
}

function escapeHtml(text) {
    const div = document.createElement("div");
    div.innerText = text;
    return div.innerHTML;
}

function formatCodeBlocks(text) {
    const regex = new RegExp(
        "```([a-zA-Z0-9]+)?\\\\n([\\\\s\\\\S]*?)```",
        "g"
    );

    return text.replace(regex, function(match, lang, code) {
        return `
            <div style="
                background:#111827;
                border:1px solid #334155;
                border-radius:14px;
                margin:14px 0;
                overflow:hidden;
            ">
                <div style="
                    background:#0b1220;
                    padding:10px 14px;
                    border-bottom:1px solid #334155;
                    font-size:13px;
                    font-weight:bold;
                    color:#cbd5e1;
                ">
                    ${lang || "code"}
                </div>

                <pre style="
                    margin:0;
                    padding:16px;
                    font-family:Consolas, monospace;
                    font-size:14px;
                    line-height:1.7;
                    white-space:pre-wrap;
                    overflow-x:auto;
                    color:white;
                ">${escapeHtml(code)}</pre>
            </div>
        `;
    });
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
            note.innerHTML = formatCodeBlocks(data.text);
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
                text: note.innerText
            }));

            ws.send(JSON.stringify({
                type: "typing",
                user: username
            }));
        }
    };
}

/* 招待リンク */

function copyInviteLink() {
    if (!currentRoomName) {
        alert("先に部屋へ入室してください");
        return;
    }

    const inviteLink =
        location.origin + "/?room=" + encodeURIComponent(currentRoomName);

    navigator.clipboard.writeText(inviteLink)
        .then(() => {
            alert("招待リンクをコピーしました！");
        })
        .catch(() => {
            alert("コピーに失敗しました");
        });
}

/* URLから自動入室 */

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
    """)

# ===== WebSocket =====
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

                for client in clients[room]:
                    if client != ws:
                        await client.send_json(data)

    except:
        clients[room].remove(ws)
