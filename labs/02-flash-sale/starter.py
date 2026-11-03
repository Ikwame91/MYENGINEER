"""
Flash-sale checkout.

buy() is called concurrently by many request handlers on several app servers, each handler with
its own database connection. You may change anything in this file, but keep the signature and
return value of buy().
"""

from shop import PaymentDeclined


def buy(conn, payments, user_id, item_id):
    """Sell one unit of item_id to user_id.

    Returns True if the user bought it (they were charged and an order exists),
    False if it's sold out or their card was declined.
    """
    (stock,) = conn.execute("SELECT stock FROM items WHERE id = ?", (item_id,)).fetchone()
    if stock <= 0:
        return False

    try:
        payments.charge(user_id)
    except PaymentDeclined:
        return False

    conn.execute("UPDATE items SET stock = ? WHERE id = ?", (stock - 1, item_id))
    conn.execute("INSERT INTO orders (user_id, item_id) VALUES (?, ?)", (user_id, item_id))
    conn.commit()
    return True
