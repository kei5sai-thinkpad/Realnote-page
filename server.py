from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
import os
import secrets

from database import *
from fastapi.responses import RedirectResponse

@app.get("/")
async def root():
    return RedirectResponse("/app")

init_db()

app = FastAPI()

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY", "super-secret-key")
)

# ================= GitHub OAuth（仮） =================
# ※ここは既存のoauthコード使ってOK

# ================= login callback =================
@app.get("/auth/callback")
async def callback(request: Request):
    # GitHub user取得済み想定
    user = {
        "id": "123",
        "login": "testuser",
        "avatar_url": ""
    }

    user_id = str(user["id"])
    name = user["login"]
    icon = user["avatar_url"]

    # 🔥 refresh token生成
    refresh_token = secrets.token_hex(32)

    create_user(user_id, name, icon, refresh_token)

    request.session["user"] = user_id

    return RedirectResponse("/app")

# ================= restore login =================
@app.post("/auth/restore")
async def restore(data: dict):
    token = data.get("token")

    user = get_user_by_token(token)

    if not user:
        return {"ok": False}

    return {
        "ok": True,
        "user": {
            "id": user[0],
            "name": user[1],
            "icon": user[2]
        }
    }

# ================= me =================
@app.get("/me")
async def me(request: Request):
    user_id = request.session.get("user")

    if not user_id:
        return {"logged_in": False}

    user = get_user(user_id)

    return {
        "logged_in": True,
        "user": {
            "id": user[0],
            "name": user[1],
            "icon": user[2]
        }
    }
