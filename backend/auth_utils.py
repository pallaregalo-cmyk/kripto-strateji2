from datetime import datetime, timedelta
from typing import Optional
import jwt
import bcrypt
import os

SECRET_KEY = os.environ.get("SECRET_KEY", "kripto-strateji-secret-change-in-production-2024")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24 * 7  # 7 gün

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())

def create_token(user_id: int, email: str) -> str:
    expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    payload = {"sub": str(user_id), "email": email, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

# FastAPI dependency
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from database import get_db
import sqlite3

bearer = HTTPBearer(auto_error=False)

def get_current_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
    db: sqlite3.Connection = Depends(get_db)
):
    if not creds:
        raise HTTPException(status_code=401, detail="Token gerekli")
    payload = decode_token(creds.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Geçersiz veya süresi dolmuş token")
    user = db.execute("SELECT * FROM users WHERE id=?", (int(payload["sub"]),)).fetchone()
    if not user:
        raise HTTPException(status_code=401, detail="Kullanıcı bulunamadı")
    return dict(user)
