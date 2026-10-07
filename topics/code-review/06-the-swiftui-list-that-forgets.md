---
title: 06 · The SwiftUI list that forgets
summary: A SwiftUI transactions screen that reloads, loses its data and stutters — review it.
minutes: 20
sources:
- Apple · StateObject — the view owns the object and keeps it across updates | https://developer.apple.com/documentation/swiftui/stateobject
- Apple · SwiftUI View — the task modifier is cancelled when the view disappears | https://developer.apple.com/documentation/swiftui/view
---

*Shape: review this PR · **Likely**, not reported: no first-hand report names a SwiftUI snippet,
but most scale-ups now build new screens in SwiftUI · SwiftUI — the fix typechecks against the iOS 18 SDK in Swift 6 mode; behaviour checked by hand*

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
            List(filtered(items)) { item in
                NavigationLink(value: item) {
                    LabeledContent(item.title) {
                        Text(item.date, format: .dateTime.day().month().year())
                    }
                }
            }
        }
    }

    private func filtered(_ items: [Transaction]) -> [Transaction] {
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
