---
title: 01 · The transactions that don't add up
summary: A modern SwiftUI transactions list — @Observable, NavigationStack, .task, .refreshable — with its service in a local package. It doesn't build, rows don't open, one record blanks the screen and refresh doubles the list. Fix it, then add merchant search and a spend total, and test both.
minutes: 60
group: Rounds
sources:
- Apple · SwiftUI Transaction — the SwiftUI type a model named Transaction collides with | https://developer.apple.com/documentation/swiftui/transaction
- Apple · navigationDestination(for:destination:) — declare it outside lazy containers such as List | https://developer.apple.com/documentation/swiftui/view/navigationdestination(for:destination:)
- Apple · Migrating to the Observable macro — @Observable with @State instead of ObservableObject | https://developer.apple.com/documentation/swiftui/migrating-from-the-observable-object-protocol-to-the-observable-macro
- Apple · localizedStandardContains(_:) — case- and diacritic-insensitive, like system search | https://developer.apple.com/documentation/foundation/nsstring/localizedstandardcontains(_:)
- Apple · ContentUnavailableView — the standard empty, error and no-results state | https://developer.apple.com/documentation/swiftui/contentunavailableview
- Dojo · iOS live-coding senior interview — Xcode 26, iOS 26 target, a transactions screen to change | https://github.com/dojo-engineering/ios-live-coding-senior-interview
---

*Shape: C · review it, then extend it — 60 minutes, your Xcode, screen shared, no AI assistant · Reported:
Uber São Paulo's iOS round (code review, then a live feature), GetYourGuide's pair coding on an existing
codebase, Doctolib's pair-programming interview, and a real European take-home of this exact shape (a SwiftUI
list, a local service package, an empty test target) · Verified: Xcode 27.1, iOS 26 target, Swift 6 language
mode with main-actor default isolation. The starter fails with exactly the two build errors below. On the
iPhone simulator, every runtime bug in the key was reproduced, and the console lines are quoted as logged.
The fix and the feature build with no warnings, and the five tests pass on the simulator.*

**How the hour runs**

| Time | The interviewer says | You're scored on |
|---|---|---|
| 0:00–0:05 | "Clone it, open it, get it running." | Reading the build error, naming the cause |
| 0:05–0:25 | "Walk me through what you'd change. Fix what matters." | Severity order, root causes, the console |
| 0:25–0:50 | "Product wants search and a spend total." | The questions you ask first, states, where logic lives |
| 0:50–1:00 | "Write a few tests. Then: what if search hits the server?" | Testable design, follow-up reasoning |

> "Here's a small app — a list of a user's card transactions. The service is in a local package, so
> you can pretend it's the network. Get it running, then tell me what you'd change before this ships.
> Fix what matters. Talk as you go."

The project is in `LiveCodingLab/Round01-Transactions`. It's written the way a 2026 project is: `@Observable`
with `@State`, `NavigationStack` with value-based links, `.task`, `.refreshable`, format styles. The bugs are
the ones that survive in modern code — not "use the new API".

```swift
// TransactionsService/Sources/TransactionsService/TransactionService.swift
import Foundation

// MARK: - Model
public struct Transaction: Decodable, Identifiable, Hashable, Sendable {
    public let id: String
    let merchant: String
    let amountMinor: Int        // in the currency's minor unit: -410 is -4.10
    let currency: String
    let category: String
    let bookedAt: String
}

// MARK: - Service
public struct TransactionService: Sendable {
    public init() {}

    private let json = """
    [
      { "id": "tx_001", "merchant": "Café Einstein", "amountMinor": -410,  "currency": "EUR", ... "bookedAt": "2026-10-14T08:12:00Z" },
      { "id": "tx_002", "merchant": "Rewe",          "amountMinor": -3289, "currency": "EUR", ... },
      ...
      { "id": "tx_005", "merchant": "Pret A Manger", "amountMinor": -645,  "currency": "GBP", ... },
      { "id": "tx_006", "merchant": "Rewe",          "amountMinor": 1299,  "currency": "EUR", "category": "refund", ... },
      ...
      { "id": "tx_009", "merchant": "Lidl",          "amountMinor": -1874, "currency": "EUR", "category": "groceries" }
    ]
    """

    public func fetchTransactions() async throws -> [Transaction] {
        try await Task.sleep(for: .milliseconds(800))   // simulate the network
        return try JSONDecoder().decode([Transaction].self, from: Data(json.utf8))
    }
}
```

