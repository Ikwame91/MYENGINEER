"""
Shop backend: the queries behind three pages.

Every function receives an open sqlite3 connection. You may change anything in
this file, but keep each function's signature and return value the same.
"""


def migrate(conn):
    """Runs once at startup against an index-free database. Put schema changes here."""
    pass


def recent_orders(conn, user_id, limit=20):
    """'My orders' page: the user's most recent orders, newest first.

    Returns [(order_id, amount_cents, status, created_at), ...]
    """
    return conn.execute(
        "SELECT id, amount_cents, status, created_at FROM orders "
        "WHERE user_id = ? ORDER BY created_at DESC, id DESC LIMIT ?",
        (user_id, limit),
    ).fetchall()


def daily_revenue(conn, day):
    """Finance report: total amount_cents of *paid* orders created on `day` ('YYYY-MM-DD', UTC)."""
    row = conn.execute(
        "SELECT COALESCE(SUM(amount_cents), 0) FROM orders "
        "WHERE status = 'paid' AND date(created_at) = ?",
        (day,),
    ).fetchone()
    return row[0]


def top_customers(conn, country, limit=10):
    """Ops dashboard: customers in `country` with the highest total *paid* spend.

    Returns [(name, total_cents), ...] sorted by total desc, ties broken by name asc.
    """
    users = conn.execute("SELECT id, name FROM users WHERE country = ?", (country,)).fetchall()
    totals = []
    for user_id, name in users:
        total = conn.execute(
            "SELECT COALESCE(SUM(amount_cents), 0) FROM orders WHERE user_id = ? AND status = 'paid'",
            (user_id,),
        ).fetchone()[0]
        totals.append((name, total))
    totals.sort(key=lambda t: (-t[1], t[0]))
    return totals[:limit]
