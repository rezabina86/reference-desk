---
title: 04 · The converter that shows the wrong answer
summary: A currency-converter view model built on async/await — review it, then explain why the compiler can't save you here.
minutes: 20
group: Review this PR
sources:
- Glassdoor · DoorDash iOS — debug a threading error in a sample project | https://www.glassdoor.com/Interview/DoorDash-IOS-Developer-Interview-Questions-EI_IE813073.0,8_KO9,22.htm
- Swift.org · Migrating to Swift 6 — data-race safety | https://www.swift.org/migration/documentation/migrationguide/
---

*Shape: review this PR · Reported: threading bugs as a review task (DoorDash); async/await is
the house style at most modern iOS teams · Compiled in Swift 6 mode: Swift 6.2 rejected the snippet, Swift 6.4
accepts it with one warning; the fix compiles on both and was run against a fake API*

> "The user types an amount and we show the converted value. QA says that if you type fast, the
> number on screen is sometimes for an amount you typed earlier — and after a network error the
> spinner never stops."

```swift
protocol RatesAPI { func rate(for currency: String) async throws -> Decimal }

final class ConverterViewModel {
    var result: String = ""
    var isLoading = false
    let api: RatesAPI

    init(api: RatesAPI) { self.api = api }

    func amountChanged(_ amount: Decimal, currency: String) {
        Task {
            isLoading = true
            let rate = try await api.rate(for: currency)
            result = "\(amount * rate)"
            isLoading = false
        }
    }
}
```

::: A hint, if you're stuck
- Type "1", "12", "125" quickly. How many requests are in flight, and whose answer lands last?
- If `api.rate` throws, which lines inside the `Task` never run?
- Which thread or actor sets `result` and `isLoading`, and who reads them?
:::

::: The key
1. **Stale result (QA's first bug).** Every keystroke starts a new `Task` and none is cancelled.
   Responses can arrive in any order; whichever finishes last wins, even if it's for an amount the
   user typed three keystrokes ago.
2. **Spinner never stops (QA's second bug).** `Task`'s closure is throwing, so `try` failing just
   ends the task — the error is silently dropped and `isLoading = false` never runs.
3. **No error state at all.** The UI can't tell "loading" from "failed".
4. **Not main-actor isolated.** `result` and `isLoading` drive UI but are mutated from whatever
   executor the task runs on. Don't rely on the compiler to say so: Swift 6.2 rejected this
   exact code (*passing closure as a 'sending' parameter risks causing data races*), but Swift 6.4
   accepts it in Swift 6 mode — both verified. 6.4's only warning is that the throwing task's
   result is unused, which is point 2, not this one. Swift 5 mode is silent.
5. **One request per keystroke.** Typing "1250" makes four network calls. Debounce.
6. **Money formatted with string interpolation.** `"\(amount * rate)"` gives "1375.0000" with no
   currency or locale. Use currency formatting.
7. **Two booleans-and-strings for state** — `isLoading` and `result` can contradict each other.
   An enum makes impossible states unrepresentable.
8. **Public mutable state.** The view can write `result`. Make it `private(set)`.
9. **`RatesAPI` isn't `Sendable`**, so it can't safely cross into the task under Swift 6.
:::

::: The idea behind it
A `Task` is a piece of async work that runs on its own. Start one per keystroke without stopping
the old ones and several answers race back; whichever arrives last wins, even if it's for an amount
the user has already changed.

The cure is *cancellation*: keep a handle to the current task and cancel it before starting the
next one. Cancellation in Swift is *cooperative* — it doesn't kill the task. It raises a flag that
well-behaved code checks (`Task.isCancelled`) before doing anything visible. That's why the fix
checks the flag before writing any state.

An error thrown inside a `Task` doesn't crash and doesn't show up anywhere. It just ends the task
quietly. So a "loading" flag set before the `try` is never cleared, and the spinner spins forever.

Finally, anything the UI shows must be changed on the main thread. Marking the view model
`@MainActor` makes the compiler guarantee it. Without it, nothing promises where `result` and
`isLoading` are changed — and as point 4 shows, whether the compiler complains depends on the Swift
version. The annotation is what turns "should be on main" into "is on main".
:::

::: The fix (compiles in Swift 6 mode, verified)
```swift
public protocol RatesAPI: Sendable {
    func rate(for currency: String) async throws -> Decimal
}

@MainActor
public final class ConverterViewModel {

    public enum State: Equatable {
        case idle
        case loading
        case loaded(String)
        case failed(String)
    }

    public private(set) var state: State = .idle
    private let api: RatesAPI
    private var current: Task<Void, Never>?

    public init(api: RatesAPI) { self.api = api }

    public func amountChanged(_ amount: Decimal, currency: String) {
        current?.cancel()
        state = .loading
        current = Task { [api] in
            do {
                try await Task.sleep(for: .milliseconds(300))          // debounce
                let rate = try await api.rate(for: currency)
                try Task.checkCancellation()
                state = .loaded((amount * rate).formatted(.currency(code: currency)))
            } catch {
                // A newer request replaced this one; it owns the state now. Check the task,
                // not the error type: URLSession reports cancellation as URLError(.cancelled).
                guard !Task.isCancelled else { return }
                state = .failed(error.localizedDescription)
            }
        }
    }
}
```

What the run against a fake API showed: a slow USD request overtaken by a fast GBP request ended
on `loaded("£85.00")` (last request wins); a failing API ended on `failed(…)` (spinner stops);
five fast keystrokes produced one network call and `loaded("US$5.50")` (debounce).

Why each piece:

- **`@MainActor` on the class** — every state change is on main by construction, and the `Task`
  created inside inherits it, so no `MainActor.run` hops.
- **Cancel the previous task** — that's the whole stale-result fix. The `Task.sleep` doubles as the
  debounce: a cancelled sleep throws immediately, so a superseded keystroke never reaches the API.
- **`checkCancellation()` after the network call** — a fake or a custom API might ignore
  cancellation and return normally; checking before writing state makes it unconditional.
- **`guard !Task.isCancelled` in the `catch`** — a cancelled task must not write `.failed`, or the
  user sees an error for a request they replaced. Don't use `catch is CancellationError` for this:
  a cancelled `URLSession` request throws `URLError(.cancelled)`, which would slip past it and
  overwrite the newer request's `.loading` with an error.
- **`[api]` capture** — copies the dependency into the task up front. It does *not* stop the task
  retaining the view model: writing `state` captures `self` anyway, which is fine here (see the
  first follow-up).
:::

::: What I'd ask next
- *"Why not `[weak self]` in that `Task`?"* — It still references `state`, so it captures `self`.
  That's fine: the task is short and cancelled by the next keystroke. Add `weak self` only if a
  task can run long after the screen is gone.
- *"In SwiftUI, where does this live?"* — `@Observable` model in `@State`; or drop `current` and
  use `.task(id: amount)`, which cancels and restarts automatically when the id changes.
- *"How would you test 'last request wins'?"* — A fake API with per-currency delays; trigger the
  slow one, then the fast one, await, assert the state. That's exactly how this fix was checked.
- *"What's actor reentrancy, and could it bite here?"* — State can change across any `await`. Here
  it's handled because nothing reads state after the `await` except the cancellation check.
:::
