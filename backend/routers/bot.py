from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
import sqlite3
import threading
import time
import hmac
import hashlib
import requests
import os
import math
from datetime import datetime
from database import get_db, DB_PATH
from auth_utils import get_current_user

router = APIRouter()
active_bots = {}

BASE_URL = "https://fapi.binance.com"
_exchange_info_cache = {}


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


def get_symbol_info(symbol):
    global _exchange_info_cache
    if symbol in _exchange_info_cache:
        return _exchange_info_cache[symbol]
    try:
        info = requests.get(f"{BASE_URL}/fapi/v1/exchangeInfo", timeout=10).json()
        for s in info.get("symbols", []):
            if s["symbol"] == symbol:
                qty_step = 1.0
                min_qty = 1.0
                price_precision = s.get("pricePrecision", 4)
                for f in s["filters"]:
                    if f["filterType"] == "LOT_SIZE":
                        qty_step = float(f["stepSize"])
                        min_qty = float(f["minQty"])
                result = {"qty_step": qty_step, "min_qty": min_qty, "price_precision": price_precision}
                print(f"Symbol info {symbol}: {result}")
                _exchange_info_cache[symbol] = result
                return result
    except Exception as e:
        print(f"ExchangeInfo hatasi: {e}")
    default = {"qty_step": 1.0, "min_qty": 1.0, "price_precision": 4}
    _exchange_info_cache[symbol] = default
    return default


def round_step(value, step):
    precision = max(0, int(round(-math.log10(step)))) if step < 1 else 0
    result = math.floor(value / step) * step
    return round(result, precision)


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
    r = signed_request("POST", "/fapi/v1/leverage", {"symbol": symbol, "leverage": leverage})
    print(f"Leverage: {r.json()}")


def cancel_open_orders(symbol):
    signed_request("DELETE", "/fapi/v1/allOpenOrders", {"symbol": symbol})


def save_trade(user_id, symbol, side, entry_price, exit_price, quantity, close_reason):
    try:
        if side == "BUY":
            pnl = (exit_price - entry_price) * quantity
            pnl_pct = (exit_price - entry_price) / entry_price * 100
        else:
            pnl = (entry_price - exit_price) * quantity
            pnl_pct = (entry_price - exit_price) / entry_price * 100

        conn = __import__('sqlite3').connect(DB_PATH, check_same_thread=False)
        conn.execute(
            """INSERT INTO trade_history
               (user_id, symbol, side, entry_price, exit_price, quantity, pnl, pnl_pct, close_reason, closed_at)
               VALUES (?,?,?,?,?,?,?,?,?,datetime('now'))""",
            (user_id, symbol, side, entry_price, exit_price, quantity,
             round(pnl, 4), round(pnl_pct, 4), close_reason)
        )
        conn.commit()
        conn.close()
        print(f"Trade kaydedildi: {side} {symbol} PnL={pnl:.4f} USDT ({pnl_pct:.2f}%)")
    except Exception as e:
        print(f"Trade kayit hatasi: {e}")


def close_position(symbol, position_amt, reason="", user_id=None, active_position=None):
    if position_amt == 0:
        return
    cancel_open_orders(symbol)
    info = get_symbol_info(symbol)
    side = "SELL" if position_amt > 0 else "BUY"
    qty = round_step(abs(position_amt), info["qty_step"])
    r = signed_request("POST", "/fapi/v1/order", {
        "symbol": symbol,
        "side": side,
        "type": "MARKET",
        "quantity": qty,
        "reduceOnly": "true",
    })
    result = r.json()
    print(f"[{datetime.now()}] Pozisyon kapatildi ({reason}): {result}")

    if user_id and active_position and "code" not in result:
        exit_price = get_price(symbol)
        save_trade(
            user_id, symbol,
            active_position["side"],
            active_position["entry_price"],
            exit_price,
            active_position["qty"],
            reason
        )


