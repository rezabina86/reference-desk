---
title: Structured concurrency and cancellation
summary: Child tasks that cannot outlive their parent, and why cancellation is a flag rather than a kill.
minutes: 7
sources:
- SE-0304 · Structured concurrency | https://github.com/swiftlang/swift-evolution/blob/main/proposals/0304-structured-concurrency.md
- WWDC21 · Swift concurrency&#58; Behind the scenes | https://developer.apple.com/videos/play/wwdc2021/10254/
---

## Tasks that own other tasks

A job often needs several things at once. You can create child tasks, and the system's rule about them is the valuable part: **a parent cannot return before its children have finished.**

Sequential — three round trips, one after another:

```swift
let profile  = try await fetchProfile(id)
let settings = try await fetchSettings(id)
let badges   = try await fetchBadges(id)
```

Concurrent, a fixed number of known children:

```swift
async let profile  = fetchProfile(id)
async let settings = fetchSettings(id)
async let badges   = fetchBadges(id)

let screen = try await Screen(profile: profile, settings: settings, badges: badges)
```

Concurrent, a number decided at runtime:

```swift
func thumbnails(for urls: [URL]) async throws -> [URL: Image] {
    try await withThrowingTaskGroup(of: (URL, Image).self) { group in
        for url in urls {
            group.addTask { (url, try await self.thumbnail(for: url)) }
        }
        return try await group.reduce(into: [:]) { $0[$1.0] = $1.1 }
    }
}
```

**What the parent-waits rule buys you.** Under the old model you sent someone off to do a task and carried on — and if you finished first, or gave up, or the screen closed, that work was still out there. Nobody tracked it. It came back hours later with a result for a job that no longer existed, or held resources nothing could reclaim.

With structured concurrency that cannot happen. Children have a lifetime bounded by their parent's. Cancel the parent and every child is cancelled. If a child throws, the parent hears about it. Nothing is orphaned.

This is the quiet reason the new model produces less mess than the old one, quite apart from the data-race question.

> **In the office.** A job that needs three sub-jobs writes three more slips and hands them out — but is not allowed to leave for the day until all three come back. Nobody goes home leaving work outstanding that nobody is tracking.

## `Task { }` and the escape hatch

`Task { }` is *unstructured* — it outlives the scope that created it and nobody waits for it — but it **inherits the enclosing actor isolation, priority and task-local values**:

```swift
@MainActor
final class FeedViewModel {
    private(set) var items: [Item] = []

    func refresh() {
        Task {                                  // inherits @MainActor
            items = try await loader.load()     // no MainActor.run needed
        }
    }
}
```

`Task.detached { }` inherits **nothing** — no actor, no priority, no task-locals, and nothing cancels it. The number of legitimate uses in an app codebase is close to zero. Reaching for it because "this shouldn't block the UI" is the classic misuse; the tool for that is `@concurrent`, which keeps priority and cancellation.

## Cancellation is cooperative

You cannot kill a task mid-work. Cutting it off halfway would leave state half-written, which is worse than letting it finish.

So cancellation sets a **flag**. Something marks the task cancelled; the work notices *between steps* and stops.

```swift
func process(_ items: [Item]) async throws -> [Result] {
    var results: [Result] = []
    for item in items {
        try Task.checkCancellation()      // throws CancellationError
        results.append(expensiveWork(item))
    }
    return results
}
```

Two ways to observe it:

```swift
try Task.checkCancellation()   // throws — use in a throwing context
if Task.isCancelled { return } // boolean — use when returning partial work
```

In SwiftUI, `.task` cancels for you when the view disappears:

```swift
.task(id: query) {              // cancels the previous one when query changes
    await viewModel.search(query)
}
```

**The consequence, exactly:** work that never checks the flag never stops. A thirty-second loop with no check runs for its full thirty seconds after the user has left the screen, holding memory and burning battery, and no amount of `cancel()` at the call site changes that.

`cancel()` does not stop anything. It marks the task and every child as cancelled. Built-in suspension points — `Task.sleep`, `URLSession`'s async methods — throw when they notice. Your own CPU loops notice nothing unless you ask.

> **In the office.** You cannot snatch paperwork out of someone's hands mid-sentence. You stamp the slip *no longer needed*. The worker sees the stamp between steps, tidies up and stops. A worker who never looks up finishes the whole job regardless.

**The trap:** `try? await Task.sleep(...)` swallows the `CancellationError`, so execution continues into whatever came next. If you use `try?`, follow it with an explicit `guard !Task.isCancelled else { return }`.

**In a review, the question that separates people:** *where do you check for cancellation?* A long synchronous loop with no check is not cancellable, whatever the paperwork says.

## Bounding the width

A task group with a thousand `addTask` calls will happily start a thousand children. If each holds a decoded image you have a memory problem, not a concurrency one:

```swift
// keep at most `limit` in flight
for url in urls {
    if inFlight >= limit { _ = try await group.next(); inFlight -= 1 }
    group.addTask { /* … */ }; inFlight += 1
}
```

Structured concurrency bounds *lifetime*. It does not bound *width* — that is yours.
