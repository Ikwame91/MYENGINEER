"""Reference solution. Read solution/NOTES.md for the reasoning."""

import datetime


def migrate(conn):
    # recent_orders: equality on user_id, rows already ordered by (created_at, id) -> no sort.
    conn.execute("CREATE INDEX IF NOT EXISTS orders_user_created ON orders (user_id, created_at, id)")
    # daily_revenue: equality on status, then a range on created_at.
    conn.execute("CREATE INDEX IF NOT EXISTS orders_status_created ON orders (status, created_at)")
    # top_customers: find the country's users, then sum their paid orders straight from the index
    # (covering: amount_cents is in the index, so the table itself is never read).
    conn.execute("CREATE INDEX IF NOT EXISTS users_country ON users (country)")
    conn.execute("CREATE INDEX IF NOT EXISTS orders_user_status_amount ON orders (user_id, status, amount_cents)")
    # Give the planner statistics. Without them it guesses that status = 'paid' is selective
    # and drives top_customers from orders_status_created, touching 85% of the table.
    conn.execute("ANALYZE")


def recent_orders(conn, user_id, limit=20):
    return conn.execute(
        "SELECT id, amount_cents, status, created_at FROM orders "
        "WHERE user_id = ? ORDER BY created_at DESC, id DESC LIMIT ?",
        (user_id, limit),
    ).fetchall()


def daily_revenue(conn, day):
    # Compare the raw column against a half-open range so the index on created_at is usable.
    start = datetime.date.fromisoformat(day)
    end = start + datetime.timedelta(days=1)
    row = conn.execute(
        "SELECT COALESCE(SUM(amount_cents), 0) FROM orders "
        "WHERE status = 'paid' AND created_at >= ? AND created_at < ?",
        (start.isoformat(), end.isoformat()),
    ).fetchone()
    return row[0]


def top_customers(conn, country, limit=10):
    # One round trip instead of 1 + N; the database does the join and aggregation.
    return conn.execute(
        "SELECT u.name, SUM(o.amount_cents) AS total "
        "FROM users u JOIN orders o ON o.user_id = u.id "
        "WHERE u.country = ? AND o.status = 'paid' "
        "GROUP BY u.id ORDER BY total DESC, u.name ASC LIMIT ?",
        (country, limit),
    ).fetchall()
