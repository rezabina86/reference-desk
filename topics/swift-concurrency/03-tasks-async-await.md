---
title: Tasks, async and await
summary: The move that makes everything else possible — separating the work from the worker.
minutes: 8
sources:
- WWDC21 · Swift concurrency&#58; Behind the scenes | https://developer.apple.com/videos/play/wwdc2021/10254/
- SE-0461 · Run nonisolated async functions on the caller's actor by default | https://github.com/swiftlang/swift-evolution/blob/main/proposals/0461-async-function-isolation.md
---

## A task is a job, not a worker

This is the central move, and everything else follows from it.

Under the old model, "do this in the background" meant *get a thread* — hire a worker. Workers are expensive, so you couldn't have many.

Under Swift concurrency you create a **task**: a description of work to be done. A task is not a thread. It is an object on the heap, cheap enough that having tens of thousands is unremarkable. Behind them sits a small, fixed pool of actual threads that pick tasks up and run them.

**Many tasks, few threads.** That single sentence is the shape of the whole system.

> **In the office.** Stop hiring people. Just stop confusing *jobs* with *workers*.
>
> Write each job on a slip of paper and put it in a tray. A slip is not a person; it costs nothing, so you can write ten thousand. Then employ exactly **six workers, one per desk**, and have them take slips from the tray and work them.
>
> Ten thousand slips, six workers, six desks, nobody standing around. **Many slips, few workers** — that's the whole rearrangement.

## `async` and `await`

A function marked `async` is one that might need to pause. Inside it, every point where it *might* pause is marked `await`:

```swift
func loadProfile(id: String) async throws -> Profile {
    let data = try await fetch(id)      // might pause here
    return try decode(data)             // ordinary work, no pause
}
```

`await` is not an instruction to go elsewhere. It marks a place where the function may be **suspended**: put down, with a note of where it had got to, so the thread can run something else. When the answer arrives the task resumes — possibly on a different thread.

Two consequences, and they are the two people get wrong.

**`await` does not mean "background".** It means "this may pause". Which thread continues afterwards is a separate question, answered in chapter 6.

**`await` does mean "the world may have moved."** You put the work down. Other work ran. Anything you checked before the `await` may no longer be true after it. That single fact is the root of chapter 5.

> **In the office.** A marked point on the slip where the worker may set it down — with a bookmark noting exactly where they had got to — and pick up somebody else's slip instead. The bookmark is the part that matters: the desk is cleared completely, so nothing of yours occupies it while you wait.

> **Under the hood.** A synchronous function keeps its local state on the thread's stack, which is why it cannot be put down — the stack frame would have to survive, and stacks don't work that way. An `async` function is compiled differently: anything needed *across* a suspension point is stored in a heap-allocated **async frame**, while anything used only within one uninterrupted stretch stays on the stack. The chain of async frames is the runtime representation of a **continuation**. When the function suspends, its stack frame is destroyed and the thread's stack is reused by the next piece of work — nothing is left occupied.

## The cooperative thread pool

Swift's threads live in a pool with a deliberate size limit, stated by Apple plainly:

> "The new thread pool will only spawn as many threads as there are CPU cores, thereby making sure not to overcommit the system."

Six cores, six threads. Not sixteen times more. Thread explosion isn't mitigated — it is structurally impossible, because no mechanism exists that creates the seventh thread.

This is only safe because of the rule from chapter 2. If a pool thread could block, six blocked threads would mean a frozen app with no way to recover. **The pool is small because threads never block, and threads never block because `await` suspends instead.**

> **In the office.** Six desks, six workers, permanently. Nobody is hired mid-crisis, because nobody ever stands on hold — they put the slip down instead. The small permanent staff is only possible *because* of that rule, and the rule is only bearable *because* the staff is small.

> **Under the hood.** Apple calls this the **runtime contract**: every thread must always be able to make forward progress. It is why `await` suspends rather than waits, and why the runtime needs to know task dependencies — that knowledge is what lets it schedule without ever parking a thread.
>
> It is also why semaphores and condition variables are **unsafe** here rather than merely discouraged: they create a dependency the runtime cannot see, so it cannot schedule around it, and a pool thread sits blocked. `os_unfair_lock` and `NSLock` are acceptable for tight critical sections with no `await` inside, because the runtime can always progress toward the release. Set `LIBDISPATCH_COOPERATIVE_POOL_STRICT=1` to have a debug runtime catch violations.

## Switching work is now cheap

Because suspended work lives on the heap rather than on a thread's stack, a thread moving from one task to another needs no help from the operating system:

> "When threads execute work under Swift concurrency they switch between continuations instead of performing a full thread context switch. This means that we now only pay the cost of a function call instead."

A context switch costs microseconds and involves the kernel. A continuation switch costs about what calling a function costs. That difference is why a six-thread pool can service enormous numbers of tasks.

## Interleaving

Put all of the above together and you get what Apple calls **interleaving**: one thread alternating between many tasks, each taking a turn whenever it can make progress.

Worth stating plainly, because beginners always ask: *on one thread, with no extra cores, does any of this help?* Yes — enormously — because the time it reclaims was time spent waiting, and waiting never needed a core.

> **In the office.** One clerk with forty slips on the go, working whichever has something to do right now. From outside it looks like forty people. It costs one desk.
