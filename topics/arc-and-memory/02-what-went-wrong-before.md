---
title: What went wrong before
summary: Manual retain/release, garbage collection, and why Swift took neither — plus the one bill ARC leaves you to pay.
minutes: 6
sources:
- Apple · Transitioning to ARC Release Notes | https://developer.apple.com/library/archive/releasenotes/ObjectiveC/RN-TransitioningToARC/Introduction/Introduction.html
- Apple · Advanced Memory Management Programming Guide | https://developer.apple.com/library/archive/documentation/Cocoa/Conceptual/MemoryMgmt/Articles/MemoryMgmt.html
- Swift · RefCount.h (runtime source) | https://github.com/swiftlang/swift/blob/main/stdlib/public/SwiftShims/swift/shims/RefCount.h
---

ARC makes much more sense as a response to two specific failures than as a feature in its own right.

## Counting by hand

Objective-C's original model was reference counting done by the programmer. Every object carried a count. You called `retain` when you took an interest, `release` when you lost interest, and at zero the object was destroyed.

```objectivec
NSImage *image = [[NSImage alloc] initWithData:data];  // count 1
[cache setObject:image forKey:key];                    // cache retains — count 2
[image release];                                       // you're done — count 1
```

The rules were written down and they were learnable: you own what you `alloc`, `new`, `copy` or `retain`, and you must balance each one. What made it hard wasn't the rule, it was that the rule had to hold **across every path through every function, forever**, including the error paths nobody runs.

Miss a `release` and you leak. Add one too many and the object dies while somebody is still using it — chapter 1's use-after-free, reported as a crash in an unrelated place. An entire diagnostic tool, NSZombie, existed for nothing but this: keep dead objects around as tombstones so the crash at least names what you over-released.

> **In the library.** Every book has a tally slip in the front cover. You add a mark when you start reading, rub one out when you finish, and the book is pulped at zero. It works perfectly, right up until the day someone forgets to rub out a mark — or rubs out somebody else's.

## Garbage collection, and why not

The other mainstream answer: don't count anything. Periodically, the runtime pauses the program, walks outward from everything currently reachable, and reclaims whatever it didn't reach.

It is genuinely better in one respect, and that respect is the whole reason this chapter exists: **a tracing collector reclaims cycles**. Two objects pointing at each other are unreachable from the outside, so a walk from the roots never marks them, and they go. There is no such thing as a retain cycle in Java.

The costs are real, though, and they are the wrong costs for a phone.

**It needs slack.** A collector performs acceptably when it has considerably more memory than the program's live data — headroom is what buys the amortisation. On a device where the system kills the largest app when memory runs short, spare headroom is exactly what you don't have.

**Collection is not free, and not when you choose.** Even a good concurrent collector does work that competes with your app, at moments decided by allocation patterns rather than by you. A frame that must ship in under sixteen milliseconds does not want a visitor.

**Destruction is not deterministic.** With counting, an object dies at a knowable point and its `deinit` runs *then*. With tracing, it dies at some point after it became unreachable — maybe soon, maybe not. That matters for anything holding something scarce: a file handle, a socket, a camera, a lock.

Apple did ship a garbage collector for Objective-C on the Mac, and then retired it: it was deprecated with OS X Mountain Lion in 2012 and later removed, in favour of ARC. It never shipped on iOS at all.

> **In the library.** The alternative to tally slips is to close the building once a week, start from the front desk, and follow every reference anyone can actually reach. Whatever you never reached gets pulped. It finds the two books that only point at each other — and it closes the building.

## The third answer: let the compiler write it

Automatic Reference Counting keeps the counting model and removes the human from it. The compiler inserts the `retain` and `release` calls for you, at compile time, in the places the rules say they belong. It arrived for Objective-C in 2011 and it is the only model Swift has ever had.

Three things follow, and they're worth being able to say in order.

**It is not a garbage collector.** Nothing scans, nothing pauses, nothing runs periodically. The work is ordinary instructions in your own code — inserted for you rather than typed by you.

**Destruction is deterministic.** The last release destroys the object right there, so `deinit` runs at a point you can reason about, and memory comes back immediately. That's what makes footprint on iOS controllable.

**It cannot reclaim a cycle.** Counting is a local rule: each object knows how many references point *at* it, and nothing knows the global shape of the graph. Two objects that hold each other keep each other's count above zero, and nothing will ever come along and notice.

That is the bill ARC leaves you. Tracing collectors fix cycles automatically and pay with pauses and headroom; ARC gives you determinism and low footprint and hands you cycles as a design problem. **Everything people call "a memory bug in Swift" is almost always the arrival of that bill.**

> **Under the hood.** Swift's runtime keeps the count in the object's header, next to its type pointer — literally part of the object. The header comments in `RefCount.h` open with *"An object conceptually has three refcounts"*; chapter 4 uses all three. There is no separate table, no collector thread, no mark phase. Reference counting in Swift is not a subsystem; it is a field and some arithmetic.

## What ARC did not fix

Being clear about this saves a lot of confusion later.

It did not make memory management free — it made it *automatic and local*. Every `retain` is still an atomic increment on a shared counter, and chapter 8 is about what that costs when several threads are involved.

It did not remove the need to think about ownership. It removed the need to *implement* it. You still have to decide which object owns which, and the rest of this topic is really about that decision, expressed in three keywords: `strong`, `weak`, `unowned`.
