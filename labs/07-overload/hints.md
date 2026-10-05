## Hint 1
An unbounded queue doesn't absorb overload; it converts it into **latency**. At +100 req/s
over capacity, the queue grows by 100 every second, and every request behind it waits longer.
Once the wait passes 500ms, *every* response arrives after the client has hung up.

## Hint 2
The backlog left over from the spike is made of requests whose clients are gone. The server
dutifully processes them all, and new requests wait behind them and time out too. That loop
keeps itself going: a *metastable failure*.

## Hint 3
Bound the queue. When it's full, `offer()` returns False right away (a fast 503). How deep should
it be? Pick the longest queueing delay you'd accept (say 100ms) and use Little's law with the
service rate (200/s).

## Hint 4
Even with a bounded queue, check `request.deadline` when a worker takes a request. If the client
will have hung up before you finish (the deadline is less than one service time away), skip it.
Don't spend a worker on a dead request.
