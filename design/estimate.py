"""Back-of-envelope estimation practice. Answers within 2x count: what matters is the order of magnitude.

    python3 lab.py estimate
"""

import math
import os
import random
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from labkit import bold, dim, green, red, yellow  # noqa: E402

SUFFIX = {"k": 1e3, "m": 1e6, "b": 1e9, "g": 1e9, "t": 1e12}


def human(x):
    for unit, size in (("T", 1e12), ("B", 1e9), ("M", 1e6), ("k", 1e3)):
        if abs(x) >= size:
            return f"{x / size:.3g}{unit}"
    return f"{x:.3g}"


def parse(text):
    m = re.fullmatch(r"\s*([0-9]*\.?[0-9]+(?:e[+-]?\d+)?)\s*([kmbgt]?)\s*", text.lower())
    if not m:
        return None
    return float(m.group(1)) * SUFFIX.get(m.group(2), 1)


def q_qps(rng):
    dau = rng.choice([5e6, 20e6, 50e6, 200e6])
    per_user = rng.choice([10, 20, 50, 100])
    avg = dau * per_user / 86_400
    return (f"An app has {human(dau)} daily active users; each makes {per_user} API requests per day.\n"
            f"What's the AVERAGE request rate, in requests/second?",
            avg, f"{human(dau)} x {per_user} / 86,400 s/day ≈ {human(avg)} QPS. Peak is typically 2-3x: "
                 f"~{human(avg * 3)} QPS. Shortcut: 1M/day ≈ 12/s.")


def q_storage(rng):
    per_day = rng.choice([1e6, 10e6, 100e6])
    size = rng.choice([200, 1_000, 5_000])
    years = rng.choice([1, 3, 5])
    total_tb = per_day * size * 365 * years / 1e12
    return (f"Users create {human(per_day)} records per day, {size:,} bytes each. Keep {years} year(s).\n"
            f"How much storage, in TB (before replication)?",
            total_tb, f"{human(per_day)} x {size} B x 365 x {years} ≈ {total_tb:.3g} TB. With 3x replication "
                      f"and indexes, plan for ~{total_tb * 4:.3g} TB.")


def q_littles(rng):
    rate = rng.choice([500, 2_000, 10_000])
    latency_ms = rng.choice([20, 100, 300, 1_000])
    inflight = rate * latency_ms / 1000
    return (f"A service handles {rate:,} requests/s with an average latency of {latency_ms} ms.\n"
            f"On average, how many requests are in flight at once?",
            inflight, f"Little's law: L = λW = {rate:,}/s x {latency_ms / 1000}s = {inflight:,.0f}. "
                      f"That's how many threads, connections, or memory buffers you need. If latency spikes "
                      f"10x, so does this.")


def q_servers(rng):
    peak = rng.choice([5_000, 20_000, 80_000])
    per_server = rng.choice([500, 1_000, 2_000])
    servers = math.ceil(peak / (per_server * 0.6))
    return (f"Peak traffic is {peak:,} RPS. One server handles {per_server:,} RPS at 100% CPU.\n"
            f"Targeting 60% utilization, how many servers do you need (before redundancy)?",
            servers, f"{peak:,} / ({per_server:,} x 0.6) ≈ {servers}. Then add headroom to lose a zone: "
                     f"with 3 zones, each must carry 50% of peak → ~{math.ceil(servers * 1.5)}.")


def q_bandwidth(rng):
    qps = rng.choice([1_000, 10_000, 50_000])
    kb = rng.choice([2, 50, 500])
    mb_s = qps * kb / 1000
    return (f"An endpoint serves {qps:,} requests/s with {kb} KB responses.\n"
            f"What's the egress bandwidth, in MB/s?",
            mb_s, f"{qps:,} x {kb} KB = {mb_s:,.0f} MB/s ≈ {mb_s * 8 / 1000:.2g} Gbps. One 10 Gbps NIC moves "
                  f"~1,000 MB/s; above that you need more machines or a CDN.")


def q_transfer(rng):
    tb = rng.choice([1, 10, 50])
    gbps = rng.choice([1, 10])
    hours = tb * 1e12 / (gbps * 1e9 / 8) / 3600
    return (f"You must copy {tb} TB to a new cluster over a {gbps} Gbps link (assume full speed).\n"
            f"How many HOURS does it take?",
            hours, f"{gbps} Gbps ≈ {gbps * 125} MB/s. {tb} TB / {gbps * 125} MB/s ≈ {hours:.3g} h. In reality you "
                   f"get 50-70% of line rate and can't saturate production links, so double it. This is why "
                   f"resharding (Lab 06) is a project.")


def q_cache(rng):
    items = rng.choice([10e6, 100e6, 1e9])
    size = rng.choice([500, 2_000, 10_000])
    hot = 0.2
    gb = items * hot * size / 1e9
    return (f"You have {human(items)} items of {size:,} bytes. 20% of items get 80% of reads.\n"
            f"How much memory, in GB, to cache the hot set?",
            gb, f"{human(items)} x 0.2 x {size:,} B ≈ {gb:,.3g} GB, plus ~30-50% overhead for keys and "
                f"structures. Compare with one cache node's RAM to size the cluster.")


def q_downtime(rng):
    nines = rng.choice([("99.9%", 0.999), ("99.95%", 0.9995), ("99.99%", 0.9999)])
    minutes = 30 * 24 * 60 * (1 - nines[1])
    return (f"Your SLO is {nines[0]} availability. How many MINUTES of downtime is that per 30-day month?",
            minutes, f"43,200 min/month x {1 - nines[1]:.4f} ≈ {minutes:.3g} min. Every deploy, failover, and "
                     f"dependency outage spends this budget.")


QUESTIONS = [q_qps, q_storage, q_littles, q_servers, q_bandwidth, q_transfer, q_cache, q_downtime]


def main():
    rng = random.Random()
    print(bold("Back-of-envelope practice") + dim("  (answers within 2x count; use k/M/B/T suffixes; q to quit)"))
    score = asked = 0
    for gen in rng.sample(QUESTIONS, 5):
        question, answer, why = gen(rng)
        print("\n" + question)
        try:
            text = input("> ").strip()
        except EOFError:
            break
        if text.lower() in ("q", "quit"):
            break
        guess = parse(text)
        asked += 1
        if guess is None or guess <= 0:
            print(yellow(f"Couldn't parse that. Answer: {human(answer)}"))
        elif answer / 2 <= guess <= answer * 2:
            score += 1
            print(green(f"✔ Answer ≈ {human(answer)}"))
        else:
            off = guess / answer
            print(red(f"✘ Answer ≈ {human(answer)}") + dim(f"  (you were {off:.2g}x)"))
        print(dim(why))
    if asked:
        print(bold(f"\n{score}/{asked} within 2x.") + dim(" Run it again: the numbers change every time."))


if __name__ == "__main__":
    main()
