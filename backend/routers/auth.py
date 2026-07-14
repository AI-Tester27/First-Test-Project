"""Authentication: login / me / logout."""
from fastapi import APIRouter, Depends, HTTPException, Response

from core import (
    db, now_utc, verify_pw, make_token,
    set_auth_cookie, clear_auth_cookie,
    public_user, audit, get_current_user,
)
from models import LoginIn

router = APIRouter()


@router.post("/auth/login")
async def login(payload: LoginIn, response: Response):
    user = await db.users.find_one({"username": payload.username.lower().strip()})
    if not user or not verify_pw(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    if not user.get("active", True):
        raise HTTPException(status_code=403, detail="Account disabled")
    token = make_token(user["id"], user["role"])
    set_auth_cookie(response, token)
    await db.users.update_one({"id": user["id"]}, {"$set": {"last_login_at": now_utc().isoformat()}})
    await audit(user, "LOGIN", "User", user["id"])
    return {"user": public_user(user), "access_token": token}


@router.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return {"user": public_user(user)}


@router.post("/auth/logout")
async def logout(response: Response, user: dict = Depends(get_current_user)):
    clear_auth_cookie(response)
    await audit(user, "LOGOUT", "User", user["id"])
    return {"ok": True}
