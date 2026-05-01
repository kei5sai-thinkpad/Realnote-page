from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth
import os

from database import *

init_db()

app = FastAPI()

# 🔐 強いキー（本番は.env推奨）
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY", "supersecret123456789"))

clients = {}

# ===== OAuth =====
oauth = OAuth()

oauth.register(
    name="github",
    client_id=os.getenv("Ov23liEVy4XOFTYLuyTM"),
    client_secret=os.getenv("17a3ff75aa684e88b2121fbf3aa1528d1cb2c6aa"),
    access_token_url="https://github.com/login/oauth/access_token",
    authorize_url="https://github.com/login/oauth/authorize",
    api_base_url="https://api.github.com/",
    client_kwargs={"scope": "user:email"},
)

# ===== login =====
@app.get("/login")
async def login(request: Request):
    redirect_uri = request.url_for("auth_callback")
    return await oauth.github.authorize_redirect(request, redirect_uri)

# ===== callback =====
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

# ===== home =====
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

# ===== app（最低限ちゃんと動くHTML）=====
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

    <h2>ノートアプリ</h2>
    <div id="note" contenteditable="true"></div>

    <script>
    let ws;

    function connect(){
        ws = new WebSocket("ws://" + location.host + "/ws/main");

        ws.onmessage = (e)=>{
            const data = JSON.parse(e.data);
            document.getElementById("note").innerText = data.text;
        };

        document.getElementById("note").oninput = ()=>{
            ws.send(JSON.stringify({
                type:"update",
                text:document.getElementById("note").innerText
            }));
        };
    }

    connect();
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
        if room in clients and ws in clients[room]:
            clients[room].remove(ws)
