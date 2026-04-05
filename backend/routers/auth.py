from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
import sqlite3
from database import get_db
from auth_utils import hash_password, verify_password, create_token, get_current_user

router = APIRouter()

class RegisterIn(BaseModel):
    email: str
    username: str
    password: str

class LoginIn(BaseModel):
    email: str
    password: str

@router.post("/register")
def register(body: RegisterIn, db: sqlite3.Connection = Depends(get_db)):
    if len(body.password) < 6:
        raise HTTPException(400, "Şifre en az 6 karakter olmalı")
    if len(body.username) < 3:
        raise HTTPException(400, "Kullanıcı adı en az 3 karakter olmalı")
    existing = db.execute(
        "SELECT id FROM users WHERE email=? OR username=?",
        (body.email.lower(), body.username)
    ).fetchone()
    if existing:
        raise HTTPException(400, "Bu email veya kullanıcı adı zaten kullanılıyor")
    hashed = hash_password(body.password)
    cur = db.execute(
        "INSERT INTO users (email, username, password) VALUES (?,?,?)",
        (body.email.lower(), body.username, hashed)
    )
    user_id = cur.lastrowid
    db.execute("INSERT INTO user_settings (user_id) VALUES (?)", (user_id,))
    db.execute(
        "INSERT INTO watchlist (user_id, symbol) VALUES (?,?),(?,?),(?,?)",
        (user_id,"BTCUSDT", user_id,"ETHUSDT", user_id,"SOLUSDT")
    )
    db.commit()
    token = create_token(user_id, body.email.lower())
    return {"token": token, "username": body.username, "email": body.email.lower()}

@router.post("/login")
def login(body: LoginIn, db: sqlite3.Connection = Depends(get_db)):
    user = db.execute(
        "SELECT * FROM users WHERE email=?", (body.email.lower(),)
    ).fetchone()
    if not user or not verify_password(body.password, user["password"]):
        raise HTTPException(401, "Email veya şifre hatalı")
    db.execute(
        "UPDATE users SET last_login=datetime('now') WHERE id=?", (user["id"],)
    )
    db.commit()
    token = create_token(user["id"], user["email"])
    return {"token": token, "username": user["username"], "email": user["email"]}

@router.get("/me")
def me(current_user: dict = Depends(get_current_user)):
    return {
        "id": current_user["id"],
        "email": current_user["email"],
        "username": current_user["username"],
        "created_at": current_user["created_at"],
        "last_login": current_user["last_login"],
    }
