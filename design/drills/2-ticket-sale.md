# Drill 2: Concert ticket sale

## The prompt

Design the system that sells tickets for a stadium tour.

- 60,000 seats per show, each a specific seat (section, row, number). 50 shows.
- Sales open at 10:00:00. **3 million** people are waiting.
- A user picks seats, then has 10 minutes to pay. Unpaid seats are released.
- No seat may be sold twice. Nobody may be charged without getting a seat.

**Deliver:** what happens at 10:00:00 (traffic shape), how seats are held and released, the
payment flow, and how the system protects itself.

Related labs: 02 (race conditions), 04 (stampede), 05 (idempotency), 07 (overload).

<!-- REVIEW -->

## Reviewer's questions

1. 3M people click at 10:00:00. What's your peak RPS for the first 10 seconds? What's the first
   component that falls over?
2. Do you let 3M people at the seat map at once? If not, what's the admission mechanism
   (virtual waiting room), and how is it fair? How do you stop bots from jumping the queue?
3. Two users click seat F-12 in the same millisecond. Walk through exactly how one wins. What's
   the database statement? (Lab 02.)
4. Holds expire after 10 minutes. What process releases them, and what happens if it's down? Can
   expiry be enforced *without* a background job?
5. The payment provider times out. Is the seat sold? Is the user charged? What does the user
   see, and what happens next? (Lab 05.)
6. The seat-map page shows availability. How fresh must it be? What happens if 3M users poll it
   every second? (Labs 03, 04.)
7. Every request touches the same show's rows. Is that a hot partition? How would you split it?
   (Lab 06.)
8. What's your load-shedding policy when you're over capacity? Who gets a 503 first? (Lab 07.)
9. How do you test this before the real 10:00:00?
10. What metrics are on the dashboard during the sale, and which one pages someone?

## Common mistakes

- Treating it as a normal e-commerce site. It's a burst of 1000× normal, aimed at a tiny dataset.
- `SELECT` to check availability then `UPDATE`: the classic lost update.
- Holding a DB transaction open while the user pays.
- No admission control: the database becomes the queue.

## Sketch of a strong answer

A waiting room admits users at the rate the purchase path can sustain (e.g. 2k/minute), with
randomized position at open to defeat refresh-spamming. Seat holds are a conditional update
(`UPDATE seats SET held_by = ?, held_until = now() + 10min WHERE id = ? AND (held_by IS NULL OR
held_until < now())`), so expiry is checked lazily and needs no job for correctness. Payment
uses an idempotency key per hold, and the order state machine is `held → paying → paid | released`,
with reconciliation for unknown outcomes. The seat map is served from a cache refreshed every ~1-2s
(single-flight), not queried per viewer. Partition by show, and within a hot show by section if
needed. Load tests replay a synthetic 10:00:00 burst with open-loop traffic.
