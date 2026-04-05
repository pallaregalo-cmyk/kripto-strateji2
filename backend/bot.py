import os
import time
import hmac
import hashlib
import requests
from datetime import datetime

API_KEY    = os.environ.get("BINANCE_API_KEY", "")
SECRET_KEY = os.environ.get("BINANCE_SECRET_KEY", "")
BASE_URL   = "https://fapi.binance.com"

def sign(params):
    query = "&".join(f"{k}={v}" for k, v in params.items())
    sig = hmac.new(SECRET_KEY.encode(), query.encode(), hashlib.sha256).hexdigest()
    return query + "&signature=" + sig

def headers():
    return {"X-MBX-APIKEY": API_KEY}

def get_price(symbol):
    r = requests.get(f"{BASE_URL}/fapi/v1/ticker/price", params={"symbol": symbol})
    return float(r.json()["price"])

def get_balance():
    params = {"timestamp": int(time.time() * 1000)}
    r = requests.get(f"{BASE_URL}/fapi/v2/balance", headers=headers(), params={"timestamp": params["timestamp"], "signature": sign(params)})
    for asset in r.json():
        if asset["asset"] == "USDT":
            return float(asset["availableBalance"])
    return 0.0

def get_position(symbol):
    params = {"symbol": symbol, "timestamp": int(time.time() * 1000)}
    r = requests.get(f"{BASE_URL}/fapi/v2/positionRisk", headers=headers(), params={**params, "signature": sign(params)})
    for p in r.json():
        if p["symbol"] == symbol:
            return float(p["positionAmt"])
    return 0.0

def set_leverage(symbol, leverage=1):
    params = {"symbol": symbol, "leverage": leverage, "timestamp": int(time.time() * 1000)}
    requests.post(f"{BASE_URL}/fapi/v1/leverage", headers=headers(), params={**params, "signature": sign(params)})

def close_position(symbol, position_amt):
    if position_amt == 0:
        return
    side = "SELL" if position_amt > 0 else "BUY"
    qty  = abs(position_amt)
    params = {
        "symbol": symbol, "side": side, "type": "MARKET",
        "quantity": qty, "reduceOnly": "true",
        "timestamp": int(time.time() * 1000)
    }
    r = requests.post(f"{BASE_URL}/fapi/v1/order", headers=headers(), params={**params, "signature": sign(params)})
    print(f"[{datetime.now()}] Pozisyon kapatıldı: {r.json()}")

def open_position(symbol, side, usdt_amount, sl_pct, tp_pct):
    price = get_price(symbol)
    qty   = round(usdt_amount / price, 3)
    params = {
        "symbol": symbol, "side": side, "type": "MARKET",
        "quantity": qty, "timestamp": int(time.time() * 1000)
    }
    r = requests.post(f"{BASE_URL}/fapi/v1/order", headers=headers(), params={**params, "signature": sign(params)})
    print(f"[{datetime.now()}] Pozisyon açıldı {side}: {r.json()}")

    # Stop Loss ve Take Profit
    if side == "BUY":
        sl_price = round(price * (1 - sl_pct / 100), 2)
        tp_price = round(price * (1 + tp_pct / 100), 2)
        sl_side  = "SELL"
    else:
        sl_price = round(price * (1 + sl_pct / 100), 2)
        tp_price = round(price * (1 - tp_pct / 100), 2)
        sl_side  = "BUY"

    # SL
    sl_params = {
        "symbol": symbol, "side": sl_side, "type": "STOP_MARKET",
        "stopPrice": sl_price, "closePosition": "true",
        "timestamp": int(time.time() * 1000)
    }
    requests.post(f"{BASE_URL}/fapi/v1/order", headers=headers(), params={**sl_params, "signature": sign(sl_params)})

    # TP
    tp_params = {
        "symbol": symbol, "side": sl_side, "type": "TAKE_PROFIT_MARKET",
        "stopPrice": tp_price, "closePosition": "true",
        "timestamp": int(time.time() * 1000)
    }
    requests.post(f"{BASE_URL}/fapi/v1/order", headers=headers(), params={**tp_params, "signature": sign(tp_params)})
    print(f"[{datetime.now()}] SL: {sl_price} | TP: {tp_price}")

def sma(prices, period):
    if len(prices) < period:
        return None
    return sum(prices[-period:]) / period

def get_klines(symbol, interval, limit=50):
    r = requests.get(f"{BASE_URL}/fapi/v1/klines", params={"symbol": symbol, "interval": interval, "limit": limit})
    return [float(k[4]) for k in r.json()]

def run_bot(symbol, timeframe, sma1_period, sma2_period, sl_pct, tp_pct):
    print(f"[{datetime.now()}] Bot başlatıldı: {symbol} {timeframe} SMA{sma1_period}/{sma2_period}")
    set_leverage(symbol, 1)

    prev_signal = None

    while True:
        try:
            prices  = get_klines(symbol, timeframe, limit=max(sma1_period, sma2_period) + 5)
            s1      = sma(prices, sma1_period)
            s2      = sma(prices, sma2_period)

            if s1 is None or s2 is None:
                time.sleep(10)
                continue

            signal = "BUY" if s1 > s2 else "SELL"
            print(f"[{datetime.now()}] SMA1={s1:.2f} SMA2={s2:.2f} Sinyal={signal}")

            if signal != prev_signal:
                position = get_position(symbol)

                # Mevcut pozisyonu kapat
                if position != 0:
                    close_position(symbol, position)
                    time.sleep(2)

                # Yeni pozisyon aç
                balance = get_balance()
                if balance > 5:
                    open_position(symbol, signal, balance * 0.95, sl_pct, tp_pct)
                    prev_signal = signal
                else:
                    print(f"[{datetime.now()}] Yetersiz bakiye: {balance} USDT")

        except Exception as e:
            print(f"[{datetime.now()}] Hata: {e}")

        time.sleep(60)

if __name__ == "__main__":
    SYMBOL    = os.environ.get("BOT_SYMBOL",    "BTCUSDT")
    TIMEFRAME = os.environ.get("BOT_TIMEFRAME", "15m")
    SMA1      = int(os.environ.get("BOT_SMA1",  "9"))
    SMA2      = int(os.environ.get("BOT_SMA2",  "21"))
    SL_PCT    = float(os.environ.get("BOT_SL",  "2.0"))
    TP_PCT    = float(os.environ.get("BOT_TP",  "4.0"))

    run_bot(SYMBOL, TIMEFRAME, SMA1, SMA2, SL_PCT, TP_PCT)
