"""Builds the shop database (provided; you don't need to edit this)."""

import datetime
import os
import random
import sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(HERE, "data.db")

USERS = 10_000
ORDERS = 300_000
COUNTRIES = ["NG", "GH", "KE", "ZA", "US", "GB", "DE", "FR", "IN", "BR", "JP", "CA"]
WEIGHTS = [20, 15, 10, 8, 12, 8, 6, 5, 7, 4, 3, 2]
START = datetime.datetime(2024, 1, 1)


def build():
    rng = random.Random(42)
    tmp = DB_PATH + ".tmp"
    if os.path.exists(tmp):
        os.remove(tmp)
    conn = sqlite3.connect(tmp)
    conn.executescript("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            country TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            amount_cents INTEGER NOT NULL,
            status TEXT NOT NULL,          -- 'paid' | 'refunded' | 'pending'
            created_at TEXT NOT NULL       -- 'YYYY-MM-DD HH:MM:SS' (UTC)
        );
    """)
    conn.executemany(
        "INSERT INTO users VALUES (?, ?, ?, ?)",
        ((i, f"user_{i:05d}", rng.choices(COUNTRIES, WEIGHTS)[0],
          (START - datetime.timedelta(days=rng.randint(0, 900))).strftime("%Y-%m-%d %H:%M:%S"))
         for i in range(1, USERS + 1)))
    statuses = ["paid"] * 85 + ["refunded"] * 5 + ["pending"] * 10
    conn.executemany(
        "INSERT INTO orders (user_id, amount_cents, status, created_at) VALUES (?, ?, ?, ?)",
        ((rng.randint(1, 100) if rng.random() < 0.1 else rng.randint(1, USERS),  # some heavy buyers
          rng.randint(199, 49_999),
          rng.choice(statuses),
          (START + datetime.timedelta(seconds=rng.randint(0, 730 * 86400))).strftime("%Y-%m-%d %H:%M:%S"))
         for _ in range(ORDERS)))
    conn.commit()
    conn.close()
    os.replace(tmp, DB_PATH)


def connect():
    """Fresh connection with every index from previous runs removed, so app.migrate() starts clean."""
    if not os.path.exists(DB_PATH):
        print("Building database (one-time, a few seconds)...")
        build()
    conn = sqlite3.connect(DB_PATH)
    for (name,) in conn.execute("SELECT name FROM sqlite_master WHERE type = 'index' AND sql IS NOT NULL").fetchall():
        conn.execute(f'DROP INDEX "{name}"')
    conn.commit()
    return conn
