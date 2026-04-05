from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import sqlite3
from database import get_db
from auth_utils import get_current_user

router = APIRouter()

class WatchlistIn(BaseModel):
    symbol: str

@router.get("/")
def get_watchlist(
    current_user: dict = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db)
):
    rows = db.execute(
        "SELECT * FROM watchlist WHERE user_id=? ORDER BY added_at DESC",
        (current_user["id"],)
    ).fetchall()
    return [dict(r) for r in rows]

@router.post("/")
def add_to_watchlist(
    body: WatchlistIn,
    current_user: dict = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db)
):
    sym = body.symbol.upper()
    try:
        db.execute(
            "INSERT INTO watchlist (user_id, symbol) VALUES (?,?)",
            (current_user["id"], sym)
        )
        db.commit()
    except Exception:
        raise HTTPException(400, f"{sym} zaten izleme listesinde")
    return {"ok": True, "symbol": sym}

@router.delete("/{symbol}")
def remove_from_watchlist(
    symbol: str,
    current_user: dict = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db)
):
    db.execute(
        "DELETE FROM watchlist WHERE user_id=? AND symbol=?",
        (current_user["id"], symbol.upper())
    )
    db.commit()
    return {"ok": True}
