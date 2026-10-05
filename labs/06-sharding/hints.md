## Hint 1
Python's `hash()` of a string is randomized per process (a defense against hash-flooding
attacks). It's fine inside one process and useless for anything stored or shared. Use a hash
with a fixed definition: `hashlib.md5(key.encode()).digest()` (fine for placement; not for security).

## Hint 2
`stable_hash % N` fixes deploys but not resharding: changing N changes almost every key's
remainder. You need a scheme where adding a node only *takes* keys from others, never shuffles
keys between existing nodes.

## Hint 3
Consistent hashing: put nodes and keys on the same circle (hash space). A key belongs to the
first node clockwise from it. Adding a node only claims the arc just before it. `bisect` finds
"the first node point clockwise" in O(log n).

## Hint 4
With one point per node, arcs are wildly uneven (try it: check balance). Give each node many
points ("virtual nodes"): hash `f"{node}#{i}"` for i in range(100s).

## Hint 5
An alternative that's simpler and needs no ring: **rendezvous (highest-random-weight) hashing**.
For each key, score every node with `hash(node + key)` and pick the highest score. Compare its
cost per lookup with the ring's.
