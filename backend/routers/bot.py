from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import sqlite3
import threading
import time
import hmac
import hashlib
import requests
import os
from datetime import datetime
from database import get_db
from auth_utils import get_current_user

router = APIRouter()

active_bots = {}

BINANCE_API_KEY    = os.environ.get("BINANCE_API_KEY", "")
BINANCE_SECRET_KEY = os.environ.get("BINANCE_SECRET_KEY", "")
BASE_URL = "https://fapi.binance.com"

def sign(params):
    query = "&".join(f"{k}={v}" for k, v in params.items())
    sig = hmac.new(BINANCE_SECRET_KEY.encode(), query.encode(), hashlib.sha256).hexdigest()
    return query + "&signature=" + sig

def bheaders():
    return {"X-MBX-APIKEY": BINANCE_API_KEY}

def get_price(symbol):
    r = requests.get(f"{BASE_URL}/fapi/v1/ticker/price", params={"symbol": symbol})
    return float(r.json()["price"])

def get_balance():
    params = {"timestamp": int(time.time() * 1000)}
    r = requests.get(
        f"{BASE_URL}/fapi/v2/balance",
        headers=bheaders(),
        params={**params, "signature": sign(params)}
    )
    for asset in r.json():
        if asset["asset"] == "USDT":
            return float(asset["availableBalance"])
    return 0.0

def get_position(symbol):
    params = {"symbol": symbol, "timestamp": int(time.time() * 1000)}
    r = requests.get(
        f"{BASE_URL}/fapi/v2/positionRisk",
        headers=bheaders(),
        params={**params, "signature": sign(params)}
    )
    for p in r.json():
        if p["symbol"] == symbol:
            return float(p["positionAmt"])
    return 0.0

def set_leverage(symbol, leverage=1):
    params = {"symbol": symbol, "leverage": leverage, "timestamp": int(time.time() * 1000)}
    requests.post(
        f"{BASE_URL}/fapi/v1/leverage",
        headers=bheaders(),
        params={**params, "signature": sign(params)}
    )

def cancel_open_orders(symbol):
    params = {"symbol": symbol, "timestamp": int(time.time() * 1000)}
    requests.delete(
        f"{BASE_URL}/fapi/v1/allOpenOrders",
        headers=bheaders(),
        params={**params, "signature": sign(params)}
    )

def close_position(symbol, position_amt):
    if position_amt == 0:
        return
    cancel_open_orders(symbol)
    side = "SELL" if position_amt > 0 else "BUY"
    qty = abs(round(position_amt, 3))
    params = {
        "symbol": symbol, "side": side, "type": "MARKET",
        "quantity": qty, "reduceOnly": "true",
        "timestamp": int(time.time() * 1000)
    }
    requests.post(
        f"{BASE_URL}/fapi/v1/order",
        headers=bheaders(),
        params={**params, "signature": sign(params)}
    )
    print(f"[{datetime.now()}] Pozisyon kapatildi: {side} {qty}")

def open_position(symbol, side, usdt_amount, sl_pct, tp_pct):
    price = get_price(symbol)
    qty = round(usdt_amount / price, 3)
    params = {
        "symbol": symbol, "side": side, "type": "MARKET",
        "quantity": qty, "timestamp": int(time.time() * 1000)
    }
    requests.post(
        f"{BASE_URL}/fapi/v1/order",
        headers=bheaders(),
        params={**params, "signature": sign(params)}
    )
    print(f"[{datetime.now()}] Pozisyon acildi {side} {qty} @ {price}")

    sl_side = "SELL" if side == "BUY" else "BUY"
    if side == "BUY":
        sl_price = round(price * (1 - sl_pct / 100), 2)
        tp_price = round(price * (1 + tp_pct / 100), 2)
    else:
        sl_price = round(price * (1 + sl_pct / 100), 2)
        tp_price = round(price * (1 - tp_pct / 100), 2)

    sl_params = {
        "symbol": symbol, "side": sl_side, "type": "STOP_MARKET",
        "stopPrice": sl_price, "closePosition": "true",
        "timestamp": int(time.time() * 1000)
    }
    requests.post(f"{BASE_URL}/fapi/v1/order", headers=bheaders(), params={**sl_params, "signature": sign(sl_params)})

    tp_params = {
        "symbol": symbol, "side": sl_side, "type": "TAKE_PROFIT_MARKET",
        "stopPrice": tp_price, "closePosition": "true",
        "timestamp": int(time.time() * 1000)
    }
    requests.post(f"{BASE_URL}/fapi/v1/order", headers=bheaders(), params={**tp_params, "signature": sign(tp_params)})
    print(f"[{datetime.now()}] SL={sl_price} TP={tp_price}")

def sma(prices, period):
    if len(prices) < period:
        return None
    return sum(prices[-period:]) / period

def get_klines(symbol, interval, limit=250):
    r = requests.get(
        f"{BASE_URL}/fapi/v1/klines",
        params={"symbol": symbol, "interval": interval, "limit": limit}
    )
    return [float(k[4]) for k in r.json()]

def tf_to_seconds(tf):
    mapping = {"1m": 60, "3m": 180, "5m": 300, "15m": 900, "30m": 1800, "1h": 3600, "4h": 14400, "1d": 86400}
    return mapping.get(tf, 900)