```swift
// Transactions/Transactions/TransactionListViewModel.swift — the target's default isolation is MainActor
import Foundation
import Observation
import TransactionsService

@Observable
final class TransactionListViewModel {
    var transactions: [Transaction] = []
    var isLoading = false
    var errorMessage: String?

    private let service = TransactionService()

    func load() async {
        isLoading = true
        do {
            let result = try await service.fetchTransactions()
            DispatchQueue.main.async {
                self.transactions.append(contentsOf: result.sorted { $0.bookedAt > $1.bookedAt })
                self.isLoading = false
            }
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}
```

```swift
// Transactions/Transactions/TransactionListView.swift
import SwiftUI
import TransactionsService

struct TransactionListView: View {
    @State private var viewModel = TransactionListViewModel()

    var body: some View {
        NavigationStack {
            List {
                ForEach(viewModel.transactions, id: \.merchant) { transaction in
                    NavigationLink(value: transaction) {
                        TransactionRow(transaction: transaction)
                    }
                    .navigationDestination(for: Transaction.self) { transaction in
                        TransactionDetailView(transaction: transaction)
                    }
                }
            }
            .navigationTitle("Transactions")
            .overlay {
                if viewModel.isLoading {
                    ProgressView()
                }
            }
            .task {
                await viewModel.load()
            }
            .refreshable {
                await viewModel.load()
            }
            .alert("Something went wrong", isPresented: .constant(viewModel.errorMessage != nil)) {
                Button("OK") {}
            } message: {
                Text(viewModel.errorMessage ?? "")
            }
        }
    }
}

struct TransactionRow: View {
    let transaction: Transaction

    var body: some View {
        HStack {
            VStack(alignment: .leading) {
                Text(transaction.merchant)
                    .font(.headline)
                Text(transaction.bookedAt.prefix(10))
                    .font(.caption)
            }
            Spacer()
            Text(Double(transaction.amountMinor) / 100, format: .currency(code: "USD"))
                .foregroundStyle(transaction.amountMinor < 0 ? .red : .green)
        }
    }
}

// TransactionDetailView: a Form of LabeledContent rows with the same fields and the same "USD".
```

## Part 1 — make it run, then review it

::: A hint, if you're stuck
The first build error isn't about a typo. Read which name it calls ambiguous and think about which other
module you imported that has the same name. Once it runs, use it like a user: tap OK, tap a row, pull to
refresh — and keep the console open. SwiftUI tells you about two of the bugs in plain English.
:::

::: The key — what I expect a senior to find
In the order you'd hit them: build, run, use, read.

**It doesn't build**

1. **`'Transaction' is ambiguous for type lookup in this context`.** SwiftUI has its own `Transaction`
   (the animation context), and the view imports both modules. The view model file compiles, because it
   doesn't import SwiftUI, and that's a clue worth saying out loud. Writing `TransactionsService.Transaction`
   fixes this file, but every SwiftUI client of the package pays the same cost. Rename it in the package to
   `CardTransaction`: the clash is in our public API.
2. **`'bookedAt' is inaccessible due to 'internal' protection level`.** Only `id` is `public`. Make the
   stored properties public. Add a `public init` too: a public struct doesn't get a public memberwise init,
   and the tests and previews you'll write need one.

**It runs, and shows an alert**

3. **"The data couldn't be read because it is missing."** `tx_009` is pending, so it has no `bookedAt`, and
   one record takes down the whole list. Use `let bookedAt: Date?` with `.iso8601` decoding: a pending
   payment is a real state, not bad data. Name the other tool, a lossy array that skips broken
   elements, and say why it's wrong here: it would hide the pending payment.
