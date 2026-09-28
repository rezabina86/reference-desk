---
title: Retain cycles
summary: The five shapes a cycle actually takes in an iOS app, how to spot each, and why "make it a tree" beats sprinkling weak.
minutes: 8
sources:
- Apple · Automatic Reference Counting (TSPL) | https://docs.swift.org/swift-book/documentation/the-swift-programming-language/automaticreferencecounting/
- WWDC21 · ARC in Swift&#58; Basics and beyond | https://developer.apple.com/videos/play/wwdc2021/10216/
- WWDC24 · Analyze heap memory | https://developer.apple.com/videos/play/wwdc2024/10173/
---

A **retain cycle** is a loop of strong references. Every object in the loop is kept alive by another object in the loop, so no count in it ever reaches zero, and nothing outside can reach any of them. It is the one failure ARC cannot fix for you, and in practice it arrives in about five recognisable shapes.

> **In the library.** Two books, each holding the other's only loan card. Neither tally reaches zero, so neither is ever pulped, and no reader can find either of them. The shelf space is gone for the lifetime of the building.

## Shape 1 — two objects that own each other

The textbook one from chapter 3: `Parent` holds `Child` strongly, `Child` holds `Parent` strongly. Usually it enters a codebase as "the child needs to call back up".

The fix is to decide which direction is ownership. Almost always the parent owns the child, and the back-pointer becomes `weak` — or `unowned` if the child genuinely cannot outlive the parent.

```swift
final class Parent { var child: Child? }
final class Child  { weak var parent: Parent? }
```

## Shape 2 — the delegate

The same thing wearing a suit. A view controller creates a loader and makes itself the loader's delegate; the loader holds the delegate strongly; neither is ever released.

```swift
final class ImageLoader {
    weak var delegate: ImageLoaderDelegate?     // the fix, and the convention
}
```

This is why "delegates are weak" is a rule of thumb in Cocoa. Two riders worth knowing: the protocol must be class-bound (`protocol ImageLoaderDelegate: AnyObject`) for `weak` to be allowed at all, and the rule is not universal — a delegate that isn't the owner, like a data source living in a separate object graph, may legitimately be strong. Convention over reasoning is how the "safe" version of this becomes the silent-failure version from chapter 4.

## Shape 3 — a closure stored on the object it captures

The most common cycle in modern Swift by a distance, because closures are objects too. A closure stored in a property is on the heap and holds strong references to everything it captured — including `self`, if `self` is mentioned.

```swift
final class SearchBox {
    var onChange: ((String) -> Void)?

    func configure() {
        onChange = { text in
            self.results = self.filter(text)     // self retained by the closure,
        }                                        // closure retained by self
    }
}
```

The loop is `self → onChange → self`. Swift makes you write `self.` explicitly inside escaping closures precisely so this is visible at the call site — that requirement is a warning sign, not a syntax tax. Chapter 6 is the whole mechanism and the capture-list fix.

## Shape 4 — the timer, the observer, the subscription

Anything long-lived that you hand a block to, and that holds the block until you tell it to stop.

```swift
timer = Timer.scheduledTimer(withTimeInterval: 1, repeats: true) { _ in
    self.tick()                                  // the run loop holds the timer,
}                                                // the timer holds this block,
                                                 // the block holds self
```

Notice the loop doesn't run through your own properties this time: `self → timer → block → self`, with the run loop keeping the timer alive independently. A repeating `Timer` retains its target or block until it is invalidated, so the object never dies, so nothing ever calls `invalidate()`. The same shape appears with `NotificationCenter`'s block-based observer, with a Combine `AnyCancellable` stored on the object whose `sink` mentions `self`, and with any `addObserver` that returns a token you're supposed to hold.

Two fixes, and you often want both: capture `self` weakly in the block, and give the object an explicit teardown point that invalidates or cancels. Relying on `deinit` to do the cancelling can't work when the cycle is what's preventing `deinit`.

## Shape 5 — the cache, the registry, the singleton

Not a cycle at all, and it deserves to be in this list because it produces the identical symptom: a screen that never goes away.

```swift
ScreenRegistry.shared.register(self)     // nothing ever unregisters
```

A global dictionary, an array of "recent" view models, a coordinator that appends every child and never removes one. Reference counting is working perfectly; something really is still holding the object. WWDC24 calls this **abandoned memory** and separates it from leaked memory for exactly this reason: a leak is unreachable, this is reachable and simply unwanted.

The fix is never `weak` sprinkled on a property. It's an eviction policy: a bound, an unregister call, `NSCache`, or a lifetime tied to something that actually ends.

> **In the library.** Shape 5 is the shelf of books that are all correctly catalogued and were last opened in 2019. Nothing is broken. The building is still full.

## How you actually find one

In order of how often it works:

**Print in `deinit`, close the screen, watch for nothing.** Crude and unreasonably effective. If it doesn't print, something is holding it.

**Xcode's Memory Graph Debugger.** Run, reach the suspect state, dismiss the screen, press the memory-graph button, and search for the type. If an instance is still there, the graph shows you every strong reference pointing at it — including `closure context` nodes, which is how a shape-3 cycle names itself. Purple badges mark what Xcode believes is leaked.

**Instruments, when it's not one object but a pattern.** Chapter 9.

The question to ask the graph is not "is it leaked" but **"who is still pointing at this, and should they be?"** Half the time the answer is shape 5 and there's no cycle to break at all.

## The better fix: change the shape

`weak` and `unowned` break cycles. They don't prevent them, and a graph held together by a dozen weak back-pointers is hard to reason about — every one is a place where the object may have vanished and the code silently does nothing.

WWDC21's advice is worth taking literally: prefer transforming cyclic class relationships into **tree** structures. One direction owns, the other direction is either absent or a non-owning callback. Two specific moves do most of the work:

**Pass it in instead of storing it.** If the child needs the parent only while a method runs, take it as a parameter. A parameter creates no cycle because it doesn't outlive the call.

**Send values, not references.** Replace "child holds a pointer back to the parent so it can tell it things" with "child hands out a value and the parent decides what to do" — a closure that captures the *store* rather than the view controller, or an `AsyncStream` the parent reads. The pointer that closed the loop stops existing.

And the structural version of the same advice: **a struct cannot be in a retain cycle**, because nothing points at it. Chapter 7 is what that does and doesn't buy you.
