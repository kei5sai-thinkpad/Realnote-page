from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth
import os
import requests

from database import *

init_db()

app = FastAPI()

# ================= セッション =================
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY", "super-secret-key")
)

clients = {}  # room -> set(ws)

# ================= GitHub OAuth =================
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

# ================= Supabase（ここ重要修正） =================
SUPABASE_URL = "https://qwoasmceczpcvkuufvkt.supabase.co"
SUPABASE_ANON_KEY = "sb_publishable_U3eBuQImXzRhe7irveKkYQ_cw0RVyem"

def verify_supabase_token(token: str):
    if not token:
        return None

    headers = {
        "Authorization": f"Bearer {token}",
        "apikey": SUPABASE_ANON_KEY
    }

    res = requests.get(
        f"{SUPABASE_URL}/auth/v1/user",
        headers=headers
    )

    if res.status_code != 200:
        return None

    return res.json()

# ================= GitHub login =================
@app.get("/login")
async def login(request: Request):
    redirect_uri = request.url_for("auth_callback")
    return await oauth.github.authorize_redirect(request, redirect_uri)

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
    request.session["username"] = name

    return RedirectResponse("/app")

# ================= Supabase login =================
@app.post("/auth/supabase")
async def supabase_login(data: dict):
    token = data.get("token")

    user = verify_supabase_token(token)

    if not user:
        raise HTTPException(status_code=401, detail="invalid token")

    return {
        "success": True,
        "user_id": user["id"],
        "email": user.get("email")
    }

# ================= home =================
@app.get("/")
async def home(request: Request):
    if not request.session.get("user"):
        return HTMLResponse("""
        <h2>ログインしてください</h2>
        <a href="/login">GitHubでログイン</a>
        """)

    return RedirectResponse("/app")

# ================= app =================
@app.get("/app")
async def app_page(request: Request):
    user_id = request.session.get("user")

    if not user_id:
        return RedirectResponse("/")

    user = get_user(user_id)

    if not user:
        username = request.session.get("username", "User")
        create_user(user_id, username, "")
        user = get_user(user_id)

    username = request.session.get("username", user[1])

    html = open("index.html", encoding="utf-8").read()

    html = html.replace(
        "let username = null;",
        f'let username = "{username}";'
    )

    return HTMLResponse(html)

# ================= rooms =================
@app.get("/rooms")
def get_rooms_api():
    return get_rooms()

@app.post("/join-room")
async def join_room(data: dict):
    room = data["room"]
    password = data.get("password", "")
    room_type = data["room_type"]

    return join_or_create_room(room, password, room_type)

# ================= websocket =================
@app.websocket("/ws/{room}")
async def websocket_endpoint(ws: WebSocket, room: str):
    await ws.accept()

    if room not in clients:
        clients[room] = set()

    clients[room].add(ws)

    await ws.send_json({
        "type": "init",
        "text": get_note(room)
    })

    try:
        while True:
            data = await ws.receive_json()

            # ===== 更新 =====
            if data["type"] == "update":
                save_note(room, data["text"])

                for client in list(clients[room]):
                    if client != ws:
                        await client.send_json({
                            "type": "update",
                            "text": data["text"]
                        })

            # ===== typing =====
            elif data["type"] == "typing":
                for client in list(clients[room]):
                    if client != ws:
                        await client.send_json({
                            "type": "typing",
                            "user": data.get("user", "User")
                        })

    except WebSocketDisconnect:
        clients[room].discard(ws)

        if len(clients[room]) == 0:
            del clients[room]