def open_position(symbol, side, usdt_amount, sl_pct, tp_pct):
    price = get_price(symbol)
    info = get_symbol_info(symbol)
    qty = round_step(usdt_amount / price, info["qty_step"])
    if qty < info["min_qty"]:
        print(f"Miktar cok kucuk: {qty} < {info['min_qty']}")
        return None

    r = signed_request("POST", "/fapi/v1/order", {
        "symbol": symbol,
        "side": side,
        "type": "MARKET",
        "quantity": qty,
    })
    result = r.json()
    print(f"[{datetime.now()}] Pozisyon acildi {side} {qty} @ {price}: {result}")

    if "code" in result:
        print(f"Pozisyon hatasi: {result}")
        return None

    pp = info["price_precision"]
    if side == "BUY":
        sl_price = round(price * (1 - sl_pct / 100), pp)
        tp_price = round(price * (1 + tp_pct / 100), pp)
    else:
        sl_price = round(price * (1 + sl_pct / 100), pp)
        tp_price = round(price * (1 - tp_pct / 100), pp)

    print(f"Bot SL takibi: {sl_price} | TP takibi: {tp_price}")
    return {"entry_price": price, "sl_price": sl_price, "tp_price": tp_price, "side": side, "qty": qty}


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

    try:
        my_ip = requests.get("https://api.ipify.org").text
        print(f"Sunucu IP: {my_ip}")
    except Exception:
        pass

    print(f"[{datetime.now()}] Bot basladi: {symbol} {timeframe} SMA{sma1_p}/{sma2_p} Miktar={trade_amount}$")
    set_leverage(symbol, 1)

    prev_signal = None
    active_position = None
    active_bots[user_id]["status"] = "running"
    active_bots[user_id]["active_position"] = None

    while active_bots.get(user_id, {}).get("running", False):
        try:
            # Manuel kapatma isteği
            if active_bots[user_id].get("force_close"):
                active_bots[user_id]["force_close"] = False
                if active_position:
                    position = get_position(symbol)
                    if position != 0:
                        close_position(symbol, position, "Manuel kapatma", user_id, active_position)
                    active_position = None
                    prev_signal = None
                    active_bots[user_id]["active_position"] = None
                time.sleep(2)
                continue

            # Manuel SL/TP güncelleme
            if active_bots[user_id].get("update_sltp") and active_position:
                upd = active_bots[user_id].pop("update_sltp")
                if upd.get("sl"):
                    active_position["sl_price"] = float(upd["sl"])
                if upd.get("tp"):
                    active_position["tp_price"] = float(upd["tp"])
                active_bots[user_id]["active_position"] = active_position
                print(f"SL/TP guncellendi: SL={active_position['sl_price']} TP={active_position['tp_price']}")

            # SL/TP takibi
            if active_position:
                current_price = get_price(symbol)
                side = active_position["side"]
                sl = active_position["sl_price"]
                tp = active_position["tp_price"]

                active_bots[user_id]["current_price"] = current_price

                sl_hit = (side == "BUY" and current_price <= sl) or (side == "SELL" and current_price >= sl)
                tp_hit = (side == "BUY" and current_price >= tp) or (side == "SELL" and current_price <= tp)

                if sl_hit:
                    print(f"[{datetime.now()}] STOP LOSS tetiklendi! Fiyat={current_price} SL={sl}")
                    position = get_position(symbol)
                    if position != 0:
                        close_position(symbol, position, "Stop Loss", user_id, active_position)
                    active_position = None
                    prev_signal = None
                    active_bots[user_id]["active_position"] = None
                    active_bots[user_id]["last_error"] = f"SL tetiklendi @ {current_price}"
                    time.sleep(5)
                    continue

                if tp_hit:
                    print(f"[{datetime.now()}] TAKE PROFIT tetiklendi! Fiyat={current_price} TP={tp}")
                    position = get_position(symbol)
                    if position != 0:
                        close_position(symbol, position, "Take Profit", user_id, active_position)
                    active_position = None
                    prev_signal = None
                    active_bots[user_id]["active_position"] = None
                    active_bots[user_id]["last_error"] = f"TP tetiklendi @ {current_price}"
                    time.sleep(5)
                    continue

            # SMA sinyali
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
            active_bots[user_id]["sma1_val"] = round(s1, 4)
            active_bots[user_id]["sma2_val"] = round(s2, 4)
            print(f"[{now}] SMA1={s1:.4f} SMA2={s2:.4f} → {signal}")

            if signal != prev_signal:
                position = get_position(symbol)
                if position != 0:
                    close_position(symbol, position, "Crossover", user_id, active_position)
                    active_position = None
                    active_bots[user_id]["active_position"] = None
                    time.sleep(2)

                balance = get_balance()
                active_bots[user_id]["balance"] = round(balance, 2)

                if balance >= trade_amount:
                    pos_info = open_position(symbol, signal, trade_amount, sl_pct, tp_pct)
                    if pos_info:
                        active_position = pos_info
                        active_bots[user_id]["active_position"] = pos_info
                        prev_signal = signal
                        active_bots[user_id]["trades"] = active_bots[user_id].get("trades", 0) + 1
                        active_bots[user_id]["last_error"] = f"Giris @ {pos_info['entry_price']} | SL={pos_info['sl_price']} TP={pos_info['tp_price']}"
                else:
                    print(f"Yetersiz bakiye: {balance} USDT (gereken: {trade_amount})")
                    active_bots[user_id]["status"] = "insufficient_balance"

        except Exception as e:
            print(f"[{datetime.now()}] Bot hatasi: {e}")
            active_bots[user_id]["last_error"] = str(e)

        if active_position:
            time.sleep(10)
        else:
            time.sleep(sleep_sec)

    try:
        position = get_position(symbol)
        if position != 0:
            close_position(symbol, position, "Bot durduruldu", user_id, active_position)
    except Exception:
        pass

    active_bots[user_id]["status"] = "stopped"
    active_bots[user_id]["active_position"] = None
    print(f"[{datetime.now()}] Bot durduruldu: user={user_id}")


