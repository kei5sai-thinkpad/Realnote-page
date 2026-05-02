from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth
import os

from database import *

init_db()

app = FastAPI()

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY", "super-secret-key")
)

# ================= OAuth設定 =================
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

# ================= GitHubログイン開始 =================
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
    name = user["login"]
    icon = user["avatar_url"]

    create_user(user_id, name, icon)

    request.session["user"] = user_id
    request.session["username"] = name

    return RedirectResponse("/app")

# ================= app =================
@app.get("/app")
async def app_page(request: Request):
    if not request.session.get("user"):
        return RedirectResponse("/")

    with open("index.html", encoding="utf-8") as f:
        html = f.read()

    username = request.session.get("username", "User")
    html = html.replace("{{username}}", username)

    return HTMLResponse(html)
