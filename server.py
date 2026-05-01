from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth
from pydantic import BaseModel
import os

from database import *

init_db()

app = FastAPI()

# =============================
# セッション
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

    return RedirectResponse("/app")

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

    return RedirectResponse("/app")

# =============================
# HTML（そのまま使用）
# =============================
@app.get("/app")
async def app_page(request: Request):
    user_id = request.session.get("user")

    if not user_id:
        return RedirectResponse("/")

    user = get_user(user_id)

    html = open("index.html", encoding="utf-8").read()

    # usernameをJSに埋め込み
    html = html.replace(
        'let username = localStorage.getItem("notecord_username");',
        f'let username = "{user[1]}";'
    )

    return HTMLResponse(html)

# =============================
# Rooms API
# =============================
@app.get("/rooms")
async def get_rooms():
    rows = get_all_rooms()

    result = []
    for name, rtype in rows:
        result.append({
            "name": name,
            "label": "閲覧専用" if rtype == "readonly" else "共有"
        })

    return result

# =============================
# Join API
# =============================
class RoomData(BaseModel):
    room: str
    password: str = ""
    room_type: str
    username: str

@app.post("/join-room")
async def join_room(data: RoomData):
    room = data.room
    password = data.password
    room_type = data.room_type
    username = data.username

    room_data = get_room(room)

    # 新規
    if not room_data:
        create_room(room, password, room_type, username)

        return {
            "success": True,
            "can_edit": True,
            "label": "作成者"
        }

    saved_room, saved_password, saved_type, owner = room_data

    if saved_password != "" and saved_password != password:
        return {
            "success": False,
            "message": "パスワードが違います"
        }

    can_edit = True
    label = "共有"

    if saved_type == "readonly" and owner != username:
        can_edit = False
        label = "閲覧専用"

    if owner == username:
        label = "作成者"

    return {
        "success": True,
        "can_edit": can_edit,
        "label": label
    }

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
                            "type": "update",
                            "text": data["text"]
                        })

            if data["type"] == "typing":
                for client in clients[room]:
                    if client != ws:
                        await client.send_json({
                            "type": "typing",
                            "user": data["user"]
                        })

    except:
        if ws in clients[room]:
            clients[room].remove(ws)
