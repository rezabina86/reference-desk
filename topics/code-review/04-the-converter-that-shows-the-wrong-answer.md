---
title: 04 · The converter that shows the wrong answer
summary: A currency-converter view model built on async/await — review it, then fix what QA reported.
minutes: 20
group: Review this PR
sources:
- Glassdoor · DoorDash iOS — debug a threading error in a sample project | https://www.glassdoor.com/Interview/DoorDash-IOS-Developer-Interview-Questions-EI_IE813073.0,8_KO9,22.htm
- Swift.org · Migrating to Swift 6 — data-race safety | https://www.swift.org/migration/documentation/migrationguide/
---

*Shape: review this PR · Reported: threading bugs as a review task (DoorDash); async/await is
the house style at most modern iOS teams · Verified: Swift 6 mode rejects the snippet, Swift 5
mode builds it with one warning; the fix's tests pass, Swift 6.4*

> "The user types an amount and we show the converted value. QA says that if you type fast, the
> number on screen is sometimes for an amount you typed earlier — and after a network error the
> spinner never stops. Review it."

```swift
protocol RatesAPI { func rate(for currency: String) async throws -> Decimal }

final class ConverterViewModel {
    var result: String = ""
    var isLoading = false
    var onChange: (() -> Void)?
    let api: RatesAPI

    init(api: RatesAPI) { self.api = api }

    func textChanged(_ text: String, currency: String) {
        let amount = Decimal(string: text)!
        amountChanged(amount, currency: currency)
    }

    func amountChanged(_ amount: Decimal, currency: String) {
        Task {
            isLoading = true
            onChange?()
            let rate = try await api.rate(for: currency)
            result = "\(amount * rate)"
            isLoading = false
            onChange?()
        }
    }
}
```

::: A hint, if you're stuck
- Type "1", "12", "125" quickly. How many requests are in flight, and whose answer lands last?
- If `api.rate` throws, which lines inside the `Task` never run?
- What does the text field contain after the user deletes everything?
- Which thread or actor sets `result` and `isLoading`, and who reads them?
:::

::: The key — what I expect a senior to find
QA's two bugs come first, because they were reported; the rest is by severity.

