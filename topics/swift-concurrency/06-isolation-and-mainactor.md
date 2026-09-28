---
title: Isolation, and why @MainActor is not the main thread
summary: Isolation domains are compile-time; threads are runtime. Four reasons they're not the same.
minutes: 10
sources:
- SE-0316 · Global Actors | https://github.com/swiftlang/swift-evolution/blob/main/proposals/0316-global-actors.md
- SE-0461 · Run nonisolated async functions on the caller's actor by default | https://github.com/swiftlang/swift-evolution/blob/main/proposals/0461-async-function-isolation.md
- WWDC25 · Embracing Swift concurrency | https://developer.apple.com/videos/play/wwdc2025/268/
- Donny Wals · Setting default actor isolation in Xcode 26 | https://www.donnywals.com/setting-default-actor-isolation-in-xcode-26/
- Malcolm Hall · @MainActor does not always mean main thread (2023, pre-SE-0461) | https://www.malcolmhall.com/2023/01/31/mainactor-does-not-always-mean-main-thread/
---

## What an isolation domain is

Chapter 4 split an actor into two halves. This chapter is about the compile-time half.

An **isolation domain** is a region of state plus the rule about who may touch it. Every piece of code belongs to exactly one of three kinds:

- **No domain** — `nonisolated`. It touches no protected state, so it needs no permission.
- **An actor instance's domain** — the code of `actor BankAccount` belongs to whichever instance it runs on. Each instance is its own domain.
- **A global actor's domain** — `@MainActor` being the one everybody knows. One domain, shared by the whole program.

The compiler's entire job here is to check, wherever code touches state, that the code and the state are in the same domain. If not, you need an `await` to get there, and what you carry across must be safe to carry.

**This is all checked and then thrown away.** Isolation has no runtime representation. It is not a flag the program can inspect while running. It is a rule enforced before the app ever launches.

> **In the office.** The rulebook entry saying which records each part of the building may touch. It lives in the rulebook, not in the building. The auditor reads it before opening day, confirms nobody's job description breaks it, and files it away. Nothing about it is visible once the doors open.

## What `@MainActor` is

`@MainActor` is a **global actor**: an actor of which there is exactly one for the whole program, referred to by name rather than by holding an instance.

```swift
@MainActor
final class ProfileViewModel {
    private(set) var state: State = .loading   // main-actor state

    func load() async {
        state = .loading
        let profile = try? await repository.profile()
        state = profile.map(State.loaded) ?? .failed
    }
}
```

Everything visible to the user lives in this domain, and the reason is coherence rather than speed. A screen must never show half the old state and half the new. Funnelling every visible change through one domain, one at a time, makes a half-updated screen impossible.

Its executor is the main thread. `MainActor` is the one actor with a dedicated thread, because the platform requires it: UIKit and AppKit must be driven from that specific thread.

> **In the office.** One counter faces the customers: the display board, the shop window, the queue number on the screen. Exactly one in the whole company, and everything the public can see goes through it. Its clerk is one specific named person who does nothing else — because the display equipment only responds to them.

> **Under the hood.** In Xcode 26 the build setting `SWIFT_DEFAULT_ACTOR_ISOLATION` can put every unannotated declaration in a module into the main-actor domain, and it is the default for new app projects. It accepts exactly two values, `MainActor` and `nonisolated` — there is no diagnostic-only mode. Apple's framing is that an app should *start* entirely on the main actor and introduce concurrency only where profiling shows it is needed.

## Why it is not "the main thread"

They are so closely related that treating them as one thing usually produces correct code, which is exactly why the confusion survives. Four reasons, in increasing order of how convincing they are.

### 1 — they are different categories of thing

The main thread is a **runtime resource**: an actual OS thread, with a stack, that the scheduler puts on a core. It exists while the program runs. You can count it.

`@MainActor` is a **compile-time contract** about which state a piece of code may touch. It does not exist at runtime at all.

One is a fact about execution. The other is a rule about access. They are connected — the rule is enforced *by* using that thread — but they are not the same statement, any more than "holding the key" and "being authorised" are the same statement.

### 2 — running on the main thread does not make you main-actor isolated

This one you can demonstrate in ten seconds:

```swift
DispatchQueue.main.async {
    self.label.text = "hello"      // error: main actor-isolated property
}                                  // …on the main thread.
```

That closure runs on the main thread. Guaranteed, by name. And the compiler still refuses, because the closure is not *declared* as belonging to the main actor's domain. Being physically on the thread tells the compiler nothing, because the compiler is not reasoning about threads.

The bridge Apple provides is an assertion, not a hop:

