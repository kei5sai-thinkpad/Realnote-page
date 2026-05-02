from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
import os
import firebase_admin
from firebase_admin import credentials, auth

from database import *

init_db()

app = FastAPI()

# ================= セッション（ログイン状態保持） =================
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY", "super-secret-key")
)

# ================= Firebase初期化 =================
cred = credentials.Certificate("firebase-key.json")
firebase_admin.initialize_app(cred)

clients = {}

# ================= ユーザー検証 =================
def verify_token(token: str):
    if not token:
        return None
    try:
        decoded = auth.verify_id_token(token)
        return decoded
    except:
        return None

# ================= home =================
@app.get("/")
async def home(request: Request):
    return HTMLResponse("""
    <h2>Real Note</h2>
    <a href="/app">アプリへ</a>
    """)

# ================= app =================
@app.get("/app")
async def app_page():
    html = open("index.html", encoding="utf-8").read()
    return HTMLResponse(html)

# ================= websocket =================
@app.websocket("/ws/{room}")
async def websocket(ws: WebSocket, room: str):
    await ws.accept()

    # 🔐 Firebaseトークン取得
    token = ws.query_params.get("token")
    user = verify_token(token)

    if not user:
        await ws.close()
        return

    user_id = user["uid"]
    username = user.get("name", "User")

    # room初期化
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

            # ===== ノート更新 =====
            if data["type"] == "update":
                save_note(room, data["text"])

                for client in clients[room]:
                    if client != ws:
                        await client.send_json({
                            "type": "update",
                            "text": data["text"]
                        })

            # ===== 入力中 =====
            if data["type"] == "typing":
                for client in clients[room]:
                    if client != ws:
                        await client.send_json({
                            "type": "typing",
                            "user": username
                        })

    except:
        if ws in clients[room]:
            clients[room].remove(ws)
