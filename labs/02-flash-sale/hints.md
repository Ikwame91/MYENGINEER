## Hint 1
The bug is **read-modify-write**: read `stock`, compute `stock - 1` in Python, write it back.
Between your read and your write, 60 other handlers did the same thing with the same number.
Their writes overwrite each other: a *lost update*.

## Hint 2
A `threading.Lock` only protects threads inside **one** process. There are 4 server processes.
The one thing all of them share is the database, so the coordination has to happen there.

## Hint 3
Make the check and the change one atomic statement:
`UPDATE items SET stock = stock - 1 WHERE id = ? AND stock > 0`
Then look at `cursor.rowcount`: 1 means you got a unit, 0 means it's sold out.

## Hint 4
An explicit `BEGIN` followed by a `SELECT` takes a *shared* lock. When two transactions both
hold shared locks and both try to upgrade to write, neither can proceed: a deadlock. SQLite
reports it as "database is locked". Postgres would abort one with a serialization or deadlock
error. If you want a transaction, say up front that you'll write (`BEGIN IMMEDIATE`, or
`SELECT ... FOR UPDATE` in Postgres).

## Hint 5
Order of operations: reserve the unit → charge the card → record the order. If the charge
fails, *compensate*: put the unit back. Don't keep a transaction open while you wait on the
payment provider.
