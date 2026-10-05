# Drill 1: URL shortener (warm-up)

## The prompt

Design a service like bit.ly.

- Users submit a long URL and get a short link like `sho.rt/aZ3kQ9`.
- Visiting the short link redirects to the long URL.
- Links never expire unless the owner deletes them.
- Owners see a click count per link.

**Scale:** 100M new links per month. Redirects outnumber creations 100:1. Redirect p99 must be
under 50ms worldwide.

**Deliver:** estimates (write QPS, read QPS, storage over 5 years), API, data model, how short
codes are generated, the redirect path, and how click counts work.

Related labs: 01 (indexes), 04 (caching), 06 (sharding).

<!-- REVIEW -->

## Reviewer's questions

1. What's your read QPS at peak? Did you design the redirect path for *that* number, or for the average?
2. How do you generate short codes? If it's random: what's the collision probability at 6
   characters of base62 after 5 years (≈ 6B links)? If it's a counter: where does the counter live,
   and what happens when that node dies? Can someone enumerate every link by incrementing codes?
3. Two users shorten the same long URL. Same code or different? What does each choice cost?
4. 301 or 302 redirect? (One lets browsers cache the redirect, which saves load but loses click
   counts. Which matters more here?)
5. Click counting: if every redirect does `UPDATE links SET clicks = clicks + 1`, what happens to
   a viral link? (Lab 02's hot row.) What would you do instead?
6. Your cache is 10× smaller than the dataset. What's the hit rate, and why? (Link popularity is very skewed.)
7. What's the shard key, and does any query need to cross shards?
8. A link is deleted. How long can the redirect keep working because of caches and CDNs? Is
   that acceptable for a malicious link?
9. How do you stop the service from becoming a phishing and malware redirector?
10. What breaks first at 10× scale?

## Common mistakes

- Designing for average QPS. Forgetting that the redirect path dominates everything.
- An auto-increment primary key exposed as the code: enumerable, and a single write bottleneck.
- Counting clicks synchronously in the redirect path.

## Sketch of a strong answer

~40 writes/s, ~4k reads/s average (~12k peak), ~3 TB over 5 years: one primary DB plus replicas
is fine; this isn't a "big data" problem, and saying so is a plus. Codes: pre-allocated ID ranges
per app server (no coordination per write), encoded base62, optionally shuffled/encrypted to
avoid enumeration. Redirect: CDN/edge cache → app → Redis → DB (cache-aside, single-flight for hot
links). Clicks: emit an event per redirect to a log/queue, aggregate asynchronously into counters;
counts are eventually consistent, and that's fine. Abuse: URL scanning at creation, and a block
list checked at the edge.
