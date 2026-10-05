# Engineer, Not Vibe Coder

What a software engineer should know and practise in the age of AI.

## The core idea

The line between an engineer and a vibe coder isn't whether you use AI. It's whether you could
have caught the mistake.

- A vibe coder accepts output they can't evaluate.
- An engineer uses AI to go faster on things they understand, and treats everything it produces
  as a draft from a confident junior.

## 1. Fundamentals you can't outsource

- **Reading code fluently.** You now read far more code than you write. The core skill is spotting
  what's wrong, unnecessary, or subtly off in code you didn't type.
- **Data structures, algorithms, and complexity.** Not for interviews, but to notice when generated
  code is quadratic on a list that will grow to a million rows.
- **How the stack works underneath.** HTTP, databases (indexes, transactions, isolation levels),
  memory, concurrency, networking. AI-written code fails at exactly these seams.
- **Debugging from first principles.** Form a hypothesis, isolate, reproduce, read the stack trace
  and logs. Pasting the error back into the chat until it goes away is the vibe coder's signature move.

## 2. Judgment (the scarce part)

- **System design and trade-offs.** AI gives you a solution. You need to know whether it's the
  right one for your scale, team, and constraints, and what it will cost in two years.
- **Problem framing.** Working out what should be built, and what shouldn't, is most of the job.
  A precise spec gets good output; a vague one gets plausible garbage.
- **Taste for simplicity.** AI over-produces: extra abstractions, needless dependencies, defensive
  code for cases that can't happen. Great engineers delete.

## 3. Engineering discipline

- **Testing.** Tests are how you verify code you didn't write. Write or carefully review them
  yourself; AI-written tests often just assert whatever the code already does.
- **Security.** Injection, authentication vs authorization, secrets handling, input validation,
  dependency risk. Generated code is routinely insecure by default.
- **Production awareness.** Observability, failure modes, rollbacks, migrations, and what happens
  at 3am when it breaks. Code that runs on your machine is only the start.
- **Version control and review.** Small commits, meaningful diffs, and never merging something you
  can't explain line by line.

## 4. Using AI well

- **Know its strengths:** boilerplate, familiar patterns, exploration, explaining unfamiliar code.
- **Know its weaknesses:** novel logic, consistency across a large codebase, anything specific to
  your system's invariants.
- **Work in verifiable steps.** Give it context and constraints, break the work down, and check
  output against reality: run it, test it, read the docs.
- **Use it to learn, not only to ship.** Ask why, ask for alternatives, ask what would break.

## 5. The human layer

- **Communicate clearly in writing.** Design docs, PR descriptions, explaining trade-offs to non-engineers.
- **Own outcomes.** "The AI wrote it" is never an answer. If you shipped it, it's yours.

## The self-test

Before shipping anything, ask:

1. Can I explain why it works?
2. Can I explain how it fails?
3. Do I know what I'd change if the requirements shifted?

If yes to all three, you're engineering, however much of it AI typed. If not, you're vibe coding,
even if you typed every character yourself.

## Pre-merge checklist

- [ ] I have read every line of the diff
- [ ] I can explain each change without looking at the chat
- [ ] Tests exist, and I checked that they test behaviour, not just the current implementation
- [ ] I considered failure cases: bad input, empty data, network errors, concurrency
- [ ] No secrets, no unvalidated input, no unnecessary new dependencies
- [ ] I removed anything the AI added that isn't needed
- [ ] I know how to roll this back

## Keeping the muscle strong

Regularly do some work without AI:

- Debug a hard bug by hand
- Design a system on paper before prompting
- Implement something from a spec or a paper
- Read a well-regarded open-source codebase

That keeps the evaluating muscle strong, and that muscle is the one you'll be paid for.

---

*How this repo maps to the principles:* every lab is "debug from first principles" plus "how the
stack works underneath". Every `check.py` is a test that verifies behaviour, not implementation.
Every `NOTES.md` is "how it fails" and "what I'd change if requirements shifted". The journal is
practice for "communicate clearly in writing".
