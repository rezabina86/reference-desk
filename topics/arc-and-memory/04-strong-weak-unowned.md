---
title: Strong, weak, unowned
summary: The three kinds of reference, what each costs at runtime, and the rule for picking one.
minutes: 9
sources:
- Apple · Automatic Reference Counting (TSPL) | https://docs.swift.org/swift-book/documentation/the-swift-programming-language/automaticreferencecounting/
- Swift · RefCount.h (runtime source) | https://github.com/swiftlang/swift/blob/main/stdlib/public/SwiftShims/swift/shims/RefCount.h
- WWDC21 · ARC in Swift&#58; Basics and beyond | https://developer.apple.com/videos/play/wwdc2021/10216/
---

A reference either keeps the thing it points at alive, or it doesn't. Swift gives you one way to do the first and two ways to do the second, and the difference between those two is the only genuinely subtle part.

## Strong

The default. No keyword — a plain `var` or `let` property holding a class instance is strong. It contributes to the count, and while it exists the object cannot die.

Use it for everything you own. A view model owns its repository; a repository owns its client; a cache owns its entries. In a healthy object graph the overwhelming majority of references are strong, and reaching for `weak` by reflex is its own bug — see the end of chapter 5.

> **In the library.** A strong reference is a mark on the tally slip. While your mark is there, the book stays.

## Weak

A `weak` reference does not contribute to the strong count, and it becomes `nil` automatically when the object dies. It must therefore be an `Optional` `var` — it has to be able to become nothing, and it has to be mutable, because something other than you changes it.

```swift
final class ImageLoader {
    weak var delegate: ImageLoaderDelegate?
}
```

Two things happen at runtime, and knowing both is what separates a usable mental model from a slogan.

**Forming the first weak reference gives the object a side table.** That's a second small allocation, and the object keeps it for the rest of its life. Weak variables then point at the side table rather than at the object, which is exactly how the zeroing can work: when the object dies, the table outlives it briefly, and reads through it return `nil`.

**Reading a weak reference is not free.** It isn't a pointer dereference; it's a runtime call that must check the object's state and, if it's still alive, hand you a *strong* reference to it for the duration of your use — otherwise it could die between your check and your call. That's an atomic retain and release per read, plus synchronisation around the table. Fine anywhere normal. Not fine in a loop over ten thousand items, which is a real optimisation you will occasionally have to make:

```swift
// reads weak storage every iteration
for item in items { weakThing?.handle(item) }

// reads it once, then works with a strong reference
if let thing = weakThing {
    for item in items { thing.handle(item) }
}
```

That second form is also more correct, not just faster: in the first, `weakThing` can become `nil` half way through and you silently process half the list.

> **In the library.** A weak reference is a note at the front desk: *"tell me if this book is pulped."* It adds no mark to the tally, so it never keeps the book alive. When the book goes, the desk quietly crosses your note out — and the only way to find out whether it's still there is to walk to the desk and ask, every time.

## Unowned

`unowned` also contributes nothing to the strong count. The difference is what happens afterwards: **nothing is zeroed, and nothing checks for you at the moment of use**. The reference is non-optional and, by default, reading one after the object has died halts the program immediately — in the runtime's own words, unowned variable load *halts in `swift_abortRetainUnowned()`*.

So the model is: `unowned` is a promise you make to the compiler that this reference will never outlive its target. If the promise holds, you pay less — no side table, no optional to unwrap, a cheaper read. If it breaks, you crash deterministically rather than corrupting anything.

```swift
final class Customer {
    var card: CreditCard?
}

final class CreditCard {
    unowned let customer: Customer      // a card without a customer is nonsense
    init(customer: Customer) { self.customer = customer }
}
```

That is the legitimate shape: the card cannot possibly outlive the customer, because the customer is the only route to it. When you can state a reason like that in one sentence, `unowned` is right. When your sentence contains "shouldn't" or "in practice", use `weak`.

There is also `unowned(unsafe)`, which removes the check as well. It's the equivalent of Objective-C's `assign` — a raw pointer with no safety net at all, reading freed memory rather than trapping. It exists for interop and hot paths; if you're reaching for it to silence a crash, you've found a lifetime bug, not a performance problem.

> **In the library.** An unowned reference is a note in your own pocket saying *"book 412, I'm certain it's still on the shelf."* Nobody updates it. If you're right, it's the cheapest thing possible. If you're wrong, you walk to shelf 412 and the building stops you at the door — better than handing you whatever is now in that slot.

## Which one, and when

The question to ask is never "which is safer?" It's **can this reference outlive what it points at?**

| Situation | Use | Why |
|---|---|---|
| You own it — it should live as long as you do | `strong` | the default, and correct far more often than people assume |
| A back-pointer to something that owns you, with equal or longer life | `unowned` | provably can't outlive it; no optional, no side table |
| A back-pointer whose lifetime is independent of yours | `weak` | it can vanish, and you need to survive that |
| A delegate | `weak` | the delegate almost always owns you; classic cycle otherwise |
| A reference held across an `await`, a network call, or any callback | `weak` | the thing can die while you're suspended; see chapter 6 |
| Interop, or a measured hot path where you can prove the lifetime | `unowned(unsafe)` | no check at all — you are the check |

A useful second question when you're stuck: **if this object died right now, is my code still meaningful?** If yes, `weak` — write the `nil` path. If the answer is "that can't happen and the code would be nonsense", `unowned` is the honest spelling, and the crash is the enforcement of what you just said.

## The thing people get wrong

`weak` is not the safe default, and treating it that way causes its own class of bugs.

A `weak` reference tells the reader *this can disappear at any moment and I'm fine with that*. When it isn't true — when the object really should have been kept alive, and something else was supposed to be holding it — the symptom isn't a crash. It's a screen that silently stops updating, a callback that never fires, a save that never happens, because by the time the work finished, `self` was `nil` and the closure returned early. Nothing is logged. Nothing is reported. That is far harder to find than a leak.

Decide ownership first. Reach for `weak` when the answer to "who owns this?" is genuinely "somebody else", not as a way of avoiding the question.

> **Under the hood.** The three counts exist to make the middle of an object's death safe. When the strong count reaches zero the object is deinited and its weak references start reading `nil`, but the *storage* can't be freed while unowned references still exist — those have to find something valid to trap on. The unowned count keeps the allocation alive past `deinit`; the weak count keeps the side table alive past the allocation. `DEINITING`, `DEINITED`, `FREED`, `DEAD`: four states between "last owner let go" and "the space is reusable", and all of them are there so `weak` can be `nil` and `unowned` can trap instead of both reading rubbish.