4. **Tap OK, and the spinner spins forever.** `isLoading` is never reset in the `catch`. Three separate
   properties can contradict each other: loading and failed at once, or loaded with an error. Replace
   them with one `State` enum: `loading`, `loaded([CardTransaction])`, `failed(String)`.
5. **`isPresented: .constant(...)`.** Tapping OK can't write back, so `errorMessage` is never cleared. The
   alert disappears, but the condition stays true. A second failure, such as a pull-to-refresh with no
   network, has no false → true change, so it shows nothing. Drive the error from state instead: a
   `ContentUnavailableView` with a Try again button. If it must be an alert, give it a real binding.

**It loads — now use it**

6. **Tap a row, and nothing happens.** The console says why:
   *"Do not put a navigation destination modifier inside a "lazy" container, like `List` or `LazyVStack`…
   It will be ignored."* — and on the tap: *"The link cannot be activated."* Move `navigationDestination`
   outside the `List`. Push the `id` rather than the whole value, so the detail reads the current data and
   not a copy taken at tap time.
7. **The second Café Einstein row shows the first one's amount and date. The second Rewe row shows
   −32.89 in red, but it's a +12.99 refund.** `id: \.merchant` gives two rows one identity, and the
   console says so: *"the ID Café Einstein occurs multiple times within the collection, this will give
   undefined results!"* The model is already `Identifiable`, so drop the `id:`.
8. **Pull to refresh, and the list doubles** — 18 rows, with the second half unsorted. `load()` *appends*.
   The cause is the append, not the second call: assign the result.
9. **Euro and pound rows show `$`.** `.currency(code: "USD")` is hard-coded, and `Double / 100` turns money
   into a float. Expose `amount: Decimal`, and format it with the transaction's own currency code.
10. **The date is a raw string prefix**, and the string sort only works because ISO-8601 happens to sort
    as text. Once it's a `Date?`, format it, show "Pending" for `nil`, and sort pending first.

**Read the code**

11. **`DispatchQueue.main.async` inside an `async` function on a main-actor type.** With the target's
    default isolation, the view model is already on the main actor, so the hop does nothing useful — and it
    breaks something. `load()` now *returns before the data is assigned*. `.refreshable` stops its spinner
    too early, and a test that awaits `load()` sees an empty list. Assign directly after the `await`.
12. **The service is built inside the view model.** Nothing can be tested without the real 800 ms
    service. Put a `TransactionFetching: Sendable` protocol in the package, inject it in `init`, and mark
    the stored dependency `@ObservationIgnored`. You need this before Part 3, so do it now.
13. **Said, not coded:**
    - Red and green alone carry the sign, which fails colour-blind users and VoiceOver. The currency format
      already prints the minus, so colour can mark money in only.
    - The `catch` treats `CancellationError` as a failure. `.task` is cancelled when the view goes away.
    - `amountMinor / 100` is wrong for JPY (0 decimals) and KWD (3).
    - `@State` with an injected view model: the initial value is built on every `init` of the view and
      thrown away after the first. That's fine at the root of the app, but not on a view that's
      re-initialised often.

What sinks this part: `removeDuplicates()` over the list, which treats 8 as a symptom; `try?` on the
decode, which turns 3 into a silent empty list; missing the console in 6 and poking at the
`NavigationLink`; or leaving 12 for later, and then having nothing to test against in Part 3.
:::

::: The idea behind it
Every bug here comes from the same mistake: **state that isn't one thing**. The flags can disagree
(4, 5). The list grows instead of being replaced (8). Identity comes from a display field (7). Navigation
is declared where SwiftUI can't see it (6). The fix that makes all of them go away is one `state`
property, replaced on every load, with real IDs and navigation declared once at the stack. That fix
also makes Part 2 small and Part 3 possible.

What "modern" means in this round:

