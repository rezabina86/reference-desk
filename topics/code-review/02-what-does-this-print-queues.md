---
title: 02 · What does this print? — queues
summary: Four short GCD puzzles on serial vs concurrent and sync vs async, including the one that crashes.
minutes: 15
group: What does this print?
sources:
- Glassdoor · Revolut Senior iOS — live coding that needs GCD concurrency "very well" | https://www.glassdoor.com/Interview/Revolut-Senior-IOS-Developer-Interview-Questions-EI_IE1176471.0,7_KO8,28.htm
- Apple · DispatchQueue — sync on the current serial queue deadlocks | https://developer.apple.com/documentation/dispatch/dispatchqueue
- Apple Developer Forums · .sync on a concurrent queue | https://developer.apple.com/forums/thread/106319
---

*Shape: what does this print · Reported: GCD questions at Revolut; this exact ordering puzzle is the
standard warm-up form · Compiled and run with Swift 6.2 (Linux libdispatch)*

> "No running it. Tell me what prints, in what order, and which parts of the order are guaranteed."

Each puzzle starts on the main thread.

**Puzzle A**

```swift
let serial = DispatchQueue(label: "serial")
print("1")
serial.async { print("2") }
serial.sync { print("3") }
print("4")
DispatchQueue.global().async { print("5") }
print("6")
```

**Puzzle B**

```swift
let serial = DispatchQueue(label: "serial")
serial.sync {
    serial.sync { print("inner") }
}
print("after")
```

**Puzzle C**

```swift
let concurrent = DispatchQueue(label: "c", attributes: .concurrent)
concurrent.sync {
    concurrent.sync { print("inner") }
}
print("after")
```

**Puzzle D**

```swift
// Inside viewDidLoad
DispatchQueue.main.sync { print("inside") }
print("after")
```

::: A hint, if you're stuck
- There are two separate questions. Does the queue run one block at a time (serial) or several (concurrent)? Does the caller wait (sync) or not (async)?
- For each line, ask: who is waiting for whom?
- "It usually prints first" and "it's guaranteed to print first" are different answers.
:::

::: Answers
**A — `1 2 3 4`, then `5` and `6` in either order.**
`2` is queued before `3` on the same serial queue, and a serial queue runs one block at a time in
order, so `3` waits for `2`. `sync` blocks the caller until `3` finishes, so `4` comes after it.
`5` goes to another thread and `6` doesn't wait for it: usually `6` prints first, but nothing
guarantees it. In the verified run it printed `1 2 3 4 6 5` three times out of three — which is
exactly the trap: "it always prints 6 first" is an observation, not a guarantee.

**B — crash.** The outer block occupies the serial queue; the inner `sync` waits for the queue to
be free; the queue is waiting for the outer block to finish. That's a deadlock, and libdispatch
detects this one and traps rather than hanging — verified: the process died with an illegal
instruction. `after` never prints.

**C — `inner`, then `after`.** A concurrent queue can run more than one block at a time, so the
inner block doesn't need the outer one to finish. No deadlock.

**D — crash.** Same as B: the main queue is serial and you are already on it.
:::

::: The idea behind it
A *queue* is a line of work waiting to run. A *serial* queue runs one block at a time, in order —
one cashier. A *concurrent* queue may run several at once — several cashiers. That's one question,
and it's about the queue.

The other question is about you, the caller. `async` means "put my work in the line and walk away".
`sync` means "stand here until my work is done".

Mix the two up and you get the classic *deadlock*. On a serial queue, a block calls `sync` onto the
same queue. It waits for the queue to be free — but the queue is busy running that very block. Each
waits for the other, forever. On the main queue that would freeze the app, so Apple's dispatch
library spots it and crashes instead, which is easier to debug.

Ordering follows from the same picture. Inside one serial queue, order is guaranteed: one cashier,
one line. Across different queues nothing is guaranteed unless something waits. A result that
"always" comes out in one order on your machine is a race that hasn't lost yet.
:::

::: What I'm really scoring
That you separate the two axes. **Serial vs concurrent** is about the queue: how many blocks it
runs at once. **Sync vs async** is about the caller: whether it waits. Candidates who mix them up
say things like "async means background" — `DispatchQueue.main.async` is async and runs on main.

The strong answer to A also says *which* orderings are guaranteed. That habit is what stops
someone shipping code that only works because a race usually goes one way.
:::

::: What I'd ask next
- *"Why do we update UI with `main.async` and never `main.sync`?"* — `sync` from main deadlocks;
  from a background thread it blocks that thread while main is busy, and can deadlock if main is
  waiting on it.
- *"Make a thread-safe counter with GCD."* — A private serial queue: reads with `sync`, writes with
  `async`; or a concurrent queue with `async(flags: .barrier)` for writes. The barrier only works
  on a concurrent queue you created; on a global queue it's ignored and the writes race.
- *"What's the modern equivalent?"* — An actor. Same mutual exclusion, checked by the compiler,
  and no possibility of puzzle B — but beware reentrancy at every `await`.
- *"Is the main queue the same as the main thread?"* — The main queue always runs on the main
  thread; other queues can run on any thread, including main when called with `sync`.
:::
