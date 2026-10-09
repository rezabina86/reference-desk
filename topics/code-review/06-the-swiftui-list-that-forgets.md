---
title: 06 · The SwiftUI list that forgets
summary: A SwiftUI transactions screen that reloads, loses its data and stutters — review it.
minutes: 20
group: Review this PR
sources:
- Apple · StateObject — the view owns the object and keeps it across updates | https://developer.apple.com/documentation/swiftui/stateobject
- Apple · SwiftUI View — the task modifier is cancelled when the view disappears | https://developer.apple.com/documentation/swiftui/view
---

*Shape: review this PR · Reported: not reported — **likely**, as most teams now build new screens in SwiftUI · Verified: the snippet compiles clean in Swift 6 mode, the fix typechecks for iOS 18 and its model tests ran on macOS, Swift 6.4*

> "Users say the list sometimes empties itself and reloads when they come back from a detail
> screen, the search is case-sensitive, and typing in search stutters on long accounts. Review it."

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
- Tap the empty space between the title and the date. What happens?
- What work runs every time you type one letter into the search field?
:::

::: The key — what I expect a senior to find
The first item is the reported "list empties itself" bug, so it leads.

1. **The model is recreated.** `@ObservedObject` with a default value doesn't own the object. Every
   time the parent re-renders, a fresh, empty `TransactionsModel` is made — the list "forgets". Use
   `@StateObject` (or an `@Observable` model held in `@State`).
2. **Published state is written off the main thread.** The model isn't `@MainActor`, so the `Task`
   in `load()` sets `items` from a background thread. At run time that's a purple warning ("Publishing
   changes from background threads is not allowed"). The compiler doesn't catch it here — this snippet
   compiles clean in Swift 6 mode, and whether it ever does depends on the Swift version and the
   target's default isolation. Annotate the model `@MainActor`.
3. **Loads overlap, and the older one can win.** `.onAppear` fires again on coming back from a
   detail screen, so a second load starts while the first may still run. Whichever reply arrives
   last wins, even if it's older. Use `.task`, which cancels its work when the view disappears.
4. **The request outlives the screen.** The unstructured `Task` holds `self` strongly and nothing
   cancels it, so the model stays alive and keeps working after the user leaves. `.task` ties the
   work to the view's lifetime.
5. **Errors become an empty list.** `try?` plus `?? []` tells the user "no transactions" when the
   network failed. In a banking app that's alarming. Keep the error and show it.
6. **Duplicate titles break identity.** `id: \.title` — two "Coffee" rows share an id, so SwiftUI
   mixes up rows, animations and taps. Make `Transaction` `Identifiable` on its real id.
7. **Tapping the gap does nothing.** `.onTapGesture` on an `HStack` only hit-tests the parts that
   draw something; the `Spacer` draws nothing, so the middle of the row ignores taps. It also gives
   VoiceOver no button trait. Use a `Button` (or add `.contentShape(Rectangle())`).
8. **Search is case-sensitive.** `contains` misses "coffee" for "Coffee". Use
   `localizedStandardContains`, which also ignores accents — "cafe" finds "Café".
9. **No loading state.** The first launch shows a blank list, which looks exactly like "you have no
   transactions". Show a spinner until the first answer.
10. **No pull to refresh.** The only way to reload is to leave and come back. Add `.refreshable`,
    which needs an `async` load.
11. **`load()` isn't `async`.** It starts a task and returns at once, so nobody can await it: not
    `.task`, not `.refreshable`, not a test. Make it `func load() async`.
12. **Global `TransactionsAPI.fetch()`.** It can't be swapped, so the model can't be tested without
    a network. Inject it.
13. **Typing stutters on long accounts.** Each letter changes `query`, so `body` runs again: it
    filters the whole array and SwiftUI re-diffs the list. Fine for a page; for thousands of rows,
    filter in the model, debounce, or search server-side.
14. **A `DateFormatter` built on every render.** Formatters are slow to create and `body` runs on
    every keystroke. Use `Text(item.date, format: .dateTime.day().month().year())`.
