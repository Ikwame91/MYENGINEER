"""
Shop backend: the queries behind three pages.

Every function receives an open sqlite3 connection. You may change anything in
this file, but keep each function's signature and return value the same.
"""

import datetime


def migrate(conn):
    """Runs once at startup against an index-free database. Put schema changes here."""
    conn.execute("CREATE INDEX IF NOT EXISTS orders_user_id ON orders(user_id, created_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS orders_status_created_at ON orders(status, created_at )")
    conn.execute("ANALYZE")  # give the planner statistics about the data distribution


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
    next_day = (datetime.date.fromisoformat(day) + datetime.timedelta(days=1)).isoformat()
    row = conn.execute(
        "SELECT COALESCE(SUM(amount_cents), 0) FROM orders "
        "WHERE status = 'paid' AND created_at >= ? AND created_at < ?",
        (day, next_day),
    ).fetchone()
    return row[0]


def top_customers(conn, country, limit=10):
    """Ops dashboard: customers in `country` with the highest total *paid* spend.

    Returns [(name, total_cents), ...] sorted by total desc, ties broken by name asc.
    """

    return conn.execute(
        "SELECT u.name, COALESCE(SUM(o.amount_cents), 0) AS total "
        "from orders o join users u on o.user_id = u.id "
        "where u.country = ? and o.status = 'paid' "
        "group by u.id "
        "order by total desc, u.name asc "
        "limit ?",
        (country, limit)
    ).fetchall()
    # users = conn.execute("SELECT id, name FROM users WHERE country = ?", (country,)).fetchall()
    # totals = []
    # for user_id, name in users:
    #     total = conn.execute(
    #         "SELECT COALESCE(SUM(amount_cents), 0) FROM orders WHERE user_id = ? AND status = 'paid'",
    #         (user_id,),
    #     ).fetchone()[0]
    #     totals.append((name, total))
    # totals.sort(key=lambda t: (-t[1], t[0]))
    # return totals[:limit]
