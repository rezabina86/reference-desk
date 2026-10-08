---
title: 06 · The SwiftUI list that forgets
summary: A SwiftUI transactions screen that reloads, loses its data and stutters — review it.
minutes: 20
group: Review this PR
sources:
- Apple · StateObject — the view owns the object and keeps it across updates | https://developer.apple.com/documentation/swiftui/stateobject
- Apple · SwiftUI View — the task modifier is cancelled when the view disappears | https://developer.apple.com/documentation/swiftui/view
---

*Shape: review this PR · **Likely**, not reported: no first-hand report names a SwiftUI snippet,
but most scale-ups now build new screens in SwiftUI · SwiftUI — the fix typechecks against the iOS SDK (iOS 18 target) in Swift 6 mode; behaviour checked by hand*

> "Users say the list sometimes empties itself and reloads when they come back from a detail
> screen, the search is case-sensitive, and scrolling stutters on long accounts. Review it."

```swift
struct TransactionsScreen: View {
    @ObservedObject var model = TransactionsModel()
    @State private var query = ""

    var body: some View {
        let formatter = DateFormatter()
        formatter.dateStyle = .medium
        return List {
            ForEach(model.items.filter { query.isEmpty || $0.title.contains(query) },
                    id: \.title) { item in
                HStack {
                    Text(item.title)
                    Spacer()
                    Text(formatter.string(from: item.date))
                }
                .onTapGesture { model.select(item) }
            }
        }
        .searchable(text: $query)
        .onAppear { model.load() }
    }
}

final class TransactionsModel: ObservableObject {
    @Published var items: [Transaction] = []

    func load() {
        Task {
            let items = try? await TransactionsAPI.fetch()
            self.items = items ?? []
        }
    }

    func select(_ item: Transaction) { /* … */ }
}
```

::: A hint, if you're stuck
- When the parent view redraws, does this view create a new `TransactionsModel`? Who owns it?
- `.onAppear` fires again when you come back from a detail screen. What does `load()` do then?
- Two transactions both called "Coffee": what does `id: \.title` mean to SwiftUI?
- What work runs every single time `body` is evaluated?
:::

::: The key
1. **The model is recreated.** `@ObservedObject` with a default value doesn't own the object;
   every time the parent re-renders, a fresh empty `TransactionsModel` is created. That's the list
   emptying itself. Use `@StateObject` (or an `@Observable` model in `@State`).
2. **Published state changed off the main actor.** The model isn't `@MainActor`, so `items` is set
   from a background executor — a runtime warning today, a compile error in Swift 6.
3. **Reload on every appearance.** `.onAppear` fires again on returning from the detail screen; the
   request isn't cancelled if the user leaves. Use `.task`, which runs once per appearance and
   cancels on disappear — and decide whether coming back should reload at all.
4. **Errors become an empty list.** `try?` plus `?? []` tells the user "no transactions" when the
   network failed. In a banking app that's alarming. Add an error state.
5. **Duplicate titles break identity.** `id: \.title` — two "Coffee" rows share an id, so SwiftUI
   mixes up rows, animations and taps. Make `Transaction` `Identifiable` on its real id.
6. **A `DateFormatter` per render.** Formatters are expensive and `body` runs often. Use
   `Text(item.date, format: .dateTime.day().month().year())` or a static formatter.
7. **Filtering inside `body`** runs on every render, for every keystroke and every unrelated state
   change. Fine for a few hundred rows; for long accounts move it into the model and recompute only
   when the query or the data changes (or filter server-side).
8. **Case-sensitive search.** `contains` misses "coffee" for "Coffee". Use
   `localizedStandardContains`, which also ignores diacritics.
9. **Tap gesture instead of a button.** `onTapGesture` gives VoiceOver no button trait and no
   highlight. Use `Button` or a `NavigationLink`.
10. **Global `TransactionsAPI.fetch()`** — not injectable, so the model can't be tested.
:::

::: The idea behind it
In SwiftUI a view is a cheap description that gets thrown away and rebuilt all the time. Anything
that must survive that — like your data model — needs an *owner* that SwiftUI keeps alive for you.

`@StateObject` (or `@State` holding an `@Observable` model) says "this view owns it; keep it across
redraws". `@ObservedObject` says "someone else owns it; I only watch it". Create the object right
there under `@ObservedObject` and every redraw makes a brand-new, empty model — the list "forgets".