class BotStartIn(BaseModel):
    strategy_id: int
    trade_amount: float = 10.0


class UpdateSLTPIn(BaseModel):
    sl: Optional[float] = None
    tp: Optional[float] = None


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
        ADMIN_EMAIL = "pallaregalo@gmail.com"
if current_user["email"] != ADMIN_EMAIL:
    raise HTTPException(403, "Bot kullanimi sadece admin hesabina ozgudur")
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
        "active_position": None,
        "current_price": None,
        "force_close": False,
    }
    t = threading.Thread(target=bot_loop, args=(uid, strategy), daemon=True)
    active_bots[uid]["thread"] = t
    t.start()
    return {"ok": True, "message": f"{strategy['name']} botu baslatildi ({body.trade_amount} USDT)"}


@router.post("/stop")
def stop_bot(current_user: dict = Depends(get_current_user)):
    if current_user["email"] != "pallaregalo@gmail.com":
        raise HTTPException(403, "Yetkisiz erisim")
    uid = current_user["id"]
    if uid not in active_bots or not active_bots[uid].get("running"):
        raise HTTPException(400, "Calisan bot yok")
    active_bots[uid]["running"] = False
    return {"ok": True, "message": "Bot durduruluyor..."}


@router.post("/close-position")
def close_position_manually(current_user: dict = Depends(get_current_user)):
    if current_user["email"] != "pallaregalo@gmail.com":
    return {"running": False}
    uid = current_user["id"]
    if uid not in active_bots or not active_bots[uid].get("running"):
        raise HTTPException(400, "Calisan bot yok")
    active_bots[uid]["force_close"] = True
    return {"ok": True, "message": "Pozisyon kapatma istegi gonderildi"}


@router.post("/update-sltp")
def update_sltp(
    body: UpdateSLTPIn,
    current_user: dict = Depends(get_current_user),
):
    uid = current_user["id"]
    if uid not in active_bots or not active_bots[uid].get("running"):
        raise HTTPException(400, "Calisan bot yok")
    if not active_bots[uid].get("active_position"):
        raise HTTPException(400, "Acik pozisyon yok")
    active_bots[uid]["update_sltp"] = {"sl": body.sl, "tp": body.tp}
    return {"ok": True, "message": "SL/TP guncelleme istegi gonderildi"}


@router.get("/status")
def bot_status(current_user: dict = Depends(get_current_user)):
    if current_user["email"] != "pallaregalo@gmail.com":
    return {"running": False}
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
        "active_position": b.get("active_position"),
        "current_price": b.get("current_price"),
    }


@router.get("/history")
def trade_history(
    symbol: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db),
):
    uid = current_user["id"]
    query = "SELECT * FROM trade_history WHERE user_id=?"
    params = [uid]
    if symbol:
        query += " AND symbol=?"
        params.append(symbol.upper())
    if start_date:
        query += " AND opened_at >= ?"
        params.append(start_date)
    if end_date:
        query += " AND opened_at <= ?"
        params.append(end_date + " 23:59:59")
    query += " ORDER BY id DESC LIMIT 200"
    rows = db.execute(query, params).fetchall()
    trades = [dict(r) for r in rows]
    total_pnl = sum(t["pnl"] or 0 for t in trades)
    wins = sum(1 for t in trades if (t["pnl"] or 0) > 0)
    return {
        "trades": trades,
        "summary": {
            "total": len(trades),
            "wins": wins,
            "losses": len(trades) - wins,
            "win_rate": round(wins / len(trades) * 100, 1) if trades else 0,
            "total_pnl": round(total_pnl, 4),
        }
    }
