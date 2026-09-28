---
title: The decision guide
summary: The ladder, the cheat sheet, the full map, and the questions to answer out loud.
minutes: 7
sources:
- WWDC21 · ARC in Swift&#58; Basics and beyond | https://developer.apple.com/videos/play/wwdc2021/10216/
- WWDC24 · Analyze heap memory | https://developer.apple.com/videos/play/wwdc2024/10173/
- Apple · Automatic Reference Counting (TSPL) | https://docs.swift.org/swift-book/documentation/the-swift-programming-language/automaticreferencecounting/
---

## The ladder

Not "manage memory". A sequence, and you stop as soon as the problem is solved.

**Step 0 — use a value type.** No identity, no sharing, no count, no cycle, no `deinit` to think about. Most model data, most state, most things passed between layers. The questions in this topic don't arise for a `struct` of `struct`s, which is the cheapest way to not have them.

**Step 1 — use a class, with strong references, when the thing has identity.** A cache, a session, a coordinator, a view model. Strong is the default and it is correct far more often than the internet implies. An object graph that is a tree of strong references has no memory problem at all.

**Step 2 — make the back-pointer non-owning when the tree needs a loop.** Decide the direction of ownership first, then spell the other direction. `weak` when the target's lifetime is independent of yours; `unowned` only when you can say in one sentence why this reference cannot outlive its target.

**Step 3 — bound anything that accumulates.** Caches, registries, arrays of children, dictionaries of in-flight tasks. A count limit, an eviction policy, an unregister call, or `NSCache`. This is the step people skip, and abandoned memory is more common in real apps than leaks.

**Step 4 — verify with the graph, once, per screen.** Push, pop, memory graph, filter for the type. Thirty seconds, at the moment you still remember what you captured.

**The error to avoid** is starting at step 2 — sprinkling `[weak self]` everywhere as a precaution. It converts a loud bug class (leaks, which tools find) into a quiet one (work that silently doesn't happen because `self` was `nil`), and it hides the fact that nobody decided who owns what.

## The reference cheat sheet

| Spelling | Keeps it alive? | After the object dies | Cost | Use when |
|---|---|---|---|---|
| `let` / `var` (strong) | yes | can't happen | a retain/release pair | you own it — the default |
| `weak var x: T?` | no | reads `nil` | side table + a runtime call per read | its lifetime is independent of yours |
| `unowned let x: T` | no | **traps** on read | cheapest non-owning read | it provably cannot outlive the target |
| `unowned(unsafe)` | no | undefined behaviour | free | interop, or a measured hot path |
| capture list `[weak self]` | no | `nil` inside the closure | as `weak` | the work is pointless if the object is gone |
| capture list `[self]` or plain `self.` | yes | can't happen | as strong | the work must finish regardless |
| non-escaping closure | n/a | n/a | none | it can't outlive the call — nothing to decide |

## The full map

| In the library | Real name | What it is | Where it lives |
|---|---|---|---|
| A book on a shelf | Object / class instance | a thing with identity, on the heap | the heap |
| The desk you carry to a chair | Stack frame | scratch space, cleared when the call returns | per thread |
| The shelves | Heap | shared storage that outlives a call | the process |
| The tally slip inside the cover | Strong reference count | how many owners it has | the object's header |
| A mark on the slip | Strong reference | an owner — while it exists, the book stays | compile-time inserted |
| Pulping at zero marks | `deinit` + deallocation | destruction, deterministic, immediate | runtime |
| A note at the front desk | `weak` reference | zeroed when the object dies | the side table |
| The desk's card index for one book | Side table | created by the first `weak` reference, never removed | the heap |
| A note in your pocket you swear is valid | `unowned` reference | no zeroing; a read after death halts | the object |
| A photocopy you take away | Value type | copied on assignment; no count, no identity | wherever its owner lives |
| Sharing one copy until someone writes | Copy-on-write | `isKnownUniquelyReferenced` on the buffer | the stdlib, in plain Swift |
| Two books holding each other's only card | Retain cycle | a loop of strong references | your design |
| A note pinned inside the book it mentions | Closure capturing `self`, stored on `self` | the same cycle, most common form | the heap |
| Correctly catalogued, unopened since 2019 | Abandoned memory | reachable and unwanted | your cache |
| Not in the catalogue, can't be removed | Leaked memory | unreachable and unfreeable | — |
| The returns trolley emptied at closing | Autorelease pool | ObjC objects released later, in a batch | Cocoa interop |
| The city closing the fullest branch | Jetsam | the OS terminating on memory pressure | the OS |
| A special pen two hands can't smudge | Atomic refcount | the count is thread-safe; the pages aren't | the object's header |

## The four sentences

**1. ARC counts owners; it does not trace the graph.** The rule is local, which is why destruction is immediate and why a cycle is invisible to it.

**2. Lifetime runs to the last use, not to the end of the scope.** And observed lifetimes are an emergent property of the optimiser, so code that depends on one works by coincidence.

**3. `weak` costs a side table and a runtime call; `unowned` costs a promise.** Break the promise and you get a deterministic halt, which is the cheap outcome compared with what the alternative would have handed you.

**4. The count is thread-safe; the object is not.** Reference counting decides lifetime, isolation decides access, and neither does the other's job.

## Answer these out loud

File closed, 90 seconds each, in trade-off shape — the decision, the alternative rejected, the boundary condition.

1. Why isn't ARC a garbage collector, and what does Swift get in exchange for that choice?
2. What exactly does a retain do, and where does the number live?
3. Why can an object be deallocated before the end of the function that created it?
4. What does forming the first `weak` reference to an object cost, permanently?
5. `weak` or `unowned` — give a rule that decides it, and an example where the other one would be a bug.
6. Why is reaching for `[weak self]` everywhere a bad default? What does it hide, and what new failure does it introduce?
7. Describe a retain cycle you have actually created. What was the loop, and how did you find it?
8. A view controller isn't deallocating. Walk through what you do, in order.
9. How does `Array` stay a value type without copying a million elements on assignment?
10. What does `isKnownUniquelyReferenced` check, and what would make it lie to you?
11. On which thread does `deinit` run, and why is that a problem worth a language feature?
12. A screen's memory climbs every time the user opens and closes it, and Instruments' Leaks finds nothing. What's your next move?
