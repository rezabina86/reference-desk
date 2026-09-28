---
title: How ARC actually works
summary: Where the count lives, who inserts the retains, and why an object can die before the end of its scope.
minutes: 8
sources:
- WWDC21 · ARC in Swift&#58; Basics and beyond | https://developer.apple.com/videos/play/wwdc2021/10216/
- Swift · RefCount.h (runtime source) | https://github.com/swiftlang/swift/blob/main/stdlib/public/SwiftShims/swift/shims/RefCount.h
- Apple · Automatic Reference Counting (TSPL) | https://docs.swift.org/swift-book/documentation/the-swift-programming-language/automaticreferencecounting/
---

## The whole model in four lines

Every class instance carries a number: how many strong references currently point at it.

- Creating it sets the number to one.
- Storing another strong reference to it adds one — a **retain**.
- A strong reference going away subtracts one — a **release**.
- At zero, `deinit` runs and the memory is handed back.

That is the entire mechanism. Everything else in this topic is either a consequence of it or a way of stepping outside it.

```swift
final class Document {
    let name: String
    init(name: String) { self.name = name }
    deinit { print("\(name) gone") }
}

var a: Document? = Document(name: "Invoice")   // count 1
var b = a                                      // count 2
a = nil                                        // count 1 — nothing printed
b = nil                                        // count 0 — "Invoice gone"
```

Note what the second line does *not* do: it doesn't copy the document. Both variables hold the address of one object. That's what "reference type" means, and it's why the count is needed at all — a `struct` assignment would have made a second, independent value and none of this would apply.

> **In the library.** One book, one tally slip. Two readers each add a mark. The first one leaves and rubs out their mark; the book stays, because the slip isn't at zero. When the second leaves, the slip hits zero and the book is pulped — the shelf space goes back to the building immediately, not at closing time.

## Who writes the retains

You never see them, and they are not magic: the Swift compiler inserts calls to `swift_retain` and `swift_release` into your code while it compiles, following ownership rules built into the language. After optimisation, the ones it can prove are unnecessary are removed. What ships is ordinary machine code with some counting in it.

This has a consequence people find surprising the first time.

**An object's guaranteed lifetime runs from initialisation to its last use — not to the end of its scope.** Swift is use-based, unlike C++, which is scope-based. Once the compiler can see you will never touch a reference again, it is free to release it there, even if the variable is still nominally in scope for another forty lines.

```swift
func process() {
    let doc = Document(name: "Invoice")
    upload(doc)
    // doc is never used again — it may be released HERE
    doSomethingSlow()
}                                   // ...not necessarily here
```

So `deinit` can run earlier than you expect, while the enclosing function is still running. That is correct behaviour, not a bug.

The other half of the warning matters more. Observed lifetimes can also be **longer** than the guarantee: with optimisation off, or with a value held in a register, an object may survive well past its last use. WWDC21 is blunt about this — observed object lifetimes are an emergent property of the compiler and can change as implementation details change. So code that works because an object happens to still be alive is code that works by coincidence.

When you genuinely need an object kept alive across a stretch of code that doesn't mention it, say so explicitly with `withExtendedLifetime(_:)` rather than relying on what the optimiser did last Tuesday. The better fix, where it's available, is to restructure so the thing you depend on is reachable through a strong reference you actually hold.

> **In the library.** You put a book back on the returns trolley the moment you stop reading it, not when you leave the building. If you need it to stay findable while you nip out for coffee, you have to say so — keeping your hand on it is not the same as it being on loan to you.

## What the count is made of

The number isn't one number. From the Swift runtime's own header:

> An object conceptually has three refcounts… The strong RC counts strong references to the object. The unowned RC counts unowned references… The weak RC counts weak references.

The strong count is the one from the four lines above: at zero, `deinit` runs. The other two exist because the object's *storage* can't be freed at the same moment its *contents* are destroyed if somebody still holds a non-owning reference to it — they need something valid to find. Chapter 4 is that mechanism in full.

The counts are stored inline in the object's header, in the machine word after the type pointer. An extra **side table** — a small separate allocation — appears only when it has to, and forming the first `weak` reference is what triggers it. Gaining one is a one-way operation; an object that has a side table never loses it.

Two practical consequences fall out of that layout:

- A class instance is never just its properties. It carries a header — type pointer plus refcount word — so a class wrapping a single `Int` costs substantially more than an `Int`.
- Some objects are marked **immortal** and skip counting entirely: string literals and certain static values. Retaining one is a no-op, and its count never reaches zero because it never started.

> **Under the hood.** The lifecycle in `RefCount.h` has six states — `LIVE`, `DEINITING`, `DEINITED`, `FREED`, `DEAD`, each with and without a side table — and they exist to answer one question: what should a `weak` or `unowned` read do at each moment between "the last owner let go" and "the memory is gone"? The bits live in an `atomic<InlineRefCountBits>`, which is why chapter 8's claim about thread safety is a fact about the layout rather than a promise about your code.

## deinit

`deinit` runs when the strong count hits zero, before the memory is released. It is the last thing the object does.

```swift
final class Connection {
    private let handle: FileHandle
    deinit { try? handle.close() }
}
```

Three rules worth holding onto.

**It is deterministic, and that's the point.** This is what ARC buys that a tracing collector doesn't: the file closes when the last owner lets go, not eventually.

**It can run on any thread.** Whoever released last runs it — which may well be a background thread, and which is the source of a genuinely nasty crash class when a `deinit` touches UIKit. Chapter 8 deals with this, including Swift 6's `isolated deinit`.

**You cannot resurrect the object.** By the time `deinit` runs, the object is already dying: any `unowned` read of it traps, and any `weak` reference to it already reads as `nil`. Handing `self` to something in `deinit` is not a thing that works.

The print-in-deinit trick is still the fastest way to answer "did this screen actually go away?", and it is how most retain cycles get found in practice — you close the screen, and nothing prints.

## Why none of this catches a cycle

Look at the four lines again. Every rule is **local**: each object knows only how many references point at it. No part of the system knows the shape of the whole graph, so nothing is in a position to notice that two objects are holding each other up.

```swift
final class Parent { var child: Child? }
final class Child  { var parent: Parent? }      // both strong

var p: Parent? = Parent()
var c: Child? = Child()
p?.child = c                                    // Child count 2
c?.parent = p                                   // Parent count 2
p = nil; c = nil                                // both counts 1 — neither dies
```

Nothing in that program is unreachable in the counting sense, and nothing is reachable in the useful sense. Both objects are leaked, permanently, and no diagnostic fires. Chapters 4 to 6 are about the three keywords that prevent this, and the shapes in which it actually shows up.
