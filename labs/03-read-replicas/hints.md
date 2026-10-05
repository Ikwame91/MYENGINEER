## Hint 1
Two different bugs. **Stale own reads**: you write to the primary, then immediately read from a
replica that hasn't applied your write yet. Even 10ms of lag is enough. **Time travel**:
`random.choice` sends one refresh to the fresh replica and the next refresh to the lagging one.

## Hint 2
Time-based rules ("primary for N seconds after a write") guess at lag. Lag isn't bounded: an
analytics query, a vacuum, or a network blip can make it seconds or minutes. Instead of time,
use **position in the log**.

## Hint 3
`update_name` gets an LSN back from `primary.write`. Save it in `session.state`. A replica can
serve this session's read if `replica.applied_lsn >= that LSN`.

## Hint 4
Monotonic reads need the same idea for *reads*: after reading from a node, the session has seen
everything up to that node's `applied_lsn`. Remember the max LSN you've written **or seen**.

## Hint 5
If no replica is fresh enough, going to the primary is correct but expensive. Even worse: reading
from the primary raises your watermark to the primary's latest LSN, which no replica has yet,
so you get stuck there. Replica-1 is usually only ~30ms behind. What if you waited a little?
