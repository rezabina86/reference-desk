---
title: Value types and copy-on-write
summary: Why a struct sidesteps the whole problem, the trap of a struct holding a class, and how Array avoids copying everything.
minutes: 8
sources:
- Swift · isKnownUniquelyReferenced (stdlib source) | https://github.com/swiftlang/swift/blob/main/stdlib/public/core/ManagedBuffer.swift
- WWDC21 · ARC in Swift&#58; Basics and beyond | https://developer.apple.com/videos/play/wwdc2021/10216/
- Apple · Structures and Classes (TSPL) | https://docs.swift.org/swift-book/documentation/the-swift-programming-language/classesandstructures/
---

Everything so far has been about reference types, because they're the only things that need managing. This chapter is the other half of the advice WWDC21 gives after all its ARC material: prefer value types to avoid the dangers of unintended sharing.

## Why a struct has no memory question

Assigning a struct copies it. Two variables, two independent values, no sharing.

```swift
struct Point { var x: Double; var y: Double }

var a = Point(x: 0, y: 0)
var b = a          // a copy — a genuinely separate value
b.x = 10           // a.x is still 0
```

Because nothing points at it, a struct cannot be in a retain cycle, cannot be shared across threads by accident, and doesn't need a count. Its lifetime is its owner's: a local struct dies when the function returns, and one stored in a class dies with the class. There is no decision to make, and no `deinit` to reason about — value types don't have one.

This is why a codebase built mostly from values simply has fewer memory bugs. Not because anybody was careful: because most of the questions never come up.

> **In the library.** A value type is a photocopy you take away with you. Nothing is shared, nobody has to be told when you're done, and there's no tally slip — when you throw your copy away, that's the end of it.

## The trap: a struct that holds a class

A struct is only a value in the sense that *its own storage* is copied. Copying it copies whatever is inside it — and if one of its properties is a class reference, the copy is of the reference, not of the object.

```swift
final class Buffer { var bytes: [UInt8] = [] }

struct Document {
    var title: String       // genuinely copied
    var buffer: Buffer      // the reference is copied; both share one Buffer
}

var one = Document(title: "A", buffer: Buffer())
var two = one
two.buffer.bytes = [1, 2, 3]
// one.buffer.bytes is now [1, 2, 3] as well
```

`two` looks like an independent value and half of it is. This is the most common "but I used a struct" surprise, and the reason `Sendable` checking for structs looks at every stored property rather than stopping at the keyword `struct`. A struct is `Sendable` only if everything inside it is, and the `Buffer` above is precisely what stops it.

Two ways out. Make the inner type a value type as well, which is usually the right answer. Or keep the class deliberately — and then either make it immutable, or implement copy-on-write so that the sharing is invisible. Which is what the standard library does.

## How Array can afford to be a value type

`Array`, `String`, `Dictionary` and `Set` all behave like values, yet copying one doesn't copy its contents:

```swift
let million = Array(0..<1_000_000)
let alsoMillion = million       // no million-element copy happens here
```

Both now refer to one buffer. The copy is deferred until somebody writes, and only then, and only if the buffer is shared. That is **copy-on-write**, and it is implemented in ordinary Swift on top of exactly the reference counting from chapter 3.

The mechanism is one question: *am I the only owner of this buffer?* The standard library asks it with `isKnownUniquelyReferenced(_:)`, which returns true when the object's strong count is one.

```swift
struct Bytes {
    private var storage: Buffer      // a class, holding the actual memory

    mutating func append(_ byte: UInt8) {
        if !isKnownUniquelyReferenced(&storage) {
            storage = storage.copy()     // somebody else is looking — copy first
        }
        storage.bytes.append(byte)       // now it's ours alone; mutate in place
    }
}
```

Read that with chapter 3's counting in mind and the whole design falls out. Copying the struct retains the buffer, so the count goes to two; the next mutation sees a count above one and forks. If the other copy has since gone away, the count is back to one and the mutation is in place, for free. Value semantics at the surface, one allocation underneath, and the reference count is the entire coordination mechanism.

> **In the library.** The library doesn't photocopy a 400-page report for every reader — everyone shares the one copy while they're only *reading*. The moment somebody wants to write in the margins, the desk checks whether anyone else has it out. If yes, they get a photocopy to scribble on. If not, they scribble on the original.

## Two things to know before you implement it

**The `&&` ordering gotcha**, straight from the standard library's own documentation. In a debug build, an instance on the left of a `&&` may still be referenced while the right-hand side is evaluated, inflating the count — so this version copies on *every* call:

```swift
// copies too frequently
if storage.shouldCopy || !isKnownUniquelyReferenced(&storage) { … }
```

Put the uniqueness check first, or compute the other condition into a local first. A performance bug that only exists in debug builds is a memorable one to have been bitten by.

**It checks strong references only.** Weak and unowned references to the buffer don't make it non-unique, and passing a weak reference always returns `false`. And uniqueness is meaningless without synchronisation: if two threads can reach the same struct, the check can say "unique" while another thread is mid-copy. The documentation's wording is that you must only call it from mutating methods with appropriate thread synchronisation — which for a value type usually means the value isn't shared across threads in the first place, and if it is, you have a data race, not a CoW problem.

## When to reach for this

Almost never directly. Use `Array` and `Dictionary`, which do it for you.

The cases where you write it yourself are specific: a value type wrapping a large buffer that gets copied often and mutated rarely (image data, a big matrix, a parsed document), or a value type wrapping something expensive to duplicate, like a `CGContext` or a database handle. Outside those, a struct holding value properties is simpler and faster, because there's no allocation to share in the first place.

The reverse also matters: **not everything should be a struct.** A type with genuine identity — a network session, a cache, a coordinator, anything where "the same one" means something — is a class, and making it a struct produces its own confusing bugs. The question is identity, not performance. When two instances with identical contents should be interchangeable, that's a value. When they shouldn't, that's an object.

## Where this leaves the topic

Values sidestep ownership; references need it decided. Most application code can be mostly values with a thin layer of long-lived objects — the caches, the coordinators, the sessions — and that thin layer is where all the material from chapters 4 to 6 applies.

Next: what happens to any of this when more than one thread is involved. The short version is that the counting is safe and the object isn't, and the difference is where several genuinely nasty crashes live.