1. **Stale result (QA's first bug).** Every keystroke starts a new `Task` and none is cancelled.
   Answers can arrive in any order, and the last one to arrive wins — even for an amount the user
   typed three keystrokes ago. Keep the task and cancel it before starting the next.
2. **Spinner never stops (QA's second bug).** The task's closure can throw, so a failing `try`
   just ends the task. The error is dropped and `isLoading = false` never runs. Catch the error and
   clear the spinner on both paths.
3. **Crash on an empty field.** `Decimal(string: text)!` is `nil` when the user deletes everything
   or pastes "abc", and the force unwrap crashes. Parse with `guard let`, and clear the result.
4. **UI state changed off the main thread.** `result`, `isLoading` and `onChange` drive the UI,
   but nothing says where the task runs. Whether the compiler flags it depends on the Swift version
   and the target's default isolation (new Xcode 26 app targets default to the main actor) — don't
   rely on it. Annotate the class `@MainActor`.
5. **An old task hides the spinner early.** The first request finishes and sets
   `isLoading = false` while the newer one is still loading. Only the current task may touch the
   spinner.
6. **The user's locale is ignored.** `Decimal(string:)` only understands a dot. A German user
   types "12,5" and gets 12, silently. Parse with `Decimal(text, format: .number)`, which uses
   the user's locale.
7. **No error state.** The UI can't tell "loading" from "failed". Expose an error message.
8. **Money formatted with string interpolation.** `"\(amount * rate)"` prints the bare number —
   "1375" or "8.5673" — with no currency symbol, no grouping, no rounding to cents. Use
   `.formatted(.currency(code:))`.
9. **The spinner starts late.** `isLoading = true` is set inside the task, so the old number
   stays on screen for a moment with no spinner. Set it before starting the task.
10. **One request per keystroke.** Typing "1250" makes four network calls. Debounce.
11. **Everything is writable from outside.** The view can set `result`, and `api` is visible to
    every caller. Make the state `private(set)` and the `api` `private`.
12. **State that can contradict itself.** `isLoading`, `result` and an error can all be set at
    once. An enum (`idle`, `loading`, `loaded`, `failed`) makes impossible states impossible.
13. **`RatesAPI` isn't `Sendable`**, so it can't safely be used from a task in Swift 6. Mark the
    protocol `Sendable`.
14. **Currency is a plain `String`.** "usd", "USD" and "US$" all compile. A small `Currency` type
    (or `Locale.Currency`) catches that.
15. **`onChange` invites a retain cycle.** A view controller that writes
    `viewModel.onChange = { self.render() }` and owns the view model keeps both alive forever. Say
    `[weak self]` at the call site — or drop the closure for an `@Observable` model.
:::

::: The idea behind it
A `Task` is a piece of async work that runs on its own. Start one per keystroke without stopping
the old ones and several answers race back. Whichever arrives last wins, even if it's for an amount
the user has already changed.

The cure is *cancellation*: keep a handle to the current task and cancel it before starting the
next one. Cancellation in Swift is *cooperative* — it doesn't kill the task. It raises a flag that
well-behaved code checks (`Task.isCancelled`) before doing anything visible. That's why the fix
checks the flag before writing any state, on the success path and in the `catch`.

An error thrown inside a `Task` doesn't crash and doesn't show up anywhere. It just ends the task
quietly. So a "loading" flag set before the `try` is never cleared, and the spinner spins forever.

Finally, anything the UI shows must change on the main thread. Marking the view model `@MainActor`
makes the compiler guarantee it, and a `Task` created inside it runs on the main actor too. The
annotation is what turns "should be on main" into "is on main".
:::

::: The fix
```swift
protocol RatesAPI: Sendable { func rate(for currency: String) async throws -> Decimal }  // key 13

@MainActor                                                         // key 4
final class ConverterViewModel {
    private(set) var result: String = ""                           // key 11
    private(set) var isLoading = false
    private(set) var errorMessage: String?                         // key 7
    var onChange: (() -> Void)?
    private let api: RatesAPI
    private var task: Task<Void, Never>?                           // key 1

    init(api: RatesAPI) { self.api = api }

    func textChanged(_ text: String, currency: String) {
        guard let amount = try? Decimal(text, format: .number) else {   // key 3, 6
            task?.cancel(); result = ""; isLoading = false; onChange?()
            return
        }
        amountChanged(amount, currency: currency)
    }

    func amountChanged(_ amount: Decimal, currency: String) {
        task?.cancel()                                             // key 1
        isLoading = true; errorMessage = nil; onChange?()          // key 9
        task = Task {
            do {
                let rate = try await api.rate(for: currency)
                guard !Task.isCancelled else { return }            // key 1, 5
                result = (amount * rate).formatted(.currency(code: currency))  // key 8
            } catch {
                guard !Task.isCancelled else { return }            // key 5
                errorMessage = error.localizedDescription          // key 2, 7
            }
            isLoading = false                                      // key 2
            onChange?()
        }
    }
}
```

**Said out loud, not coded:** one `State` enum instead of three properties; a debounce
(`try await Task.sleep(for: .milliseconds(300))` at the top of the task — a cancelled sleep throws,
so a replaced keystroke never reaches the API — and a test would inject that sleep); a `Currency`
type; `@Observable` instead of `onChange`.

Why each piece:

- **The `Task` needs no hops to main.** It is created inside a `@MainActor` class, so it runs on
  the main actor; only the `await` leaves it.
- **Check `Task.isCancelled` after the `await`, even if the API respects cancellation.** A fake,
  or an API that ignores cancellation, still returns normally. Checking before writing makes the
  rule unconditional.
- **The same check in `catch`, not `catch is CancellationError`.** `URLSession` reports a
  cancelled request as `URLError(.cancelled)`. A type check would let it through, and the user would
  see an error for a request they replaced.
- **A cancelled task returns before `isLoading = false`.** The newer task owns the spinner now —
  that is key 5.
:::

::: Now write the tests
> "Good. Now write me the tests you'd want on this view model before it merges — one for each
> thing QA reported, and one for the crash."

**What I'd test, and why**

1. **Last request wins.** A slow USD answer arrives after a newer GBP one; the screen must show
   GBP. This is QA's first bug.
2. **A failure stops the spinner.** The API throws; `isLoading` must go back to `false` and the
   error must show. That's QA's second bug.
3. **A replaced request never writes its failure**, even when it ends with `URLError(.cancelled)`,
   the way `URLSession` ends a cancelled request. It's the subtle line in the fix, and the one
   someone will "simplify" to `catch is CancellationError`.
4. **An empty field clears the result instead of crashing** — the regression test for key 3.

I wouldn't test the currency formatting itself — that's Apple's code. I build the expected string
with the same `.formatted(.currency(code:))` call, so the test passes in any locale.

**The seam.** The API already comes in through `init`, so no new seam is needed. The test passes a
*fake*: a small stand-in that records each request and holds it open until the test answers it.
That way the test decides the order answers arrive in, and every run does the same thing.

```swift
import Foundation
import Testing

/// A fake API: it records each request and holds it until the test answers.
@MainActor
final class FakeRatesAPI: RatesAPI {
    private(set) var requests: [String] = []
    private var pending: [String: CheckedContinuation<Decimal, Error>] = [:]

    func rate(for currency: String) async throws -> Decimal {
        requests.append(currency)
        return try await withCheckedThrowingContinuation { pending[currency] = $0 }
    }

    func answer(_ currency: String, with rate: Decimal) {
        pending.removeValue(forKey: currency)?.resume(returning: rate)
    }

    func fail(_ currency: String, with error: Error) {
        pending.removeValue(forKey: currency)?.resume(throwing: error)
    }
}

/// Gives queued main-actor work a turn until `condition` holds. Bounded by a count, not a clock.
@MainActor
func waitUntil(maxYields: Int = 1_000, _ condition: () -> Bool) async {
    for _ in 0..<maxYields where !condition() { await Task.yield() }
}

@MainActor
struct ConverterViewModelTests {
    let api = FakeRatesAPI()

    @Test func lastRequestWins() async {
        // Given a USD request still waiting, replaced by a GBP request
        let viewModel = ConverterViewModel(api: api)
        viewModel.amountChanged(100, currency: "USD")
        viewModel.amountChanged(100, currency: "GBP")
        await waitUntil { api.requests.count == 2 }

        // When GBP answers first and the old USD answer arrives last
        api.answer("GBP", with: Decimal(string: "0.85")!)
        await waitUntil { !viewModel.isLoading }
        api.answer("USD", with: Decimal(string: "1.10")!)
        await waitUntil(maxYields: 100) { false }   // give the late answer its turns

        // Then the screen still shows GBP
        #expect(viewModel.result == Decimal(85).formatted(.currency(code: "GBP")))
    }

    @Test func failureStopsTheSpinner() async {
        let viewModel = ConverterViewModel(api: api)
        viewModel.amountChanged(10, currency: "USD")
        await waitUntil { api.requests.count == 1 }

        api.fail("USD", with: URLError(.notConnectedToInternet))
        await waitUntil { !viewModel.isLoading }

        #expect(viewModel.isLoading == false)
        #expect(viewModel.errorMessage == URLError(.notConnectedToInternet).localizedDescription)
    }

    @Test func replacedRequestNeverWritesTheFailure() async {
        // Given a USD request replaced by a GBP request
        let viewModel = ConverterViewModel(api: api)
        viewModel.amountChanged(10, currency: "USD")
        viewModel.amountChanged(10, currency: "GBP")
        await waitUntil { api.requests.count == 2 }

        // When the old one ends the way URLSession ends a cancelled request
        api.fail("USD", with: URLError(.cancelled))
        await waitUntil(maxYields: 100) { false }

        // Then no error shows, and the spinner stays for GBP
        #expect(viewModel.errorMessage == nil)
        #expect(viewModel.isLoading)
    }

    @Test func emptyFieldClearsTheResultInsteadOfCrashing() async {
        // Given a converted amount on screen
        let viewModel = ConverterViewModel(api: api)
        viewModel.textChanged("12", currency: "USD")
        await waitUntil { api.requests.count == 1 }
        api.answer("USD", with: 2)
        await waitUntil { !viewModel.isLoading }

        // When the user deletes the text
        viewModel.textChanged("", currency: "USD")

        // Then the result clears, and no new request starts
        #expect(viewModel.result == "")
        #expect(api.requests == ["USD"])
    }
}
```

`waitUntil` gives the view model's task turns on the main actor until the condition holds. It's
bounded by a count, not a time, so a slow machine can't make it flaky.

Ran with Swift 6.4: 4 tests, all passed.
:::

::: What I'd ask next
- *"Why not `[weak self]` in that `Task`?"* — It writes `result`, so it captures `self`. That's
  fine: the task is short and the next keystroke cancels it. Add `weak self` only if a task can
  run long after the screen is gone.
- *"Add the debounce. How do you test it without waiting 300 ms?"* — Sleep at the top of the
  task, and pass the sleep in through `init` with `Task.sleep` as the default. The test passes one
  that returns at once but still throws when cancelled; five keystrokes, one request.
- *"In SwiftUI, where does this live?"* — An `@Observable` model in `@State`; or drop `task` and
  use `.task(id: amount)`, which cancels and restarts by itself when the id changes.
- *"What's actor reentrancy, and could it bite here?"* — State can change across any `await`.
  Here it's handled, because after the `await` the task only checks cancellation before writing.
:::
