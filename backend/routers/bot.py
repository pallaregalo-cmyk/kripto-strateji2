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

BASE_URL = "https://fapi.binance.com"


def get_api_key():
    return os.environ.get("BINANCE_API_KEY", "")


def get_secret_key():
    return os.environ.get("BINANCE_SECRET_KEY", "")


def signed_request(method, path, extra_params=None):
    params = extra_params or {}
    params["timestamp"] = int(time.time() * 1000)
    query = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    sig = hmac.new(
        get_secret_key().encode("utf-8"),
        query.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    url = f"{BASE_URL}{path}?{query}&signature={sig}"
    headers = {"X-MBX-APIKEY": get_api_key()}
    if method == "GET":
        return requests.get(url, headers=headers)
    elif method == "POST":
        return requests.post(url, headers=headers)
    elif method == "DELETE":
        return requests.delete(url, headers=headers)


def get_price(symbol):
    r = requests.get(f"{BASE_URL}/fapi/v1/ticker/price", params={"symbol": symbol})
    return float(r.json()["price"])


def get_balance():
    r = signed_request("GET", "/fapi/v2/balance")
    data = r.json()
    if not isinstance(data, list):
        print(f"Balance hatasi: {data}")
        return 0.0
    for asset in data:
        if asset["asset"] == "USDT":
            return float(asset["availableBalance"])
    return 0.0


def get_position(symbol):
    r = signed_request("GET", "/fapi/v2/positionRisk", {"symbol": symbol})
    data = r.json()
    if not isinstance(data, list):
        print(f"Position hatasi: {data}")
        return 0.0
    for p in data:
        if p["symbol"] == symbol:
            return float(p["positionAmt"])
    return 0.0


def set_leverage(symbol, leverage=1):
    signed_request("POST", "/fapi/v1/leverage", {"symbol": symbol, "leverage": leverage})


def cancel_open_orders(symbol):
    signed_request("DELETE", "/fapi/v1/allOpenOrders", {"symbol": symbol})


def close_position(symbol, position_amt):
    if position_amt == 0:
        return
    cancel_open_orders(symbol)
    side = "SELL" if position_amt > 0 else "BUY"
    qty = abs(round(position_amt, 3))
    r = signed_request("POST", "/fapi/v1/order", {
        "symbol": symbol,
        "side": side,
        "type": "MARKET",
        "quantity": qty,
        "reduceOnly": "true",
    })
    print(f"[{datetime.now()}] Pozisyon kapatildi: {side} {qty} → {r.json()}")


def open_position(symbol, side, usdt_amount, sl_pct, tp_pct):
    price = get_price(symbol)
    qty = round(usdt_amount / price, 3)

    r = signed_request("POST", "/fapi/v1/order", {
        "symbol": symbol,
        "side": side,
        "type": "MARKET",
        "quantity": qty,
    })
    print(f"[{datetime.now()}] Pozisyon acildi {side} {qty} @ {price} → {r.json()}")

    sl_side = "SELL" if side == "BUY" else "BUY"
    if side == "BUY":
        sl_price = round(price * (1 - sl_pct / 100), 2)
        tp_price = round(price * (1 + tp_pct / 100), 2)
    else:
        sl_price = round(price * (1 + sl_pct / 100), 2)
        tp_price = round(price * (1 - tp_pct / 100), 2)

    r_sl = signed_request("POST", "/fapi/v1/order", {
        "symbol": symbol,
        "side": sl_side,
        "type": "STOP_MARKET",
        "stopPrice": sl_price,
        "closePosition": "true",
    })
    print(f"SL order: {r_sl.json()}")

    r_tp = signed_request("POST", "/fapi/v1/order", {
        "symbol": symbol,
        "side": sl_side,
        "type": "TAKE_PROFIT_MARKET",
        "stopPrice": tp_price,
        "closePosition": "true",
    })
    print(f"TP order: {r_tp.json()}")
    print(f"[{datetime.now()}] SL={sl_price} TP={tp_price}")


def sma(prices, period):
    if len(prices) < period:
        return None
    return sum(prices[-period:]) / period


def get_klines(symbol, interval, limit=250):
    r = requests.get(
        f"{BASE_URL}/fapi/v1/klines",
        params={"symbol": symbol, "interval": interval, "limit": limit},
    )
    data = r.json()
    if not isinstance(data, list) or len(data) == 0:
        print(f"Klines hatasi: {data}")
        return []
    if not isinstance(data[0], list):
        print(f"Beklenmedik klines format: {data[0]}")
        return []
    return [float(k[4]) for k in data]


def tf_to_seconds(tf):
    mapping = {
        "1m": 60, "3m": 180, "5m": 300, "15m": 900,
        "30m": 1800, "1h": 3600, "4h": 14400, "1d": 86400,
    }
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

            if not prices:
                time.sleep(30)
                continue

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
            print(f"[{now}] SMA1={s1:.4f} SMA2={s2:.4f} → {signal}")

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
    db: sqlite3.Connection = Depends(get_db),
):
    uid = current_user["id"]

    if uid in active_bots and active_bots[uid].get("running"):
        raise HTTPException(400, "Bot zaten calisiyor. Once durdurun.")

    strat = db.execute(
        "SELECT * FROM strategies WHERE id=? AND user_id=?",
        (body.strategy_id, uid),
    ).fetchone()
    if not strat:
        raise HTTPException(404, "Strateji bulunamadi")

    if not get_api_key() or not get_secret_key():
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
