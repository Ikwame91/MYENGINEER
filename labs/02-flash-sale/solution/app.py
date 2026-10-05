"""Reference solution. Read solution/NOTES.md for the reasoning."""

from shop import PaymentDeclined


def buy(conn, payments, user_id, item_id):
    # 1. Reserve a unit atomically. The check and the decrement are one statement, so the
    #    database serializes them and two buyers can't both take the last unit.
    reserved = conn.execute(
        "UPDATE items SET stock = stock - 1 WHERE id = ? AND stock > 0", (item_id,)
    ).rowcount == 1
    conn.commit()
    if not reserved:
        return False

    # 2. Call the payment provider with no transaction open: never hold a lock across a network call.
    try:
        payments.charge(user_id)
    except PaymentDeclined:
        # Compensate: give the unit back so someone else can buy it.
        conn.execute("UPDATE items SET stock = stock + 1 WHERE id = ?", (item_id,))
        conn.commit()
        return False

    # 3. Record the sale.
    conn.execute("INSERT INTO orders (user_id, item_id) VALUES (?, ?)", (user_id, item_id))
    conn.commit()
    return True
