import sqlite3
import os

DB_PATH = "/app/data/kripto.db"

def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    c = conn.cursor()

    c.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        email       TEXT    UNIQUE NOT NULL,
        username    TEXT    UNIQUE NOT NULL,
        password    TEXT    NOT NULL,
        created_at  TEXT    DEFAULT (datetime('now')),
        last_login  TEXT
    );

    CREATE TABLE IF NOT EXISTS strategies (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        name        TEXT    NOT NULL,
        symbol      TEXT    NOT NULL DEFAULT 'BTCUSDT',
        timeframe   TEXT    NOT NULL DEFAULT '15m',
        days        INTEGER NOT NULL DEFAULT 7,
        sma1        INTEGER NOT NULL DEFAULT 9,
        sma2        INTEGER NOT NULL DEFAULT 21,
        rsi_period  INTEGER NOT NULL DEFAULT 14,
        rsi_ob      INTEGER NOT NULL DEFAULT 70,
        rsi_os      INTEGER NOT NULL DEFAULT 30,
        stop_loss   REAL    NOT NULL DEFAULT 2.0,
        take_profit REAL    NOT NULL DEFAULT 4.0,
        notes       TEXT    DEFAULT '',
        strategy_type TEXT DEFAULT 'sma',
        bb_period     INTEGER DEFAULT 20,
        bb_std        REAL    DEFAULT 2.0,
        created_at  TEXT    DEFAULT (datetime('now')),
        updated_at  TEXT    DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS backtest_results (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        strategy_id  INTEGER NOT NULL REFERENCES strategies(id) ON DELETE CASCADE,
        user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        total_trades INTEGER,
        win_rate     REAL,
        total_pnl    REAL,
        max_drawdown REAL,
        ran_at       TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS watchlist (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        symbol     TEXT    NOT NULL,
        added_at   TEXT    DEFAULT (datetime('now')),
        UNIQUE(user_id, symbol)
    );

    CREATE TABLE IF NOT EXISTS user_settings (
        user_id         INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
        default_tf      TEXT    DEFAULT '15m',
        default_days    INTEGER DEFAULT 7,
        theme           TEXT    DEFAULT 'auto',
        updated_at      TEXT    DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS trade_history (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        symbol       TEXT    NOT NULL,
        side         TEXT    NOT NULL,
        entry_price  REAL    NOT NULL,
        exit_price   REAL,
        quantity     REAL    NOT NULL,
        pnl          REAL,
        pnl_pct      REAL,
        close_reason TEXT,
        opened_at    TEXT    DEFAULT (datetime('now')),
        closed_at    TEXT
    );
    """)
try:
        c.execute("ALTER TABLE strategies ADD COLUMN strategy_type TEXT DEFAULT 'sma'")
    except:
        pass
    try:
        c.execute("ALTER TABLE strategies ADD COLUMN bb_period INTEGER DEFAULT 20")
    except:
        pass
    try:
        c.execute("ALTER TABLE strategies ADD COLUMN bb_std REAL DEFAULT 2.0")
    except:
        pass
    conn.commit()
    conn.commit()
    conn.close()
    print("✓ Veritabanı hazır:", DB_PATH)
