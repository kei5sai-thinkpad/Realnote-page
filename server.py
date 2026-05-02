from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth
import os

from database import *

init_db()

app = FastAPI()

# ================= セッション =================
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY", "super-secret-key"),
    same_site="lax",
    https_only=True
)

clients = {}

# ================= OAuth =================
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

# ================= login =================
@app.get("/login/github")
async def login_github(request: Request):
    redirect_uri = request.url_for("auth_callback")
    return await oauth.github.authorize_redirect(request, redirect_uri)

# ================= callback =================
@app.get("/auth/callback")
async def auth_callback(request: Request):
    token = await oauth.github.authorize_access_token(request)
    resp = await oauth.github.get("user", token=token)
    user = resp.json()

    user_id = str(user["id"])
    username = user["login"]
    icon = user["avatar_url"]

    create_user(user_id, username, icon)

    request.session["user"] = user_id
    request.session["username"] = username

    return RedirectResponse("/app")

# ================= logout =================
@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/")

# ================= home =================
@app.get("/")
async def home(request: Request):
    return RedirectResponse("/app")

# ================= app =================
@app.get("/app")
async def app_page(request: Request):
    user_id = request.session.get("user")

    if not user_id:
        return RedirectResponse("/")

    user = get_user(user_id)

    # 👇 これ超重要
    if not user:
        username = request.session.get("username", "User")

        create_user(user_id, username, "")

        user = get_user(user_id)

    html = open("index.html", encoding="utf-8").read()

    html = html.replace(
        "let username = null;",
        f'let username = "{user[1]}";'
    )

    return HTMLResponse(html)

# ================= rooms =================
@app.get("/rooms")
def rooms():
    return get_rooms()

@app.post("/join-room")
async def join_room(data: dict):
    return join_or_create_room(
        data.get("room"),
        data.get("password", ""),
        data.get("room_type")
    )

# ================= websocket =================
@app.websocket("/ws/{room}")
async def ws(ws: WebSocket, room: str):
    await ws.accept()

    clients.setdefault(room, set()).add(ws)

    await ws.send_json({
        "type": "init",
        "text": get_note(room)
    })

    try:
        while True:
            data = await ws.receive_json()

            if data["type"] == "update":
                save_note(room, data["text"])

                for c in list(clients[room]):
                    if c != ws:
                        await c.send_json(data)

            elif data["type"] == "typing":
                for c in list(clients[room]):
                    if c != ws:
                        await c.send_json(data)

    except WebSocketDisconnect:
        clients[room].remove(ws)

        if not clients[room]:
            del clients[room]