15. **Access control.** `items` can be set from outside the model, and `model` is a public-ish
    `var` a parent could replace. Make them `private(set)` and `private`.
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
struct Transaction: Identifiable, Equatable { let id: UUID; let title: String; let date: Date }  // key 6

struct TransactionsScreen: View {
    @StateObject private var model: TransactionsModel                 // keys 1, 15
    @State private var query = ""

    init(fetch: @escaping @Sendable () async throws -> [Transaction] = TransactionsAPI.fetch) {
        _model = StateObject(wrappedValue: TransactionsModel(fetch: fetch))   // key 12
    }

    var body: some View {
        List(model.items(matching: query)) { item in                   // keys 6, 8, 13
            Button { model.select(item) } label: {                     // key 7
                HStack {
                    Text(item.title)
                    Spacer()
                    Text(item.date, format: .dateTime.day().month().year())   // key 14
                }
            }
        }
        .overlay { if let message = model.error { Text(message) } }    // key 5
        .searchable(text: $query)
        .task { await model.load() }                                   // keys 3, 4
    }
}

@MainActor                                                             // key 2
final class TransactionsModel: ObservableObject {
    @Published private(set) var items: [Transaction] = []              // key 15
    @Published private(set) var error: String?                         // key 5
    private let fetch: @Sendable () async throws -> [Transaction]

    init(fetch: @escaping @Sendable () async throws -> [Transaction]) { self.fetch = fetch }

    func load() async {                                                // key 11
        do {
            items = try await fetch()
            error = nil
        } catch {
            guard !Task.isCancelled else { return }                    // leaving isn't an error
            self.error = "Couldn't load transactions."
        }
    }

    func items(matching query: String) -> [Transaction] {             // keys 8, 13
        query.isEmpty ? items : items.filter { $0.title.localizedStandardContains(query) }
    }

    func select(_ item: Transaction) { /* … */ }
}
```

**Said out loud, not coded:** an `@Observable` model in `@State` on iOS 17; a state enum
(loading, loaded, failed) with a spinner and `ContentUnavailableView` for keys 5 and 9;
`.refreshable { await model.load() }` (key 10, one line once `load()` is `async`); a debounced or
server-side search and pagination for very long accounts.

Why each piece:

- **The closure with a default is the one seam.** Production passes `TransactionsAPI.fetch`, tests
  pass their own closure. No protocol needed for one function.
- **Check the task, not the error.** Pushing a detail screen cancels `.task`, and URLSession reports
  that as `URLError(.cancelled)`, not `CancellationError`. `Task.isCancelled` catches both.
- **`load()` never clears `items`.** `.task` still runs again when you come back. The old list stays
  on screen and is replaced in place — no flash to empty.
- **The filter moved into the model as a function of the query.** It's the same work, but it's
  out of the view and a test can call it.
:::

::: Now write the tests
> "Good. Now write me a few tests for the model and the search — the ones you'd want before
> merging."

**What I'd test, and why**

1. **A failed load shows an error, not an empty list.** That's the bug the old `try?` hid.
2. **A cancelled load shows no error.** Push a detail screen mid-load and SwiftUI cancels `.task`;
   URLSession throws `URLError(.cancelled)`. Without the `Task.isCancelled` check the user comes back
   to "Couldn't load transactions". That's the edge case in this fix.
3. **A reload keeps the list on screen.** Coming back runs `load()` again. The list must stay while
   it waits, then update in place — the regression test for "the list empties itself".
4. **Search ignores case and accents.** "coffee" finds "Coffee", "cafe" finds "Café". A reported bug.

I wouldn't unit-test the view. `List`, `.task` and `.searchable` are Apple's code, and "does this
row look right" is a job for a preview or a UI test. The `@StateObject` fix is checked by hand: push
a detail screen, come back, and the list is still there.

**The seam.** A *seam* is a place where a test can swap in its own piece. Here it's the `fetch`
closure. Most tests pass a closure that answers at once. Two need the load to wait *in flight*, so
`PendingFetch` holds the answer until the test gives it. `waitUntil` yields to other tasks a bounded
number of times instead of sleeping, so the tests give the same result on every run.

```swift
import Foundation
import Testing