*Identity* is the other half. SwiftUI matches rows between redraws by their `id`. If two rows share
an id, SwiftUI can't tell them apart, so state, animations and taps end up on the wrong row. Use a
real unique id.

And because `body` can run many times a second, anything expensive inside it — a new
`DateFormatter`, filtering a long list — runs every time. Keep `body` a cheap description and do the
work once, somewhere else.
:::

::: The fix
```swift
@MainActor
@Observable
final class TransactionsModel {
    enum State { case loading, loaded([Transaction]), failed(String) }

    private(set) var state: State = .loading
    private let api: TransactionsFetching

    init(api: TransactionsFetching) { self.api = api }

    func load() async {
        do {
            state = .loaded(try await api.fetch())
        } catch {
            // .task is cancelled when a detail screen is pushed. URLSession reports that as
            // URLError(.cancelled), not CancellationError, so check the task, not the error.
            guard !Task.isCancelled else { return }
            state = .failed(error.localizedDescription)
        }
    }
}

struct TransactionsScreen: View {
    @State private var model: TransactionsModel
    @State private var query = ""

    init(api: TransactionsFetching) {
        _model = State(initialValue: TransactionsModel(api: api))
    }

    var body: some View {
        content
            .searchable(text: $query)
            .task { await model.load() }
    }

    @ViewBuilder private var content: some View {
        switch model.state {
        case .loading:
            ProgressView()
        case .failed(let message):
            ContentUnavailableView("Couldn't load transactions",
                                   systemImage: "exclamationmark.triangle",
                                   description: Text(message))
        case .loaded(let items):
            // Needs a NavigationStack above with .navigationDestination(for: Transaction.self),
            // or tapping a row does nothing.
            List(Self.filtered(items, by: query)) { item in
                NavigationLink(value: item) {
                    LabeledContent(item.title) {
                        Text(item.date, format: .dateTime.day().month().year())
                    }
                }
            }
        }
    }

    static func filtered(_ items: [Transaction], by query: String) -> [Transaction] {
        query.isEmpty ? items : items.filter { $0.title.localizedStandardContains(query) }
    }
}
```

`.task` still runs again when you come back from a detail screen. That's now harmless: `load()`
never resets the state to `.loading`, so the list stays on screen and refreshes in place. If coming
back shouldn't refetch at all, start `load()` with `if case .loaded = state { return }`.

The filter stays in `body` on purpose: a page of transactions is small. Point 7 says when to move it.

`@Observable` and `ContentUnavailableView` need iOS 17. On iOS 16, keep `ObservableObject` with
`@StateObject` and a plain empty-state view — the fixes are the same.
:::

::: Now write the tests
> "Good. Now write me a few tests for the model and the search — the ones you'd want before
> merging."

What I'd test, and why:

1. **A cancelled load leaves the screen alone.** Push a detail screen mid-load and SwiftUI cancels
   `.task`; URLSession throws `URLError(.cancelled)`. Without the `Task.isCancelled` check, the user
   comes back to "Couldn't load transactions". That's the subtle bug in this fix, so it gets the
   first test.
2. **A reload keeps the list on screen.** Coming back from a detail screen runs `load()` again. The
   list must stay visible while it waits — no flash to a spinner — and then update in place.
3. **Success shows the list, failure shows the error.** The old code turned a network error into
   an empty list. These two pin the new states.
4. **Search ignores case and accents.** "coffee" finds "Coffee", "cafe" finds "Café". This was one
   of the reported bugs.

I wouldn't unit-test the view itself. `List`, `.task` and `.searchable` are Apple's code, and
"does this row look right" is a job for a preview or a UI test, not a unit test.

**The seam.** A *seam* is a place where a test can swap in its own piece. Here it's
`TransactionsFetching`: the model takes it in `init`, so the tests pass a *fake* — a small
stand-in that answers however the test wants, with no network. One fake answers at once. The other
waits until the test says "answer now", so the test can cancel or check the screen *while* the load
is in flight. No sleeps, so the tests are *deterministic*: same result every run. The filter was a
private method on the view; I made it `static` and gave it the query as a parameter, so a test can
call it without building a view.

