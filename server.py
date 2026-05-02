from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
import os

from database import *

init_db()

app = FastAPI()

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY", "super-secret-key")
)

clients = {}

# ================= rooms =================
@app.get("/rooms")
def rooms():
    return get_rooms()

# ================= join =================
@app.post("/join-room")
async def join_room(data: dict):
    room = data.get("room")
    password = data.get("password", "")
    room_type = data.get("room_type")

    if not room:
        return {"success": False, "message": "room required"}

    return join_or_create_room(room, password, room_type)

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
                        await c.send_json({
                            "type": "update",
                            "text": data["text"]
                        })

            elif data["type"] == "typing":
                for c in list(clients[room]):
                    if c != ws:
                        await c.send_json(data)

    except WebSocketDisconnect:
        clients[room].remove(ws)

        if not clients[room]:
            del clients[room]
