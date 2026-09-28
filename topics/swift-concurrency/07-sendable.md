---
title: Sendable
summary: What is allowed to cross a boundary — and the two separate jobs the one keyword does.
minutes: 6
sources:
- SE-0302 · Sendable and @Sendable closures | https://github.com/swiftlang/swift-evolution/blob/main/proposals/0302-concurrent-value-and-concurrent-closures.md
- SE-0414 · Region based Isolation | https://github.com/swiftlang/swift-evolution/blob/main/proposals/0414-region-based-isolation.md
- SE-0430 · sending parameter and result values | https://github.com/swiftlang/swift-evolution/blob/main/proposals/0430-transferring-parameters-and-results.md
- WWDC25 · Embracing Swift concurrency | https://developer.apple.com/videos/play/wwdc2025/268/
---

Once there are domains, things have to move between them — and not everything can safely move.

## The whole idea in one question

When I hand this to somewhere else, **do they get their own copy, or do we both end up holding the same thing?**

Own copy → nothing can go wrong → `Sendable`.
Same thing → we can both change it at once → not `Sendable`.

That maps almost exactly onto value types versus reference types.

> **In the office.** What may go across the counter. A photocopy is fine — you each end up with your own, and neither can spoil the other's. A key to a room you also hold a key to is not fine: you have handed the problem straight through the wall, and the counter did nothing for you.

## The four cases

**Value types — free.**

```swift
struct Money {                    // implicitly Sendable, no annotation
    let amount: Decimal
    var currency: String          // `var` is fine — each holder has its own copy
}
```

**Immutable final class — declare it, the compiler verifies.**

```swift
final class Config: Sendable {
    let apiKey: String            // every stored property must be `let`
    let timeout: TimeInterval     // and every type must itself be Sendable
}
```

Swift infers `Sendable` for structs and enums, never for classes. You state it; it checks you.

**Mutable class — refused.**

```swift
final class Counter: Sendable {   // error: stored property 'value' is mutable
    var value = 0
}
```

Refused because the property *can* be mutated, not because anything does. `let` versus `var` only matters for classes; for a struct it is irrelevant, because copying already solved the problem.

**Protection the compiler can't see — `@unchecked`.**

```swift
final class ImageStore: @unchecked Sendable {
    private let lock = NSLock()
    private var images: [URL: Data] = [:]

    func image(for url: URL) -> Data? {
        lock.lock(); defer { lock.unlock() }
        return images[url]
    }
}
```

A promise, not a proof. The obvious follow-up is *how do you know?*, and the only honest answers are "there is a lock", "it is immutable in practice", or "one task drives it, and here is where that is written down."

## The trap that catches everyone

A container is only as safe as its contents.

```swift
struct UserProfile: Sendable {    // error — and it points at `avatar`
    let name: String
    let avatar: ImageBuffer       // a non-Sendable class
}
```

It is a struct, everything is `let`, and it still fails. Copying the struct copies the *reference* to the buffer, not the buffer. You handed over a key and called it a photocopy.

## Two jobs, one keyword

This is the distinction that separates people who understand `Sendable` from people who have memorised it.

| Job | Checked | Rescued by region isolation? |
|---|---|---|
| A value crossing a boundary at a call site | by dataflow | **Yes** — a *disconnected* value can cross without conforming |
| A conformance requirement (`protocol P: Sendable`, a `Sendable` struct's properties) | on the declaration | **No** — there is no dataflow to analyse |

That is why removing `& Sendable` from a return type sometimes compiles and removing `: Sendable` from a protocol never does.

> **Under the hood.** **SE-0414 (region-based isolation)** lets the compiler track which values can reach which others and prove a value is *disconnected* — nothing outside this region can still reach it. A disconnected non-`Sendable` value can safely cross, because after the transfer the sender provably cannot touch it.
>
> **SE-0430 (`sending`)** carries that fact across a function signature. Region analysis is intraprocedural: at a call site the compiler knows only the *signature*, not the callee's body. So a function returning a bare non-`Sendable` value is assumed to be handing back something possibly still in its own region, and the transfer is rejected. `-> sending T` is the callee promising the result is disconnected, verified inside the callee.
>
> Choosing between them: a `Sendable` bound when the type genuinely is safe to share — checked once, at the type. `sending` when the type isn't `Sendable` but this particular value is exclusively owned — checked at every implementation of the signature, which is a larger maintenance surface.

## Why it goes on a protocol

`Sendable` is transitive. Anything *storing* an `any HTTPClientType` needs that type to be `Sendable` in order to be `Sendable` itself. Leave it off the contract and every holder becomes non-`Sendable`, and it spreads outward through the app.

You cannot add it cheaply later, which is why it belongs on the job description written at the start rather than on any particular implementation.

## The bit most people miss

**`Sendable` is only ever checked at a crossing.**

A mutable class used entirely within one domain never needs it. It is not a verdict on whether a type is well written — it is a question asked at a specific boundary, about a specific value, at a specific moment.

Which is why *"why does this need to be `Sendable`?"* has the answer **"because it crosses here — and if I move that line, it doesn't."**
