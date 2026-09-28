---
title: Actors
summary: What an actor is, and the difference between an actor and a thread.
minutes: 9
sources:
- SE-0306 · Actors | https://github.com/swiftlang/swift-evolution/blob/main/proposals/0306-actors.md
- SE-0392 · Custom Actor Executors | https://github.com/swiftlang/swift-evolution/blob/main/proposals/0392-custom-actor-executors.md
- WWDC21 · Swift concurrency&#58; Behind the scenes | https://developer.apple.com/videos/play/wwdc2021/10254/
---

Chapter 3 solved *too many threads*. It did nothing about *shared data*. That is this chapter.

## What an actor is

An **actor** is a thing that owns some data and is the only route to it.

```swift
actor BankAccount {
    private var balance: Decimal = 0

    func deposit(_ amount: Decimal) {
        balance += amount
    }

    func currentBalance() -> Decimal {
        balance
    }
}
```

From outside you cannot touch `balance`. You can only ask the actor to do something, and asking costs an `await`:

```swift
let account = BankAccount()
await account.deposit(100)
let b = await account.currentBalance()
```

Two callers can never be inside the actor at the same moment, so `balance += 100` cannot lose an increment. That safety is **structural** — there is no other route to the data — rather than a rule everyone has to remember. This is the difference between an actor and a lock, and it is the entire point.

> **In the office.** Take the cabinet out of the open office. Put it in a back room, with a counter and a clerk in front of it. Now nobody *can* reach the cabinet — not "shouldn't", can't, there is a wall. You write your request, hand it across, and wait your turn. Two people can no longer spoil the same page because neither of them ever touches it.

> **Under the hood.** SE-0306 defines an actor as "a reference type that protects access to its mutable state." Cross-actor access is permitted in exactly two forms: reading an immutable `let` within the same module, or an asynchronous call. Everything else is a compile error, not a convention.

## How is an actor different from a thread?

This is the most common point of confusion, and the reason is that the question quietly assumes they are the same kind of thing. They are not.

**A thread is a worker.** It *executes*. It has a stack, the OS schedules it onto a core, and while it runs it consumes a core.

**An actor is a protected area around data.** It does not execute anything. It has no stack. The OS has never heard of it. It is not scheduled onto a core, because it isn't the sort of thing that runs.

Asking how an actor differs from a thread is like asking how a bank vault differs from a bank teller. One is a worker, the other is a protected place workers must go through. They are not alternatives — a real system has both.

**So what runs an actor's code?** A thread from the pool in chapter 3. Which one? Whichever is free.

```swift
actor Counter {
    private var n = 0
    func bump() {
        n += 1
        print(Thread.current)   // a DIFFERENT thread on different calls
    }
}
```

Call `bump()` ten times and you may see several different threads. The actor doesn't care; nothing about its guarantee depends on which thread does the work. Conversely, one pool thread will, over a second, run work belonging to dozens of actors.

*(Swift discourages inspecting `Thread.current` from concurrent code precisely because the answer is meaningless to the model — but as a one-off demonstration it makes the point better than any paragraph.)*

**The guarantee, stated exactly.** An actor gives **mutual exclusion, not thread affinity**. SE-0392 is explicit: a serial executor guarantees that for any two jobs, all of one happens before all of the other — and deliberately says nothing about threads. Apple's wording: *"Swift's concurrency design is intentionally vague about the details of how code is actually run."*

| | Thread | Actor |
|---|---|---|
| What it is | a worker that executes | a protected region of data |
| Owned by | the operating system | your program |
| Has a stack | yes, ~0.5 MB+ | no |
| Scheduled onto a core | yes | never — it doesn't run |
| How many | hundreds, each costs | millions, they're just objects |
| Created because | you need something executed | you have state to protect |
| Guarantees | nothing about your data | one access at a time |
| Runs on | a core | whatever pool thread is free |

**The one sentence:** *a thread is who does the work; an actor is what the work must go through to reach the data.*

> **In the office.** The clerk is a worker. The counter is a place. The counter doesn't *do* anything — it is the arrangement that forces requests through one at a time. Whoever happens to be free staffs it, and it may be a different person each time. The counter never notices, and the guarantee never depended on who was standing there.

## What an actor is made of

Precisely, an actor is two things stuck together — and separating them is what makes chapter 6 make sense.

**An isolation domain.** A compile-time idea: a named region of state, plus the rule that only code belonging to that region may touch it. This exists entirely in the compiler. It has no runtime existence; it is checked and then erased.

**A serial executor.** A runtime object that accepts jobs and runs them one at a time. The thing that turns the compile-time promise into actual behaviour.

The split matters because the halves are independent. The domain says *who may touch this state*. The executor says *where the work runs*. Chapter 6 is entirely about what happens when people assume those are one question.

> **Under the hood.** SE-0392 formalises this. Every actor has an `unownedExecutor` — by default a fresh serial executor, but you can supply your own. Two different actors can be given the *same* executor and both remain correctly isolated from each other, because isolation is a compile-time property of the types, not of which executor they share. That is the cleanest available proof that isolation and execution are different things.

## Actor versus serial queue

The closest older tool is a serial `DispatchQueue`. Both give one-at-a-time access. They differ in what happens when someone has to wait — which is exactly the theme of chapter 2.

| | Serial DispatchQueue | Actor |
|---|---|---|
| Nobody's using it | dispatches to a thread — a context switch | current thread hops straight in, ~a function call |
| Someone's using it | **blocks the calling thread** | **suspends the caller**, frees the thread |
| Blocked callers | occupy threads → thread explosion | none — nothing blocks |
| Order of work | strictly FIFO | not guaranteed FIFO |
| High-priority work stuck behind low | yes — priority inversion | no — can be run ahead |

That last row is worth understanding rather than memorising. With a serial queue, work runs in arrival order; a high-priority item behind five low-priority ones waits for all five. The old workaround was to boost the priority of everything ahead of it, which makes the five finish sooner but doesn't change that they must finish first. An actor isn't FIFO: pending work can be reordered, so the important item can go next.

> **In the office.** A one-at-a-time window where waiting customers stand in line, versus one where you drop off a slip and go do something else. With the line, an urgent request behind five routine ones waits for all five, no matter how urgent. With slips, the urgent one can be pulled forward.

> **Under the hood.** SE-0306 states plainly that "tasks awaiting an actor are not guaranteed to be run in the same order they originally awaited that actor." Non-FIFO isn't sloppiness — it is the mechanism that solves priority inversion, and it is why an actor is not a drop-in replacement for a serial queue in code that silently depended on ordering.

## Hopping between actors is cheap

When code on actor A calls actor B and B is free, no thread changes and the OS is not involved — the runtime suspends A's work item and starts B's on the same thread. Apple: *"the thread did not block while hopping actors… hopping did not require a different thread."* The cost is close to a function call.

When B is busy the caller is suspended and the thread goes off to do other work. Still no blocking.

Compare with a serial queue, where "busy" means the calling thread waits — which is where thread explosion came from.

> **In the office.** If the back room is free, the clerk you are already talking to simply walks through — no new person, no handover. If it is busy, you leave your slip and go; nobody stands waiting.
