# Numbers every engineer should know (roughly)

Orders of magnitude, not exact values. They vary by hardware and year. What matters is the
*ratios*: memory is ~1000× faster than a cross-datacenter round trip.

## Latency

| Operation | Time | Feels like (if 1ns = 1s) |
|---|---|---|
| L1 cache reference | 1 ns | 1 second |
| Main memory reference | 100 ns | 2 minutes |
| Compress 1 KB (fast codec) | 2 µs | 30 minutes |
| Read 1 MB sequentially from memory | 10 µs | 3 hours |
| SSD random read (4 KB) | 20–100 µs | 1 day |
| Round trip within a datacenter | 0.5 ms | 6 days |
| Read 1 MB sequentially from SSD | 0.2–1 ms | 1 week |
| Simple indexed DB query (incl. network) | 1 ms | 2 weeks |
| Disk seek (spinning HDD) | 10 ms | 4 months |
| Round trip same continent | 20–50 ms | 1–2 years |
| Round trip across the world | 150–300 ms | 5–10 years |

## Throughput (one well-tuned machine, order of magnitude)

| Thing | Rate |
|---|---|
| Postgres/MySQL simple indexed reads | 10k–50k QPS |
| Postgres/MySQL writes (with fsync) | 1k–10k TPS |
| Redis / Memcached | 100k+ ops/s |
| Kafka partition (writes) | ~10–50 MB/s |
| Web app server (typical, non-trivial endpoint) | 100s–1000s RPS |
| 1 Gbps network | ~100 MB/s |
| 10 Gbps network | ~1 GB/s |

## Handy conversions

- 1 day ≈ **86,400 s ≈ 10⁵ s**. So 1M requests/day ≈ **12 QPS** average.
- Peak ≈ **2–3× average** for consumer traffic (more for spiky events).
- 1 million × 1 KB = **1 GB**. 1 billion × 1 KB = **1 TB**.
- 2³² ≈ 4 billion. 2⁶⁴ is large enough for any ID you'll ever need.
- A year ≈ **3 × 10⁷ s**.
- Availability: 99.9% = **8.8 hours** of downtime per year; 99.99% = **53 minutes**; 99.999% = **5 minutes**.
- Little's law: **in-flight = rate × latency**. 1000 RPS × 0.2 s = 200 concurrent requests.

Practise using these: `python3 lab.py estimate`.