| Use | Instead of |
|---|---|
| `@Observable` held in `@State` | `ObservableObject` / `@StateObject` / `@Published` |
| `NavigationStack` + `NavigationLink(value:)` + one `navigationDestination` outside the list | `NavigationView`, `NavigationLink(destination:)` |
| `.task` and `.refreshable` with `async` functions | `onAppear { Task { … } }` and GCD hops |
| Main-actor default isolation, Swift 6 language mode | `DispatchQueue.main.async` sprinkled after `await` |
| `ContentUnavailableView` (and `.search`) | a hand-rolled empty `VStack`, or an alert for every state |
| `Text(value, format: .currency(code:))`, `Date.FormatStyle` | string interpolation and `specifier:` |
| Swift Testing (`@Test`, `#expect`) | `XCTestCase` |
:::

::: The fix
Rename, make it public, model pending as `nil`, and add the seam:

```swift
import Foundation

// MARK: - Model
public struct CardTransaction: Decodable, Identifiable, Hashable, Sendable {
    public let id: String
    public let merchant: String
    public let amountMinor: Int          // minor units: -410 is -4.10
    public let currency: String
    public let category: String
    public let bookedAt: Date?           // nil while the payment is pending

    public var amount: Decimal { Decimal(amountMinor) / 100 }   // two-decimal currencies only

    public init(id: String, merchant: String, amountMinor: Int, currency: String, category: String, bookedAt: Date?) {
        self.id = id
        self.merchant = merchant
        self.amountMinor = amountMinor
        self.currency = currency
        self.category = category
        self.bookedAt = bookedAt
    }
}

// MARK: - Service
public protocol TransactionFetching: Sendable {
    func fetchTransactions() async throws -> [CardTransaction]
}

public struct TransactionService: TransactionFetching {
    public init() {}

    private let json = """ ... unchanged ... """

    public func fetchTransactions() async throws -> [CardTransaction] {
        try await Task.sleep(for: .milliseconds(800))   // simulate the network
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        return try decoder.decode([CardTransaction].self, from: Data(json.utf8))
    }
}
```

One state, replaced instead of appended, injected:

```swift
import Foundation
import Observation
import TransactionsService

@Observable
final class TransactionListViewModel {   // main actor: the target's default isolation
    enum State: Equatable {
        case loading
        case loaded([CardTransaction])
        case failed(String)
    }

    private(set) var state: State = .loading

    init(service: any TransactionFetching) {
        self.service = service
    }

    func load() async {
        if case .failed = state { state = .loading }    // a retry shows the spinner; a refresh keeps the list
        do {
            let result = try await service.fetchTransactions()
            state = .loaded(result.sorted(by: Self.pendingFirstThenNewest))   // replace, never append
        } catch is CancellationError {
            // the view went away mid-load: not an error
        } catch {
            state = .failed(error.localizedDescription)
        }
    }

    func transaction(id: CardTransaction.ID) -> CardTransaction? {
        guard case .loaded(let all) = state else { return nil }
        return all.first { $0.id == id }
    }

    @ObservationIgnored private let service: any TransactionFetching

    private static func pendingFirstThenNewest(_ a: CardTransaction, _ b: CardTransaction) -> Bool {
        switch (a.bookedAt, b.bookedAt) {
        case (nil, nil): a.id < b.id
        case (nil, _): true
        case (_, nil): false
        case let (a?, b?): a > b
        }
    }
}
```

The view: one `switch` over the state, navigation declared once outside the `List`, and the dependency
injected through `init`:

```swift
import SwiftUI
import TransactionsService

struct TransactionListView: View {
    @State private var viewModel: TransactionListViewModel

    init(service: any TransactionFetching = TransactionService()) {
        _viewModel = State(initialValue: TransactionListViewModel(service: service))
    }

    var body: some View {
        NavigationStack {
            content
                .navigationTitle("Transactions")
                .task { await viewModel.load() }
                .refreshable { await viewModel.load() }
                .navigationDestination(for: CardTransaction.ID.self) { id in   // outside the List
                    if let transaction = viewModel.transaction(id: id) {
                        TransactionDetailView(transaction: transaction)
                    }
                }
        }
    }

    @ViewBuilder
    private var content: some View {
        switch viewModel.state {
        case .loading:
            ProgressView()
        case .failed(let message):
            ContentUnavailableView {
                Label("Couldn't load transactions", systemImage: "exclamationmark.triangle")
            } description: {
                Text(message)
            } actions: {
                Button("Try again") { Task { await viewModel.load() } }
            }
        case .loaded(let transactions):
            List(transactions) { transaction in
                NavigationLink(value: transaction.id) {
                    TransactionRow(transaction: transaction)
                }
            }
        }
    }
}
```

