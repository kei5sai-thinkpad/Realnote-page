from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth
import asyncio
from datetime import datetime
import os

from database import *

init_db()

app = FastAPI()

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

@app.get("/login/github")
async def login_github(request: Request):
    return await oauth.github.authorize_redirect(
        request,
        request.url_for("auth_callback")
    )

@app.get("/auth/callback")
async def auth_callback(request: Request):
    token = await oauth.github.authorize_access_token(request)
    resp = await oauth.github.get("user", token=token)
    user = resp.json()

    create_user(str(user["id"]), user["login"], user["avatar_url"])

    request.session["user"] = str(user["id"])
    return RedirectResponse("/app")

# ================= pages =================
@app.get("/")
async def home(request: Request):
    if not request.session.get("user"):
        return HTMLResponse('<a href="/login/github">GitHubログイン</a>')
    return RedirectResponse("/app")

@app.get("/app")
async def app_page(request: Request):
    user_id = request.session.get("user")
    if not user_id:
        return RedirectResponse("/")

    user = get_user(user_id)

    if not user:
        request.session.clear()
        return RedirectResponse("/")

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

                for c in clients[room]:
                    if c != ws:
                        await c.send_json(data)

    except WebSocketDisconnect:
        clients[room].remove(ws)

# ================= Bot =================
async def news_bot():
    while True:
        try:
            room = "news-room"

            text = f"""📰 最新ニュース

更新: {datetime.now().strftime('%H:%M:%S')}

・AIが進化中
・新アプリ登場
・開発者爆増中
"""

            save_note(room, text)

            if room in clients:
                for c in clients[room]:
                    await c.send_json({
                        "type": "update",
                        "text": text
                    })

        except Exception as e:
            print("Bot error:", e)

        await asyncio.sleep(20)

@app.on_event("startup")
async def startup():
    asyncio.create_task(news_bot())
