---
title: The decision guide
summary: Apple's ladder, the full map, and the questions to answer out loud.
minutes: 6
sources:
- WWDC25 · Embracing Swift concurrency | https://developer.apple.com/videos/play/wwdc2025/268/
- WWDC21 · Swift concurrency&#58; Behind the scenes | https://developer.apple.com/videos/play/wwdc2021/10254/
---

## The ladder Apple actually recommends

Not "use concurrency". A sequence — and you stop as soon as the problem is solved.

**Step 0 — everything on the main actor.**
> "Your apps should start by running all of their code on the main thread… Many apps only need to use concurrency sparingly, and some don't need concurrency at all."

No shared state means no data races, and the fastest correct program is the one that never left one domain.

**Step 1 — `async` for waiting.** The screen freezes during a network call. Make it `async` and `await` it. The main thread is released during the wait and picks the work back up when the answer arrives. No extra threads, no new domain, no new failure modes. This solves the large majority of real responsiveness problems.

**Step 2 — `@concurrent` for measured work.** Still stuttering, and Instruments shows real CPU time on the main thread — a big decode, a resize, an inference pass. Move that one function off. Profile first; the hop costs two context switches, and paying that to save nothing is a regression.

**Step 3 — an actor for shared non-UI state.** Only once several concurrent things genuinely share state that isn't UI state: a cache, a connection pool, a token store. Apple's trigger:
> "Use actors when you find that storing data on the main actor is causing too much code to run on the main thread."

**The error to avoid** is skipping to step 3 because actors are the interesting part. An actor around a stateless service serialises it for no benefit; `@concurrent` on a small decode is a straight loss.

## The isolation cheat sheet

| Spelling | Where it runs | When |
|---|---|---|
| `func f()` in a `@MainActor` type | main actor | UI state, view models |
| `nonisolated func f()` | caller's context, synchronously | pure functions inside an isolated type |
| `func f() async` (nonisolated) | **caller's actor** (SE-0461) | the normal case for async work |
| `nonisolated(nonsending) func f() async` | same — explicit spelling | when you want it stated regardless of flags |
| `@concurrent func f() async` | global executor, always | **measured** CPU work only |
| `actor A { func f() }` | A's executor, serially | genuinely shared mutable state |
| `Task { }` | inherits caller's actor | fire-off work from isolated code |
| `Task.detached { }` | nothing inherited | almost never |

## The full map

| In the office | Real name | What it is | Where it lives |
|---|---|---|---|
| A desk | Core | hardware that executes instructions | the chip |
| A worker | Thread | a worker with a stack, scheduled by the OS | the OS |
| The permanent staff, one per desk | Cooperative pool | every thread Swift concurrency has | the runtime |
| A slip of paper in the tray | Task | a unit of work, not a worker | the heap |
| A slip set aside with a bookmark | Continuation | a suspended task's saved state | the heap |
| The marked point where a slip may be set down | `await` | a point where work may be put down | compile + runtime |
| The rulebook: who may touch which records | Isolation domain | a region of state and who may touch it | **compile time only** |
| A back room with a counter in front | Actor | an isolation domain + a serial executor | both |
| The counter and its queue | Executor | runs jobs, one at a time for an actor | the runtime |
| The one counter facing the customers | `@MainActor` | the global domain backed by the main thread | both |
| Work that touches no records | `nonisolated` | belongs to no domain | compile time |
| Sending a job to the back office | `@concurrent` | always run on the pool | both |
| A photocopy rather than a key | `Sendable` | safe to carry across a boundary | **compile time only** |
| Two workers writing the same page | Data race | what the whole system exists to prevent | — |
| Hiring more staff who all stand on hold | Thread explosion | GCD's failure mode | — |
| The clerk taking a phone call mid-request | Actor reentrancy | the world moves while you're suspended | — |
| Standing in the office ≠ being authorised | isolation vs thread | the distinction in chapter 6 | — |

## The four sentences

If everything compresses to anything, it is these.

**1. Many tasks, few threads.** Tasks are cheap objects; threads are a fixed pool sized to the cores. Threads never block, which is why the pool can stay small.

**2. `await` is a suspension point, not a thread switch.** It guarantees the thread is released. It guarantees nothing about what is still true when you resume.

**3. An actor is not a worker, it's a protected region.** It gives mutual exclusion, not thread affinity. Its code runs on whatever pool thread is free.

**4. Isolation is compile-time; threads are runtime.** `@MainActor` is a domain that happens to be backed by the main thread — which is why you can be on the thread without being in the domain.

## Answer these out loud

File closed, 90 seconds each, in trade-off shape — the decision, the alternative rejected, the boundary condition.

1. Why does a small fixed thread pool work when GCD's growing one didn't?
2. What does `await` guarantee and what does it not?
3. What is the difference between an actor and a thread?
4. An actor and a serial queue both give one-at-a-time access. When does the difference matter?
5. Two callers ask an actor-backed cache for the same key at once. What happens, and why won't a lock fix it?
6. Why is `@MainActor` not the same as the main thread? Give two independent reasons.
7. Why does `MainActor.assumeIsolated` exist at all?
8. What changed in Swift 6.2 about `nonisolated async`, and what did it break?
9. When is `@concurrent` justified, and when is it a regression?
10. When is `Sendable` actually required?
11. What does structured concurrency guarantee that `Task { }` does not?
12. Where in your code do you check for cancellation, and what happens if you don't?
