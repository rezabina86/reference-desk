---
title: ARC under concurrency
summary: Why the count is thread-safe and the object isn't, what a task keeps alive, and which thread runs deinit.
minutes: 8
sources:
- Swift · RefCount.h (runtime source) | https://github.com/swiftlang/swift/blob/main/stdlib/public/SwiftShims/swift/shims/RefCount.h
- SE-0371 · Isolated synchronous deinit | https://github.com/swiftlang/swift-evolution/blob/main/proposals/0371-isolated-synchronous-deinit.md
- SE-0302 · Sendable and @Sendable closures | https://github.com/swiftlang/swift-evolution/blob/main/proposals/0302-concurrent-value-and-concurrent-closures.md
---

This chapter is the seam between this topic and the concurrency one. It answers a question people often assume away in both directions: *if two threads share an object, does ARC protect me?*

Partly. It protects the count. It does not protect the object.

## The count is atomic; the contents are not

The reference count lives in an `atomic` word in the object's header. Two threads retaining and releasing the same object at the same instant cannot corrupt it, cannot lose an increment, and cannot cause a premature free. That is a property of the runtime's data layout, not of your code, and it holds whatever you do.

What it buys you is exactly one guarantee: **while you hold a strong reference, the object will not be destroyed underneath you.** That's real, and it's why passing an object between threads never produces the chapter 1 use-after-free on its own.

What it does not touch is the object's *state*. Two threads calling `account.balance += 100` race on `balance` just as hard as they ever did. ARC keeps the book on the shelf; it says nothing about two people writing on page 40 at once.

> **In the library.** The tally slip is written in a special pen that two hands can't smudge — the count is always exactly right. The pages are ordinary paper.

This is the whole reason `Sendable` exists as a separate idea from reference counting, and why a `final class` with only `let` properties can be `Sendable` while the same class with one `var` cannot. Counting safety is free and automatic; state safety is the thing you have to design.

## Atomic isn't free

Each retain and release is an atomic read-modify-write on a word that other cores may be touching. In a loop over a large collection of class instances, or a chain of `weak` reads (chapter 4), that traffic is measurable — it's cache-line contention, not just instruction count.

Two things follow, in this order of importance.

**Don't optimise it by reflex.** The compiler removes most redundant pairs, and the remainder is usually dwarfed by whatever the code is actually doing. Chasing retain traffic without a profile is the classic wasted afternoon.

**When it does show up, it shows up as a shape.** Time Profiler attributing real time to `swift_retain` / `swift_release`, typically from a tight loop over reference types. The fix is structural — values instead of references in the hot path, or hoisting a weak read out of a loop — not micro-tweaks.

## What a task keeps alive

A `Task` holds its closure until it finishes, and the closure holds its captures (chapter 6). So the rule is short: **anything a running task mentions stays alive until that task ends.**

That is usually correct and often the point. An upload that must complete should keep its uploader alive. The cases to watch are the ones where "until it ends" isn't a bound:

- a task looping over an `AsyncStream` that never terminates
- a task stored on the object it captures — the cycle from chapter 6
- a detached task that outlives the screen that started it, still holding a view model

Structured concurrency helps by construction: `async let` and task groups end before their scope does, so their captures can't outlive it. Unstructured `Task { }` is the one you have to reason about, and cancellation is how you bound it. Cancelling doesn't kill anything on its own — the task still has to notice and return — but returning is what releases the captures.

## Actors hold references like anything else

An actor is a class, so it is reference counted, and everything it stores it stores strongly. A cache actor holding view models keeps them alive; a task stored in an actor's dictionary keeps its closure alive. Isolation says who may *touch* state; it says nothing about how long that state lives.

The cycle shapes from chapter 5 all still apply inside actors, with one twist: you can't break one from outside, because you can't reach in without `await`. That makes "the actor holds everything for ever" a common shape — an in-flight-task registry that never removes finished entries is a cache with no eviction (shape 5), wearing a concurrency hat.

## Which thread runs deinit

Whichever thread released last. That may be a background thread, the main thread, or a cooperative-pool thread running some unrelated task — the object has no say in it, and neither do you.

This produces a specific, nasty crash class: a `deinit` that touches UIKit, or a `@MainActor`-isolated property, from whatever thread happened to drop the last reference. It fires rarely, in release builds, on other people's devices.

Swift's answer is `isolated deinit`, implemented in Swift 6.2:

```swift
@MainActor
final class Screen {
    let view: UIView
    isolated deinit {
        view.removeFromSuperview()   // guaranteed to run on the main actor
    }
}
```

Without it, a `deinit` on an actor or a global-actor-isolated class cannot touch the isolated state at all — the restriction SE-0327 imposed, which is why so much code grew an explicit `close()` or `invalidate()` method instead. Both patterns are still reasonable; the explicit teardown has the advantage that it runs at a point you chose rather than at an arbitrary release.

Worth noticing what an isolated `deinit` costs: if the last release happens off the main actor, the destruction has to hop, so the object's death is now asynchronous with respect to whoever released it. Determinism in *order* is preserved; determinism in *timing* is not.

> **Under the hood.** The state machine in `RefCount.h` is what makes the concurrent case safe at all. Between "strong count hit zero" and "the memory is gone" there are four states, and a `weak` read arriving from another thread during any of them has a defined answer — `nil` — rather than a race against the deallocation. That's why `weak` reads are a runtime call and not a pointer dereference, and it's why they cost what they cost.

## The two sentences to have ready

**ARC is thread-safe; your object is not.** The count is atomic, so an object won't be freed while you hold a reference. Nothing about that serialises access to its properties — that's what actors, locks and `Sendable` are for.

**Reference counting decides lifetime; isolation decides access.** They are orthogonal, they are enforced in different places — one at runtime, one at compile time — and most confusion here comes from expecting either to do the other's job.
