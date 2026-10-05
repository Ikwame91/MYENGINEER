# Lab 06: Sharding

**Concepts:** horizontal partitioning, hash vs range partitioning, stable hashing, the cost of
resharding, consistent hashing, virtual nodes, rendezvous hashing, hot keys and skew.

## The situation

> **#infra-planning** · Monday
> **Your tech lead:** We outgrew one database last year, so users are split across 4 shards by
> `hash(user_id) % 4`. Black Friday is in 3 weeks and we need a 5th shard. Can you check the
> router is ready?
> **On-call (yesterday):** Odd: after Tuesday's deploy, about 75% of users got "account not found"
> until we rolled back. Couldn't reproduce locally.

`app.py` is the router every service uses to find a user's shard.

## Run it

```bash
python3 lab.py run 06      # day one, a deploy, adding a shard, removing one, a celebrity
python3 lab.py check 06
```

## Investigate before you touch code

In `journal/06.md`:

1. Why did 75% of users vanish after a deploy, but never in a single local run? (Run
   `python3 -c "print(hash('user:1'))"` twice. Then look up `PYTHONHASHSEED`.)
2. With `% N`, adding one shard moves ~80% of keys. Derive that number on paper. What's the
   *minimum* fraction that has to move when going from 4 to 5 shards, and why?
3. Moving 80% of 500M users means copying ~0.8 TB *while serving traffic*. What happens to reads
   for a key during its migration?
4. Section 5: a single celebrity account makes one shard take ~37% of traffic, even though keys
   are perfectly balanced. Why can't a better hash function fix this?

## Rules

- Change only `app.py`. Standard library only.
- Draw the ring on paper before you code it. Seriously.

## Done when

`python3 lab.py check 06` passes: stable across processes, balanced (≤ 1.25× average), and
adding or removing a shard moves only the keys that have to move.

## After you pass

Read `solution/NOTES.md`, especially the hot-key section. The check doesn't grade it, but it comes
up in senior design interviews and in real incidents.