def bot_loop(user_id, strategy):
    symbol = strategy["symbol"]
    timeframe = strategy["timeframe"]
    sma1_p = strategy["sma1"]
    sma2_p = strategy["sma2"]
    sl_pct = strategy["stop_loss"]
    tp_pct = strategy["take_profit"]
    trade_amount = strategy.get("trade_amount", 10.0)
    sleep_sec = tf_to_seconds(timeframe)

    print(f"[{datetime.now()}] Bot basladi: {symbol} {timeframe} SMA{sma1_p}/{sma2_p} Miktar={trade_amount}$")
    set_leverage(symbol, 1)

    prev_signal = None
    active_bots[user_id]["status"] = "running"

    while active_bots.get(user_id, {}).get("running", False):
        try:
            limit = max(sma1_p, sma2_p) + 10
            prices = get_klines(symbol, timeframe, limit=limit)
            s1 = sma(prices, sma1_p)
            s2 = sma(prices, sma2_p)

            if s1 is None or s2 is None:
                time.sleep(10)
                continue

            signal = "BUY" if s1 > s2 else "SELL"
            now = datetime.now().strftime("%H:%M:%S")
            active_bots[user_id]["last_signal"] = signal
            active_bots[user_id]["last_check"] = now
            active_bots[user_id]["sma1_val"] = round(s1, 2)
            active_bots[user_id]["sma2_val"] = round(s2, 2)

            if signal != prev_signal:
                position = get_position(symbol)
                if position != 0:
                    close_position(symbol, position)
                    time.sleep(2)

                balance = get_balance()
                active_bots[user_id]["balance"] = round(balance, 2)

                if balance >= trade_amount:
                    open_position(symbol, signal, trade_amount, sl_pct, tp_pct)
                    prev_signal = signal
                    active_bots[user_id]["trades"] = active_bots[user_id].get("trades", 0) + 1
                else:
                    print(f"Yetersiz bakiye: {balance} USDT (gereken: {trade_amount})")
                    active_bots[user_id]["status"] = "insufficient_balance"

        except Exception as e:
            print(f"[{datetime.now()}] Bot hatasi: {e}")
            active_bots[user_id]["last_error"] = str(e)

        time.sleep(sleep_sec)

    try:
        position = get_position(symbol)
        if position != 0:
            close_position(symbol, position)
            cancel_open_orders(symbol)
    except Exception:
        pass

    active_bots[user_id]["status"] = "stopped"
    print(f"[{datetime.now()}] Bot durduruldu: user={user_id}")


class BotStartIn(BaseModel):
    strategy_id: int
    trade_amount: float = 10.0


@router.post("/start")
def start_bot(
    body: BotStartIn,
    current_user: dict = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db)
):
    uid = current_user["id"]

    if uid in active_bots and active_bots[uid].get("running"):
        raise HTTPException(400, "Bot zaten calisiyor. Once durdurun.")

    strat = db.execute(
        "SELECT * FROM strategies WHERE id=? AND user_id=?",
        (body.strategy_id, uid)
    ).fetchone()
    if not strat:
        raise HTTPException(404, "Strateji bulunamadi")

    if not BINANCE_API_KEY or not BINANCE_SECRET_KEY:
        raise HTTPException(400, "Binance API key ayarlanmamis")

    strategy = dict(strat)
    strategy["trade_amount"] = body.trade_amount

    active_bots[uid] = {
        "running": True,
        "status": "starting",
        "strategy_id": body.strategy_id,
        "strategy_name": strategy["name"],
        "symbol": strategy["symbol"],
        "timeframe": strategy["timeframe"],
        "trade_amount": body.trade_amount,
        "trades": 0,
        "last_signal": None,
        "last_check": None,
        "balance": None,
        "last_error": None,
    }

    t = threading.Thread(target=bot_loop, args=(uid, strategy), daemon=True)
    active_bots[uid]["thread"] = t
    t.start()

    return {"ok": True, "message": f"{strategy['name']} botu baslatildi ({body.trade_amount} USDT)"}


@router.post("/stop")
def stop_bot(current_user: dict = Depends(get_current_user)):
    uid = current_user["id"]
    if uid not in active_bots or not active_bots[uid].get("running"):
        raise HTTPException(400, "Calisan bot yok")
    active_bots[uid]["running"] = False
    return {"ok": True, "message": "Bot durduruluyor..."}


@router.get("/status")
def bot_status(current_user: dict = Depends(get_current_user)):
    uid = current_user["id"]
    if uid not in active_bots:
        return {"running": False}
    b = active_bots[uid]
    return {
        "running": b.get("running", False),
        "status": b.get("status"),
        "strategy_name": b.get("strategy_name"),
        "symbol": b.get("symbol"),
        "timeframe": b.get("timeframe"),
        "trade_amount": b.get("trade_amount"),
        "last_signal": b.get("last_signal"),
        "last_check": b.get("last_check"),
        "sma1_val": b.get("sma1_val"),
        "sma2_val": b.get("sma2_val"),
        "balance": b.get("balance"),
        "trades": b.get("trades", 0),
        "last_error": b.get("last_error"),
    }
