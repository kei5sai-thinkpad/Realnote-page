from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
import os

from database import (
    init_db,
    get_rooms,
    join_or_create_room,
    get_note,
    save_note
)

# ================= 初期化 =================
init_db()

app = FastAPI()

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY", "super-secret-key")
)

clients = {}

# ================= root =================
@app.get("/")
async def root():
    return RedirectResponse("/app")

@app.get("/app")
async def app_page():
    with open("index.html", encoding="utf-8") as f:
        return HTMLResponse(f.read())

# ================= rooms =================
@app.get("/rooms")
def rooms():
    return get_rooms()

# ================= join =================
@app.post("/join-room")
async def join_room(data: dict):
    room = data.get("room")
    password = data.get("password", "")
    room_type = data.get("room_type", "shared")

    if not room:
        return {"success": False, "message": "room required"}

    return join_or_create_room(room, password, room_type)

# ================= websocket =================
@app.websocket("/ws/{room}")
async def ws_endpoint(ws: WebSocket, room: str):
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

            if data["type"] == "update":
                save_note(room, data["text"])

                for c in list(clients[room]):
                    if c != ws:
                        await c.send_json({
                            "type": "update",
                            "text": data["text"]
                        })

            elif data["type"] == "typing":
                for c in list(clients[room]):
                    if c != ws:
                        await c.send_json({
                            "type": "typing",
                            "user": data.get("user", "User")
                        })

    except WebSocketDisconnect:
        clients[room].discard(ws)

        if not clients[room]:
            del clients[room]
