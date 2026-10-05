# Drill 3: Social news feed

## The prompt

Design the home timeline for a social network.

- Users follow other users. The home feed shows recent posts from people you follow, newest first.
- 300M daily active users. Each opens the feed ~10 times a day. Posting is ~1 post per user per
  day on average.
- Most users follow ~200 accounts. Some accounts have **100M followers**.
- The feed must load in under 200ms (p99).

**Deliver:** estimates, data model, how a feed is built (on write? on read?), how celebrity posts
are handled, and how new posts appear.

Related labs: 01 (indexes), 03 (replicas), 04 (caching), 06 (hot keys).

<!-- REVIEW -->

## Reviewer's questions

1. Feed reads per second vs posts per second? What does that ratio tell you about where to do the work?
2. **Fan-out on write** (push each post into followers' feeds) vs **fan-out on read** (pull from
   followees at read time). Compute the cost of each for an average user and for a 100M-follower celebrity.
3. A celebrity posts. With fan-out on write, how many writes is that, and how long until the last
   follower sees it? What does that do to your queue? (Lab 07.)
4. What do you do with users who haven't logged in for a year? Do you still fan out to them?
5. Where is the precomputed feed stored, how big is it per user, and how many entries do you keep?
6. A user follows someone new. Does their feed update immediately? Should it?
7. A post is deleted, or the author blocks you. How does it leave every feed it was pushed to?
8. Ranking ("top posts") instead of reverse-chronological: what changes in the architecture?
9. What's the shard key for posts, for feeds, and for the follow graph? Which queries cross shards? (Lab 06.)
10. A user posts and immediately refreshes their own profile. Do they see their post? (Lab 03.)

## Common mistakes

- Pure fan-out on read: the feed query merges 200 timelines across many shards on every open.
- Pure fan-out on write: a celebrity post becomes 100M writes.
- Ignoring the read:write asymmetry (~30k feed reads/s vs ~3.5k posts/s average, before peaks).

## Sketch of a strong answer

Hybrid. Fan out on write for normal accounts into a per-user feed list in an in-memory store
(keep the last ~500 post IDs, not full posts). Celebrity posts (follower count > threshold) are
**not** fanned out; they're merged in at read time from a small, heavily cached "celebrity recent
posts" set. Skip fan-out for inactive users and build their feed on demand when they return.
Posts are stored once, sharded by post ID or author, and hydrated by ID with batch reads.
Deletes are filtered at read time (tombstones) and cleaned up lazily. Read-your-writes for your
own posts is handled by merging the user's own recent posts client-side or via session routing.