`TransactionRow` shows `Text(transaction.amount, format: .currency(code: transaction.currency))`, the date or
"Pending", and green only for money in.
:::

## Part 2 — add the feature

> "Nice. Product wants two things: a search field that filters by merchant, and a line under the
> list that says how much was spent in what's showing."

::: A hint, if you're stuck
Before you write anything, ask what "spent" means. The data has a refund, a top-up, a pending payment
and two currencies.
:::

::: The key — what I expect a senior to find
**The questions to ask first** — each one changes the code:

- **Does "spent" mean money out only?** Yes, so the refund (+12.99) and the top-up (+500) don't reduce it.
- **Does a pending payment count?** Yes. The user has spent that money, so it's included.
- **Two currencies — convert, or one total each?** One total per currency. Adding €160 to £6 gives a
  number that means nothing, and converting needs a rate we don't have. This is the trap in the brief.
- **Match the merchant only, and should "cafe" find "Café"?** Merchant only, ignoring case and accents.

**What I'm looking at while you build:**

- Filtering and totals are computed properties on the view model over `state` and `query`, not code in
  `body`. With `@Observable`, the view re-renders on exactly what it read.
- `.searchable(text: $viewModel.query)`: a binding straight into the `@State`-held observable.
- `localizedStandardContains`: `lowercased().contains` misses "cafe" → "Café".
- `Decimal` for the total, grouped by currency.
- No results is its own state: `ContentUnavailableView.search(text:)`, not an empty white list.
- The total follows the search: it's the spend of what's *showing*.
:::

::: The fix
Added to `TransactionListViewModel`:

```swift
var query = ""

var visible: [CardTransaction] {
    guard case .loaded(let all) = state else { return [] }
    let query = query.trimmingCharacters(in: .whitespaces)
    guard !query.isEmpty else { return all }
    return all.filter { $0.merchant.localizedStandardContains(query) }   // "cafe" finds "Café"
}

/// Money out only, one total per currency: adding EUR to GBP is a number that means nothing.
var spentByCurrency: [(currency: String, amount: Decimal)] {
    Dictionary(grouping: visible.filter { $0.amountMinor < 0 }, by: \.currency)
        .map { (currency: $0.key, amount: -$0.value.reduce(Decimal.zero) { $0 + $1.amount }) }
        .sorted { $0.currency < $1.currency }
}
```

In the view, add `.searchable(text: $viewModel.query, prompt: "Merchant")` next to `.task`, and the
`.loaded` case becomes a no-results branch plus a list with a footer:

```swift
case .loaded where viewModel.visible.isEmpty:
    ContentUnavailableView.search(text: viewModel.query)
case .loaded:
    List {
        Section {
            ForEach(viewModel.visible) { transaction in
                NavigationLink(value: transaction.id) {
                    TransactionRow(transaction: transaction)
                }
            }
        } footer: {
            SpendFooter(totals: viewModel.spentByCurrency)   // "Spent: €160.42 and £6.45" with no search
        }
    }
```

```swift
struct SpendFooter: View {
    let totals: [(currency: String, amount: Decimal)]

    var body: some View {
        if !totals.isEmpty {
            Text("Spent: " + totals
                .map { $0.amount.formatted(.currency(code: $0.currency)) }
                .formatted(.list(type: .and)))
        }
    }
}
```
:::

## Part 3 — test it

> "Good. Write a few tests for what you just built."

::: Now write the tests
A fake that answers at once, and five behaviours: three from Part 1 and two from Part 2. The target's
default isolation puts the fake on the main actor. A `Sendable` protocol requirement can't be met from
there, so mark the fake `nonisolated`.