/// Holds the fetch open until the test answers it.
actor PendingFetch {
    private var continuation: CheckedContinuation<[Transaction], any Error>?
    var isWaiting: Bool { continuation != nil }

    func fetch() async throws -> [Transaction] {
        try await withCheckedThrowingContinuation { continuation = $0 }
    }

    func answer(_ result: Result<[Transaction], any Error>) {
        continuation?.resume(with: result)
        continuation = nil
    }
}

@MainActor
func waitUntil(maxYields: Int = 1_000, _ condition: () async -> Bool) async {
    for _ in 0..<maxYields {
        if await condition() { return }
        await Task.yield()
    }
    Issue.record("Condition never became true")
}

func transaction(_ title: String) -> Transaction {
    Transaction(id: UUID(), title: title, date: .now)
}

@MainActor
struct TransactionsModelTests {
    @Test func failedLoadShowsAnErrorNotAnEmptyList() async {
        let model = TransactionsModel(fetch: { throw URLError(.notConnectedToInternet) })

        await model.load()

        #expect(model.error == "Couldn't load transactions.")
    }

    @Test func cancelledLoadShowsNoError() async {
        // Given a load waiting for the network
        let pending = PendingFetch()
        let model = TransactionsModel(fetch: { try await pending.fetch() })
        let task = Task { await model.load() }
        await waitUntil { await pending.isWaiting }

        // When the user leaves and URLSession reports the cancel as an error
        task.cancel()
        await pending.answer(.failure(URLError(.cancelled)))
        await task.value

        // Then no error appears
        #expect(model.error == nil)
    }

    @Test func reloadKeepsTheListOnScreen() async {
        // Given a list that has loaded once
        let coffee = transaction("Coffee"), rent = transaction("Rent")
        let pending = PendingFetch()
        let model = TransactionsModel(fetch: { try await pending.fetch() })
        let first = Task { await model.load() }
        await waitUntil { await pending.isWaiting }
        await pending.answer(.success([coffee]))
        await first.value

        // When it loads again, as .task does on coming back from a detail screen
        let second = Task { await model.load() }
        await waitUntil { await pending.isWaiting }

        // Then the old list stays while we wait, and is replaced in place
        #expect(model.items == [coffee])
        await pending.answer(.success([coffee, rent]))
        await second.value
        #expect(model.items == [coffee, rent])
    }

    @Test func searchIgnoresCaseAndAccents() async {
        let model = TransactionsModel(fetch: {
            [transaction("Coffee"), transaction("Café Central"), transaction("Rent")]
        })
        await model.load()

        #expect(model.items(matching: "coffee").map(\.title) == ["Coffee"])
        #expect(model.items(matching: "cafe").map(\.title) == ["Café Central"])
        #expect(model.items(matching: "").count == 3)
    }
}
```

Ran with Swift 6.4: 4 tests, all passed.
:::

::: What I'd ask next
- *"`@StateObject` vs `@ObservedObject` in one sentence."* — `@StateObject` means this view creates
  and owns it; `@ObservedObject` means someone else owns it and passes it in.
- *"Would you move to `@Observable`?"* — On iOS 17, yes: `@State private var model`. One catch:
  `@State`'s initial value is built again each time the parent re-creates the view (SwiftUI keeps
  only the first), while `@StateObject` takes an autoclosure and builds it once. So keep the model's
  `init` cheap, with no work started in it.
- *"How would you find what's making typing stutter?"* — Instruments' SwiftUI template (how often
  each `body` runs), `Self._printChanges()` in a debug build, then cut work out of `body`.
- *"10,000 transactions — what changes?"* — Paginate from the API, load more near the end of the
  list, and search on the server.
- *"Why does `Identifiable` matter beyond `ForEach`?"* — Identity drives state preservation,
  transitions and diffing; a wrong id moves `@State` between rows.
:::