```swift
DispatchQueue.main.async {
    MainActor.assumeIsolated {
        self.label.text = "hello"   // fine
    }
}
```

`assumeIsolated` doesn't move anything. It says *I know I'm already there, take my word for it and check me at runtime* — and it traps if you were wrong.

**The existence of this API is itself the proof.** If being on the main thread and being main-actor isolated were the same thing, there would be nothing to assume.

Contrast `await MainActor.run { }`, which genuinely does move the work. Assert versus hop — two tools for two situations, and knowing which you need is knowing this distinction.

> **In the office.** Standing in the front office is not the same as being authorised at the front desk. A courier can be physically inside the front office and still not be allowed to change the display board, and no amount of standing there grants it — authorisation is written in the rulebook, standing there is just where your feet happen to be. `assumeIsolated` is the courier saying *check my badge, I really do have authorisation* — a sentence that would be meaningless if being in the room were the authorisation.

### 3 — the guarantee is about state, not location

What main-actor isolation buys you is: *no other code is touching this state at the same time.*

Running on one specific thread is how that guarantee happens to be delivered **for this one actor**. Every other actor gets the identical guarantee with no dedicated thread at all — its work runs on whatever pool thread is free.

So "runs on the main thread" is a property of `MainActor`'s particular executor. It is not what isolation *means*. Define `@MainActor` as "the main thread" and you have defined it by an implementation detail that no other actor shares.

### 4 — the thread behaviour changed and the isolation didn't

The most convincing one, because it is a natural experiment Swift ran on itself.

```swift
@MainActor
func refresh() async {
    let items = await loader.load()   // loader.load() is nonisolated async
    self.items = items
}
```

**Before Swift 6.2:** `load()` hopped to the cooperative pool. It ran off the main thread.
**From Swift 6.2 (SE-0461):** `load()` runs on the caller's actor. It runs *on* the main thread.

Same source. Same isolation before and after — `refresh()` was main-actor isolated in both, `load()` was nonisolated in both. Completely different thread behaviour.

If isolation and thread placement were the same thing, this change could not have happened. They moved independently, because they are independent.

> **Under the hood.** This is why articles written between 2021 and 2025 saying "a nonisolated async function runs on a background thread" are now wrong — including good ones, one of which is cited below precisely because it documents the old behaviour. SE-0338 made that the rule; SE-0461 reversed the default and introduced `@concurrent` as the explicit opt-out. The migration hazard is real: work that used to drift off the main thread by default now stays on it, so Swift 6.2 can move CPU work *onto* main in code nobody edited.

### And the one that makes it concrete

A `@MainActor` function is still main-actor isolated while it is suspended at an `await` — during which the main thread is off running something else entirely. The isolation persists across a gap in which the code is not executing on any thread at all.

**A thread cannot be borrowed and given back. A domain can.**

**For a room:** *"`@MainActor` is an isolation domain — a compile-time statement about which state you may touch. The main thread is the executor that happens to back it. `DispatchQueue.main.async` puts you on the thread without putting you in the domain, which is exactly why `MainActor.assumeIsolated` exists."*

## `nonisolated`

Belongs to no domain, because it touches no protected state.

```swift
@MainActor
final class Formatter {
    nonisolated func format(_ n: Int) -> String { "\(n)" }   // callable anywhere, no await
}
```

Free — no queue, no waiting — and the compiler holds you to the claim. Reach for protected state from nonisolated code and you are stopped at compile time.

Since SE-0461, a `nonisolated async` function runs on **the caller's actor**, start to finish, including after every `await`. "Belongs to no domain" no longer implies "runs somewhere else."

> **In the office.** Work that touches no records at all: converting a measurement, adding up figures somebody handed you. No counter, no queue, no permission. Anyone, anywhere, any number at once.

## `@concurrent`

The explicit instruction to leave the caller's actor and run on the cooperative pool.

```swift
@concurrent
func decodeImage(_ data: Data) async -> Image { /* … */ }
```

It always hops — even from a caller that had no actor, where the hop buys nothing. `async`-only, and mutually exclusive with `@MainActor`.

**When it is justified:** measured CPU work — decoding a large payload, downsampling an image, running inference. Back to chapter 1: this is the *real work* tool, not the *waiting* tool. Networking already suspends, and suspending doesn't occupy the actor, so moving I/O off buys nothing and costs two hops.

Apple's instruction is to profile first: *"If it can't be made faster [without concurrency], you might need to introduce concurrency."* Not speculatively.

> **In the office.** Deliberately sending a job to the back office rather than doing it at your own desk. Right for a long stocktake. A straight loss for adding up four numbers, because the two handovers cost more than the sum did.