```swift
import Foundation
import Testing
import TransactionsService
@testable import Transactions

nonisolated private struct FakeService: TransactionFetching {
    var result: Result<[CardTransaction], any Error>
    func fetchTransactions() async throws -> [CardTransaction] { try result.get() }
}

private func transaction(_ id: String, _ merchant: String, _ minor: Int, _ currency: String = "EUR",
                         booked: String?) -> CardTransaction {
    CardTransaction(id: id, merchant: merchant, amountMinor: minor, currency: currency, category: "test",
                    bookedAt: booked.map { try! Date("2026-10-\($0)T08:00:00Z", strategy: .iso8601) })
}

struct TransactionListViewModelTests {
    let sample = [
        transaction("a", "Café Einstein", -410, booked: "14"),
        transaction("b", "Rewe", 1299, booked: "08"),
        transaction("c", "Pret A Manger", -645, "GBP", booked: "09"),
        transaction("d", "Lidl", -1874, booked: nil),
        transaction("e", "Café Einstein", -380, booked: "11"),
    ]

    @Test func loadsPendingFirstThenNewest() async {
        let viewModel = TransactionListViewModel(service: FakeService(result: .success(sample)))
        await viewModel.load()
        #expect(viewModel.visible.map(\.id) == ["d", "a", "e", "c", "b"])
    }

    @Test func refreshingReplacesInsteadOfDuplicating() async {
        let viewModel = TransactionListViewModel(service: FakeService(result: .success(sample)))
        await viewModel.load()
        await viewModel.load()
        #expect(viewModel.visible.count == 5)
    }

    @Test func aFailureEndsTheLoadingState() async {
        struct Offline: LocalizedError { var errorDescription: String? { "Offline" } }
        let viewModel = TransactionListViewModel(service: FakeService(result: .failure(Offline())))
        await viewModel.load()
        #expect(viewModel.state == .failed("Offline"))
    }

    @Test func searchIgnoresCaseAndAccents() async {
        let viewModel = TransactionListViewModel(service: FakeService(result: .success(sample)))
        await viewModel.load()
        viewModel.query = "cafe einstein"
        #expect(viewModel.visible.map(\.id) == ["a", "e"])
    }

    @Test func spendIsTotalledPerCurrencyAndIgnoresMoneyIn() async {
        let viewModel = TransactionListViewModel(service: FakeService(result: .success(sample)))
        await viewModel.load()
        #expect(viewModel.spentByCurrency.map(\.currency) == ["EUR", "GBP"])
        #expect(viewModel.spentByCurrency.map(\.amount) == [Decimal(string: "26.64")!, Decimal(string: "6.45")!])
    }
}
```

`refreshingReplacesInsteadOfDuplicating` only passes because of finding 11. With the `DispatchQueue` hop,
`load()` returned before the data landed, so the count was 0 and the test failed for a reason that had
nothing to do with duplicates.
:::

::: What I'd ask next
- **"Search now hits the server."** Use `.task(id: viewModel.query)` with a short `try await Task.sleep(for:)`
  before the request. SwiftUI cancels the previous task when the query changes, so a slow "ca" response
  can't overwrite "café". Send no request for an empty query.
- **"Ten thousand transactions, paged."** Add a cursor in the service and load the next page when the last
  row appears. Dedupe by `id` when a page boundary moves. This is where `append` comes back, so say why
  it's safe now.
- **"Show amounts in yen."** Minor units differ by currency. Take the exponent from the backend, or from
  `Locale.Currency`, not the hard-coded `/ 100`.
- **"The booking date shows the wrong day for some users."** `00:00Z` is the previous evening in New York.
  Decide whether a booking date is a calendar day (format it in UTC, or send `yyyy-MM-dd`) or an instant
  (local time, as now).
- **"Something outside SwiftUI needs to react when the list changes."** Use `Observations` (iOS 26), an
  `AsyncSequence` over an `@Observable` value, instead of adding Combine back.
:::
