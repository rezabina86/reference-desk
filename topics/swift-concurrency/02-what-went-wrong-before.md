---
title: What went wrong before
summary: Callbacks, GCD thread explosion, locks — and the single root cause underneath all three.
minutes: 5
sources:
- WWDC21 · Swift concurrency&#58; Behind the scenes | https://developer.apple.com/videos/play/wwdc2021/10254/
- WWDCNotes · Behind the scenes (transcript detail) | https://wwdcnotes.com/documentation/wwdc21-10254-swift-concurrency-behind-the-scenes/
---

Swift concurrency is not a new way to do the same thing. It is a response to three specific failures, and it is much easier to hold in your head if you know what it was reacting to.

## Callbacks

The first answer to waiting: hand over a piece of code to run when the answer arrives, and return immediately.

```swift
loadUser(id) { user in
    loadAvatar(user) { image in
        resize(image) { small in
            display(small)          // three levels deep, and no error handling yet
        }
    }
}
```

It works, and it has three problems. It nests — each step buries the next. Errors must be threaded through by hand at every level. And nothing forces you to call the callback: forget one branch and the operation silently never finishes, with no complaint from the compiler.

## GCD, and thread explosion

Grand Central Dispatch let you hand work to queues and managed threads for you. A big improvement, with one structural flaw: **when a thread blocked, GCD brought up another thread** to keep the remaining work moving.

Apple's own example:

> A news app updating a hundred feeds. Each network callback needs the database, and blocks waiting for it. GCD sees blocked threads with work still queued, so it creates more. On a six-core iPhone you end up with roughly **sixteen times more threads than cores**.

Every one of those threads holds its stack. The OS tries to give each a fair share, so it context-switches constantly. The device now spends most of its energy on the bookkeeping of having too many threads.

This is **thread explosion**, and it is the specific failure Swift concurrency was built to make impossible.

> **In the office.** Whenever a worker is stuck on hold, the manager hires another so the work keeps moving. Soon there are ninety-six people in a six-desk office, almost all on hold, and most of the day goes on deciding who gets to sit down.

## Locks

The standard answer to shared data: a lock. One holder at a time, everyone else waits.

Locks work, and they cost three things.

They are a **convention, not a barrier** — the data is still reachable, and the protection holds only while every piece of code remembers to take the lock, forever.

Two locks taken in opposite orders by two threads produce a **deadlock**, where both wait for each other permanently.

And a thread waiting on a lock is a blocked thread, which in a GCD world causes the section above.

> **In the office.** A single key to the cabinet. It works — but the cabinet is still standing open, so the protection lasts exactly as long as everyone's memory. And two workers who take two keys in opposite orders wait for each other, politely, forever.

## The root cause

Read those two together and the common factor is blocking.

**A blocked thread is a thread that is occupied but not working**, and every bad outcome above follows from having a lot of them. Thread explosion is blocked threads multiplying. Deadlock is blocked threads that will never unblock. Even the callback pyramid exists because the alternative — writing it straight and waiting — would block.

So Swift's design starts from one rule: **threads must never block.** Everything in the next chapter is a consequence of taking that seriously.