```swift
import Foundation
import Testing

// A fake that answers at once.
struct StubFetcher: TransactionsFetching {
    let result: Result<[Transaction], any Error>
    func fetch() async throws -> [Transaction] { try result.get() }
}

// A fake that waits until the test says "answer now".
actor ControlledFetcher: TransactionsFetching {
    private var pending: CheckedContinuation<[Transaction], any Error>?
    private var callWaiter: CheckedContinuation<Void, Never>?

    func fetch() async throws -> [Transaction] {
        try await withCheckedThrowingContinuation { continuation in
            pending = continuation
            callWaiter?.resume()
            callWaiter = nil
        }
    }

    func waitUntilCalled() async {
        if pending != nil { return }
        await withCheckedContinuation { callWaiter = $0 }
    }

    func finish(with result: Result<[Transaction], any Error>) {
        pending?.resume(with: result)
        pending = nil
    }
}

func transaction(_ title: String) -> Transaction {
    Transaction(id: UUID(), title: title, date: .now)
}

extension TransactionsModel.State {
    var items: [Transaction]? {
        if case .loaded(let items) = self { items } else { nil }
    }
    var isLoading: Bool {
        if case .loading = self { true } else { false }
    }
    var isFailed: Bool {
        if case .failed = self { true } else { false }
    }
}

@MainActor
struct TransactionsModelTests {
    @Test func cancelledLoadLeavesStateUntouched() async {
        // Given a load that is waiting for the network
        let fetcher = ControlledFetcher()
        let model = TransactionsModel(api: fetcher)
        let task = Task { await model.load() }
        await fetcher.waitUntilCalled()

        // When the screen goes away and URLSession reports the cancel as an error
        task.cancel()
        await fetcher.finish(with: .failure(URLError(.cancelled)))
        await task.value

        // Then no error screen appears
        #expect(model.state.isLoading)
    }

    @Test func reloadKeepsTheListOnScreen() async {
        // Given a list that has loaded once
        let coffee = transaction("Coffee"), rent = transaction("Rent")
        let fetcher = ControlledFetcher()
        let model = TransactionsModel(api: fetcher)
        let first = Task { await model.load() }
        await fetcher.waitUntilCalled()
        await fetcher.finish(with: .success([coffee]))
        await first.value

        // When it loads again, as it does on coming back from a detail screen
        let second = Task { await model.load() }
        await fetcher.waitUntilCalled()

        // Then the old list stays while we wait, and is replaced in place
        #expect(model.state.items == [coffee])
        await fetcher.finish(with: .success([coffee, rent]))
        await second.value
        #expect(model.state.items == [coffee, rent])
    }

    @Test func successfulLoadShowsTheList() async {
        let coffee = transaction("Coffee")
        let model = TransactionsModel(api: StubFetcher(result: .success([coffee])))

        await model.load()

        #expect(model.state.items == [coffee])
    }

    @Test func failedLoadShowsAnError() async {
        let model = TransactionsModel(api: StubFetcher(result: .failure(URLError(.notConnectedToInternet))))

        await model.load()

        #expect(model.state.isFailed)
    }

    @Test func searchIgnoresCaseAndAccents() {
        let items = [transaction("Coffee"), transaction("Café Central"), transaction("Rent")]

        #expect(TransactionsScreen.filtered(items, by: "coffee").map(\.title) == ["Coffee"])
        #expect(TransactionsScreen.filtered(items, by: "cafe").map(\.title) == ["Café Central"])
        #expect(TransactionsScreen.filtered(items, by: "").count == 3)
    }
}
```

Ran on the iOS Simulator (iOS 18.5, Swift 6 mode): 5 tests, all passed.
:::

::: What I'd ask next
- *"`@StateObject` vs `@ObservedObject` in one sentence."* — `@StateObject` means this view creates
  and owns it; `@ObservedObject` means someone else owns it and passes it in.
- *"Is `@State` with an `@Observable` model a drop-in for `@StateObject`?"* — Almost.
  `State(initialValue:)` builds a new model every time the parent re-renders and throws it away;
  `@StateObject` takes an autoclosure and builds it once. Keep the model's `init` cheap, with no work
  started in it.
- *"How would you find what's making scrolling stutter?"* — Instruments' SwiftUI template (view
  body counts), `Self._printChanges()` in a debug build, then cut work out of `body`.
- *"10,000 transactions — what changes?"* — Paginate from the API, load more near the end of the
  list, and stop filtering client-side.
- *"Why does `Identifiable` matter beyond `ForEach`?"* — Identity drives state preservation,
  transitions and diffing; a wrong id moves `@State` between rows.
:::
