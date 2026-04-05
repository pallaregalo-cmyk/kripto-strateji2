from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
import sqlite3
from database import get_db
from auth_utils import get_current_user, hash_password, verify_password

router = APIRouter()

class SettingsIn(BaseModel):
    default_tf: Optional[str] = None
    default_days: Optional[int] = None
    theme: Optional[str] = None

class PasswordIn(BaseModel):
    current_password: str
    new_password: str

@router.get("/settings")
def get_settings(
    current_user: dict = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db)
):
    row = db.execute(
        "SELECT * FROM user_settings WHERE user_id=?", (current_user["id"],)
    ).fetchone()
    if not row:
        db.execute("INSERT INTO user_settings (user_id) VALUES (?)", (current_user["id"],))
        db.commit()
        row = db.execute("SELECT * FROM user_settings WHERE user_id=?", (current_user["id"],)).fetchone()
    return dict(row)

@router.put("/settings")
def update_settings(
    body: SettingsIn,
    current_user: dict = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db)
):
    fields, vals = [], []
    if body.default_tf is not None:
        fields.append("default_tf=?"); vals.append(body.default_tf)
    if body.default_days is not None:
        fields.append("default_days=?"); vals.append(body.default_days)
    if body.theme is not None:
        fields.append("theme=?"); vals.append(body.theme)
    if not fields:
        raise HTTPException(400, "Güncellenecek alan yok")
    fields.append("updated_at=datetime('now')")
    vals.append(current_user["id"])
    db.execute(
        f"UPDATE user_settings SET {','.join(fields)} WHERE user_id=?", vals
    )
    db.commit()
    return {"ok": True}

@router.put("/password")
def change_password(
    body: PasswordIn,
    current_user: dict = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db)
):
    user = db.execute("SELECT * FROM users WHERE id=?", (current_user["id"],)).fetchone()
    if not verify_password(body.current_password, user["password"]):
        raise HTTPException(400, "Mevcut şifre hatalı")
    if len(body.new_password) < 6:
        raise HTTPException(400, "Yeni şifre en az 6 karakter olmalı")
    db.execute(
        "UPDATE users SET password=? WHERE id=?",
        (hash_password(body.new_password), current_user["id"])
    )
    db.commit()
    return {"ok": True}

@router.get("/stats")
def get_stats(
    current_user: dict = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db)
):
    uid = current_user["id"]
    strat_count = db.execute("SELECT COUNT(*) FROM strategies WHERE user_id=?", (uid,)).fetchone()[0]
    bt_count    = db.execute("SELECT COUNT(*) FROM backtest_results WHERE user_id=?", (uid,)).fetchone()[0]
    wl_count    = db.execute("SELECT COUNT(*) FROM watchlist WHERE user_id=?", (uid,)).fetchone()[0]
    best = db.execute(
        """SELECT s.name, b.total_pnl FROM backtest_results b
           JOIN strategies s ON s.id=b.strategy_id
           WHERE b.user_id=? ORDER BY b.total_pnl DESC LIMIT 1""", (uid,)
    ).fetchone()
    return {
        "strategy_count": strat_count,
        "backtest_count": bt_count,
        "watchlist_count": wl_count,
        "best_strategy": dict(best) if best else None,
    }
