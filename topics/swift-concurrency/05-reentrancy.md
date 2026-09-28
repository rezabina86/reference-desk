---
title: Reentrancy
summary: The honest limitation — an actor stops data races, not the world moving while you wait.
minutes: 7
sources:
- SE-0306 · Actors | https://github.com/swiftlang/swift-evolution/blob/main/proposals/0306-actors.md
- WWDC21 · Swift concurrency&#58; Behind the scenes | https://developer.apple.com/videos/play/wwdc2021/10254/
---

This is the chapter that separates people who have used actors from people who have read about them. It gets its own chapter because it is also the most-asked senior interview question in the whole area.

## The guarantee, and its edge

An actor guarantees that two pieces of code are never inside it *simultaneously*.

It does **not** guarantee that one piece of code runs start to finish without anyone else getting in.

Because when code inside an actor hits an `await`, it is put down. The actor is released. Someone else gets in. When your work resumes, the world has moved.

```swift
actor ImageLoader {
    private var cache: [URL: Data] = [:]

    func data(for url: URL) async throws -> Data {
        if let cached = cache[url] { return cached }       // A: not there
        let data = try await download(url)                 // actor released here
        cache[url] = data
        return data
    }
}
```

Two callers ask for the same image at the same time. Both reach A, both find nothing, both download, both store.

**No data race. No crash. Nothing corrupted. Two downloads.**

Doubled bandwidth, doubled cost, and every tool you own says the code is safe — because it is safe. It is just wrong.

> **In the office.** The clerk has to phone a supplier about your request. Rather than making the whole queue wait ten minutes, he sets your slip aside and serves the next person — which is the good design, and is also the catch. While your slip was aside, other requests went through. The record you checked before the call may not say the same thing after it.

## The single-threaded illusion

Apple's name for what an actor provides is the **single-threaded illusion**: no two functions ever run *concurrently* on an actor, but they may **interleave** at suspension points.

Interleaving is a feature, not a defect. It is what prevents deadlock, what frees the thread instead of blocking it, and what lets high-priority work jump the queue. Reentrancy is the bill for all three.

> **Under the hood.** SE-0306 chose reentrancy deliberately over the alternative. A non-reentrant actor — one that refuses new work while any call is suspended — deadlocks the moment two actors await each other, and reintroduces exactly the priority inversion that chapter 4 showed actors solving. The proposal's framing is that reentrancy trades a hard failure (deadlock) for a soft one (invariants needing re-validation), and the soft one is at least fixable in your own code.

## The fix

Never a bigger lock. A lock changes nothing here, because the two callers were never simultaneous — the problem is a gap in time, not simultaneous access.

The fix is to record that work is **already in flight**, and to record it **before** suspending:

```swift
actor ImageLoader {

    // MARK: - Publics

    func data(for url: URL) async throws -> Data {
        switch cache[url] {
        case .ready(let data):
            return data
        case .inFlight(let task):
            return try await task.value          // join the existing download
        case nil:
            break
        }

        let task = Task { try await self.download(url) }
        cache[url] = .inFlight(task)             // ← before any await. No window exists.

        do {
            let data = try await task.value
            cache[url] = .ready(data)
            return data
        } catch {
            cache[url] = nil                     // don't cache the failure
            throw error
        }
    }

    // MARK: - Privates

    private enum Entry {
        case inFlight(Task<Data, Error>)
        case ready(Data)
    }

    private var cache: [URL: Entry] = [:]

    private func download(_ url: URL) async throws -> Data { /* … */ }
}
```

The load-bearing line is `cache[url] = .inFlight(task)` sitting between creating the task and the first `await`. **Actor code runs uninterrupted between suspension points**, so there is no moment in which a second caller can slip past.

Two details worth keeping:

`Task { … }` inside an actor method inherits the actor's isolation, so `self.download(url)` is a normal isolated call. The explicit `self.` is required because the closure escapes.

`cache[url] = nil` in the `catch` is what makes a transient failure retryable rather than permanent. Caching the failure is the second-most-common bug in this shape.

## The general rule

**Establish your invariant before you suspend, and re-check anything you assumed after you resume.**

That covers every case in this family, and the family is large: the same shape recurs as a token-refresh actor, a mutation queue, a generic in-flight registry, and a deduplicating network layer. Learn it once and you have all four.

**The sentence to have automatic:** *"Actors guarantee no data races, not atomicity across suspension points — every invariant has to be re-validated after every `await`."*
