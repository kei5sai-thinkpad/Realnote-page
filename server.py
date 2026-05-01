from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth
import os

from database import *

init_db()

app = FastAPI()

# =============================
# セッション（重要）
# =============================
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY", "super-secret-key")
)

clients = {}

# =============================
# OAuth（GitHub）
# =============================
oauth = OAuth()

oauth.register(
    name="github",
    client_id=os.getenv("GITHUB_CLIENT_ID"),
    client_secret=os.getenv("GITHUB_CLIENT_SECRET"),
    access_token_url="https://github.com/login/oauth/access_token",
    authorize_url="https://github.com/login/oauth/authorize",
    api_base_url="https://api.github.com/",
    client_kwargs={"scope": "user:email"},
)

# =============================
# ログイン
# =============================
@app.get("/login")
async def login(request: Request):
    redirect_uri = request.url_for("auth_callback")
    return await oauth.github.authorize_redirect(request, redirect_uri)

# =============================
# コールバック
# =============================
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

# =============================
# ホーム
# =============================
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
    <img src="{user[2]}" width="60" style="border-radius:50%">
    <br><br>
    <a href="/app">ノートへ</a>
    """)

# =============================
# アプリ画面
# =============================
@app.get("/app")
async def app_page(request: Request):
    if not request.session.get("user"):
        return RedirectResponse("/")

    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="UTF-8">
    </head>
    <body>

    <h2>リアルタイムノート</h2>

    <div id="note" contenteditable="true"
        style="border:1px solid #ccc; padding:10px; height:200px;">
    </div>

    <script>
    let ws = new WebSocket(
        (location.protocol === "https:" ? "wss://" : "ws://")
        + location.host + "/ws/main"
    );

    ws.onmessage = (e) => {
        const data = JSON.parse(e.data);
        document.getElementById("note").innerText = data.text;
    };

    document.getElementById("note").oninput = () => {
        ws.send(JSON.stringify({
            type: "update",
            text: document.getElementById("note").innerText
        }));
    };
    </script>

    </body>
    </html>
    """)

# =============================
# WebSocket
# =============================
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
                        await client.send_json({
                            "text": data["text"]
                        })

    except:
        if ws in clients[room]:
            clients[room].remove(ws)
