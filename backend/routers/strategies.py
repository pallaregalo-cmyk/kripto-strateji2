from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
import sqlite3
from database import get_db
from auth_utils import get_current_user

router = APIRouter()

class StrategyIn(BaseModel):
    name: str
    symbol: str = "BTCUSDT"
    timeframe: str = "15m"
    days: int = 7
    sma1: int = 9
    sma2: int = 21
    rsi_period: int = 14
    rsi_ob: int = 70
    rsi_os: int = 30
    stop_loss: float = 2.0
    take_profit: float = 4.0
    notes: str = ""

class BacktestIn(BaseModel):
    strategy_id: int
    total_trades: int
    win_rate: float
    total_pnl: float
    max_drawdown: float

@router.get("/")
def list_strategies(
    current_user: dict = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db)
):
    rows = db.execute(
        """SELECT s.*, 
           (SELECT total_trades FROM backtest_results WHERE strategy_id=s.id ORDER BY ran_at DESC LIMIT 1) as last_trades,
           (SELECT win_rate     FROM backtest_results WHERE strategy_id=s.id ORDER BY ran_at DESC LIMIT 1) as last_wr,
           (SELECT total_pnl    FROM backtest_results WHERE strategy_id=s.id ORDER BY ran_at DESC LIMIT 1) as last_pnl,
           (SELECT max_drawdown FROM backtest_results WHERE strategy_id=s.id ORDER BY ran_at DESC LIMIT 1) as last_dd,
           (SELECT ran_at       FROM backtest_results WHERE strategy_id=s.id ORDER BY ran_at DESC LIMIT 1) as last_run
           FROM strategies s WHERE s.user_id=? ORDER BY s.updated_at DESC""",
        (current_user["id"],)
    ).fetchall()
    return [dict(r) for r in rows]

@router.post("/")
def create_strategy(
    body: StrategyIn,
    current_user: dict = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db)
):
    cur = db.execute(
        """INSERT INTO strategies
           (user_id,name,symbol,timeframe,days,sma1,sma2,rsi_period,rsi_ob,rsi_os,stop_loss,take_profit,notes)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (current_user["id"], body.name, body.symbol, body.timeframe, body.days,
         body.sma1, body.sma2, body.rsi_period, body.rsi_ob, body.rsi_os,
         body.stop_loss, body.take_profit, body.notes)
    )
    db.commit()
    row = db.execute("SELECT * FROM strategies WHERE id=?", (cur.lastrowid,)).fetchone()
    return dict(row)

@router.put("/{sid}")
def update_strategy(
    sid: int,
    body: StrategyIn,
    current_user: dict = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db)
):
    existing = db.execute(
        "SELECT id FROM strategies WHERE id=? AND user_id=?", (sid, current_user["id"])
    ).fetchone()
    if not existing:
        raise HTTPException(404, "Strateji bulunamadı")
    db.execute(
        """UPDATE strategies SET
           name=?,symbol=?,timeframe=?,days=?,sma1=?,sma2=?,rsi_period=?,
           rsi_ob=?,rsi_os=?,stop_loss=?,take_profit=?,notes=?,
           updated_at=datetime('now')
           WHERE id=? AND user_id=?""",
        (body.name, body.symbol, body.timeframe, body.days,
         body.sma1, body.sma2, body.rsi_period, body.rsi_ob, body.rsi_os,
         body.stop_loss, body.take_profit, body.notes, sid, current_user["id"])
    )
    db.commit()
    row = db.execute("SELECT * FROM strategies WHERE id=?", (sid,)).fetchone()
    return dict(row)

@router.delete("/{sid}")
def delete_strategy(
    sid: int,
    current_user: dict = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db)
):
    existing = db.execute(
        "SELECT id FROM strategies WHERE id=? AND user_id=?", (sid, current_user["id"])
    ).fetchone()
    if not existing:
        raise HTTPException(404, "Strateji bulunamadı")
    db.execute("DELETE FROM strategies WHERE id=?", (sid,))
    db.commit()
    return {"ok": True}

@router.post("/backtest")
def save_backtest(
    body: BacktestIn,
    current_user: dict = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db)
):
    strat = db.execute(
        "SELECT id FROM strategies WHERE id=? AND user_id=?",
        (body.strategy_id, current_user["id"])
    ).fetchone()
    if not strat:
        raise HTTPException(404, "Strateji bulunamadı")
    db.execute(
        """INSERT INTO backtest_results (strategy_id,user_id,total_trades,win_rate,total_pnl,max_drawdown)
           VALUES (?,?,?,?,?,?)""",
        (body.strategy_id, current_user["id"],
         body.total_trades, body.win_rate, body.total_pnl, body.max_drawdown)
    )
    db.execute(
        "UPDATE strategies SET updated_at=datetime('now') WHERE id=?", (body.strategy_id,)
    )
    db.commit()
    return {"ok": True}

@router.get("/{sid}/history")
def backtest_history(
    sid: int,
    current_user: dict = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db)
):
    strat = db.execute(
        "SELECT id FROM strategies WHERE id=? AND user_id=?", (sid, current_user["id"])
    ).fetchone()
    if not strat:
        raise HTTPException(404, "Strateji bulunamadı")
    rows = db.execute(
        "SELECT * FROM backtest_results WHERE strategy_id=? ORDER BY ran_at DESC LIMIT 20", (sid,)
    ).fetchall()
    return [dict(r) for r in rows]
