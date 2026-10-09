---
title: 23 · The presenter that holds the view
summary: An MVP orders screen — a view controller, a presenter and a view protocol — that leaks, updates the table off the main thread and hides its business rule in didSelect. Review it, fix it without leaving MVP, and write the classic presenter tests.
minutes: 20
group: Review this PR
sources:
- Swift Book · Automatic Reference Counting — strong reference cycles between class instances | https://docs.swift.org/swift-book/documentation/the-swift-programming-language/automaticreferencecounting/
- Martin Fowler · Passive View — the view as a thin, dumb layer the presenter drives | https://martinfowler.com/eaaDev/PassiveScreen.html
- Apple · MainActor | https://developer.apple.com/documentation/swift/mainactor
- Apple · DateFormatter — creating formatters is expensive; use the user's locale | https://developer.apple.com/documentation/foundation/dateformatter
---

*Shape: review this PR · Reported: a common senior-round topic; no specific company report found ·
Verified: the snippet is rejected in Swift 6 mode (two isolation errors); the fix's view controller
typechecks against the iOS SDK; the presenter's tests ran on macOS with Swift 6.4*

> "Our orders screen, MVP: a view controller, a presenter, a view protocol. QA says the list
> sometimes stays empty forever, memory grows each time you open the screen, and an order placed at
> eleven last night says 'Today'. `OrderService` calls back on a background queue. Review it."

```swift
import UIKit

struct Order {
    let id: String
    let total: Double
    let placedAt: Date
    let isDelivered: Bool
}

struct OrderRow {
    let title: String
    let subtitle: String
    let color: UIColor
}

protocol OrdersView {
    func show(rows: [OrderRow])
}

final class OrdersPresenter {
    var view: OrdersView?
    private var orders: [Order] = []

    func viewDidLoad() {
        OrderService.shared.fetchOrders { result in
            switch result {
            case .success(let orders):
                self.orders = orders
                self.view?.show(rows: orders.map(self.makeRow))
            case .failure:
                break
            }
        }
    }

    func order(at index: Int) -> Order {
        orders[index]
    }

    private func makeRow(_ order: Order) -> OrderRow {
        let formatter = DateFormatter()
        formatter.dateFormat = "dd/MM/yyyy"
        let days = Calendar.current.dateComponents([.day], from: order.placedAt, to: Date()).day!
        return OrderRow(
            title: "Order " + order.id + " - " + String(order.total) + "€",
            subtitle: days < 1 ? "Today" : formatter.string(from: order.placedAt),
            color: order.isDelivered ? .systemGreen : .systemOrange
        )
    }
}

final class OrdersViewController: UITableViewController, OrdersView {
    let presenter = OrdersPresenter()
    private var rows: [OrderRow] = []

    override func viewDidLoad() {
        super.viewDidLoad()
        presenter.view = self
        presenter.viewDidLoad()
    }

    func show(rows: [OrderRow]) {
        self.rows = rows
        tableView.reloadData()
    }

    override func tableView(_ tableView: UITableView, numberOfRowsInSection section: Int) -> Int {
        rows.count
    }

    override func tableView(_ tableView: UITableView, cellForRowAt indexPath: IndexPath) -> UITableViewCell {
        let cell = tableView.dequeueReusableCell(withIdentifier: "OrderCell")!
        cell.textLabel?.text = rows[indexPath.row].title
        cell.detailTextLabel?.text = rows[indexPath.row].subtitle
        cell.textLabel?.textColor = rows[indexPath.row].color
        return cell
    }

    override func tableView(_ tableView: UITableView, didSelectRowAt indexPath: IndexPath) {
        let order = presenter.order(at: indexPath.row)
        if order.isDelivered && Date().timeIntervalSince(order.placedAt) < 30 * 24 * 3600 {
            let returnScreen = ReturnViewController()
            returnScreen.order = order
            navigationController?.pushViewController(returnScreen, animated: true)
        } else {
            let alert = UIAlertController(title: "Not returnable", message: nil, preferredStyle: .alert)
            alert.addAction(UIAlertAction(title: "OK", style: .default))
            present(alert, animated: true)
        }
    }
}
```

In Swift 5 mode it compiles. With `OrderService`'s completion declared `@Sendable` — as a
background callback should be — Swift 6 rejects it with two errors: the controller's conformance
to `OrdersView` "crosses into main actor-isolated code", and the presenter is captured in a
`@Sendable` closure (checked). Both point at the same bug, key 2.

::: A hint, if you're stuck
- Draw the arrows between the controller and the presenter. Can you write `weak` in front of `view`?
- Which thread runs the `fetchOrders` closure, and what does it end up calling?
- What does the user see if `fetchOrders` fails?
- Which of these lines could you test without a simulator? Which need the real clock?
:::

::: The key — what I expect a senior to find
1. **`dequeueReusableCell(withIdentifier:)!` crashes.** That older method returns `nil` when no
   cell is registered for the identifier, and `!` turns that into a crash. Use
   `dequeueReusableCell(withIdentifier:for:)`, which always returns a cell. (The `.day!` is safe —
   asking for `.day` always fills it — but say why, or use `?? 0`.)
2. **The table is reloaded off the main thread.** The service calls back on a background queue, and
   the presenter calls `view?.show`, which calls `reloadData()`, right there. UIKit off main is
   undefined behaviour: missing rows, crashes, "the list stays empty". Hop to main in the presenter,
   and mark the presenter and the view protocol `@MainActor`.
3. **The presenter holds the view strongly: a retain cycle.** The controller owns the presenter, and
   `presenter.view = self` points back. Neither is ever freed — the memory growth. `view` should be
   `weak`, but `weak` won't compile until the protocol says "classes only": add `: AnyObject`.
4. **The fetch closure keeps the presenter alive.** It captures `self` strongly, so a slow request
   keeps the presenter (and, today, the whole screen) alive until it answers. `[weak self]`.
5. **No loading or error state.** `case .failure: break` — the user gets a blank table forever,
   with no message and no way to retry. That's QA's "stays empty". Tell the view.
6. **"Today" means "less than 24 hours".** `dateComponents(.day) < 1` counts whole 24-hour
   periods, so an order from 23:00 yesterday says "Today" at 09:00. Compare calendar days:
   `Calendar.isDate(_:inSameDayAs:)`.
7. **Money and dates are built for one country.** `String(12.5) + "€"` gives "12.5€" — no cents,
   and the symbol in the wrong place for most locales. `"dd/MM/yyyy"` ignores the user's region; an
   American reads 03/04 as March. None of it is localized. Use `formatted(.currency(code:))`, a
   `dateStyle`, and `String(localized:)`.
8. **The business rule lives in `didSelect`.** "Delivered and less than 30 days old" is product
   logic, in the one class you can't unit-test easily. And `order(at:)` hands the model to the
   view. In MVP the view reports the tap; the presenter decides and tells the view what to show.
9. **The presenter imports UIKit and builds a `UIColor`.** Then it only compiles for iOS, and its
   tests need a simulator. Strings are the presenter's job; colour is the view's. Pass a fact
   (`isDelivered`) and let the view pick the colour.
10. **`Date()` read inline, twice.** "Today" and "30 days" can't be tested without waiting a day.
    Inject the clock: `now: () -> Date = Date.init`.
11. **A singleton inside the presenter.** `OrderService.shared` can't be replaced, so no test can
    give it a failure or a slow reply. Inject it behind a small protocol.
12. **A `DateFormatter` per row.** Creating formatters is expensive and this runs for every row on
    every reload. Make one and keep it.
13. **`30 * 24 * 3600` isn't 30 days.** Days around a daylight-saving change are 23 or 25 hours.
    Let `Calendar` count days.
14. **The controller creates its presenter.** `let presenter = OrdersPresenter()` means the screen
    can't be built with a fake; pass the presenter in when you create the screen.
15. **`textLabel` is the old cell API.** Since iOS 14, `UIListContentConfiguration` is the way —
    style, not a blocker.
:::

::: The idea behind it
**MVP** splits a screen into three parts. The **view** (the view controller, plus a protocol that
describes it) is dumb: it draws what it's told and reports what the user did. The **presenter**
holds the screen's logic: it fetches data, decides what to show, formats it, and calls the view.
The **model** is the data and services. The point of the split is that the presenter is plain
Swift: you can test every decision with a fake view, without UIKit.

That only works if the arrows point the right way. The controller *owns* the presenter (a strong
reference: it must stay alive as long as the screen does). The presenter only *talks to* the view,
so its reference must be `weak` — otherwise each holds the other up and neither is ever freed. A
`weak` reference only works on objects of a class, which is why the view protocol needs
`: AnyObject`, a promise that only classes conform.

The second rule is the thread. A service can reply on any thread, but the view is UIKit, and UIKit
lives on the main thread. The presenter is the border: it takes the reply, moves to main, and only
then talks to the view. `@MainActor` on the presenter and the protocol lets the compiler check that.

Think of a newsreader and a producer. The producer (presenter) gathers the stories and decides the
running order; the newsreader (view) reads what's on the autocue. The newsreader doesn't decide
which story is newsworthy — and the producer doesn't go on camera.
:::

::: The fix
The presenter, with the changed lines marked:

```swift
import Foundation                                             // key 9: no UIKit

struct OrderRow: Equatable {
    let title: String
    let subtitle: String
    let isDelivered: Bool                                     // key 9: the view picks the colour
}

@MainActor
protocol OrdersView: AnyObject {                              // key 2, 3
    func show(rows: [OrderRow])
    func showLoading(_ isLoading: Bool)                       // key 5
    func showMessage(_ message: String)                       // key 5, 8
    func showReturn(for order: Order)                         // key 8
}

protocol OrderFetching: Sendable {                            // key 11: the seam
    func fetchOrders(completion: @escaping @Sendable (Result<[Order], Error>) -> Void)
}

extension OrderService: OrderFetching {}

@MainActor
final class OrdersPresenter {
    weak var view: OrdersView?                                // key 3
    private var orders: [Order] = []
    private let service: OrderFetching
    private let now: () -> Date                               // key 10
    private let formatter: DateFormatter = {                  // key 7, 12
        let formatter = DateFormatter()
        formatter.dateStyle = .medium
        return formatter
    }()

    init(service: OrderFetching = OrderService.shared, now: @escaping () -> Date = Date.init) {
        self.service = service
        self.now = now
    }

    func viewDidLoad() {
        view?.showLoading(true)
        service.fetchOrders { [weak self] result in           // key 4
            DispatchQueue.main.async {                        // key 2
                guard let self else { return }
                self.view?.showLoading(false)
                switch result {
                case .success(let orders):
                    self.orders = orders
                    self.view?.show(rows: orders.map(self.makeRow))
                case .failure:
                    self.view?.showMessage(String(localized: "We couldn't load your orders."))
                }
            }
        }
    }

    func didSelectRow(at index: Int) {                        // key 8: the rule lives here now
        guard orders.indices.contains(index) else { return }
        let order = orders[index]
        let days = Calendar.current.dateComponents([.day], from: order.placedAt, to: now()).day ?? .max
        if order.isDelivered && days < 30 {                   // key 13
            view?.showReturn(for: order)
        } else {
            view?.showMessage(String(localized: "This order can't be returned."))
        }
    }

    private func makeRow(_ order: Order) -> OrderRow {
        let isToday = Calendar.current.isDate(order.placedAt, inSameDayAs: now())   // key 6
        return OrderRow(
            title: String(localized: "Order \(order.id) · \(order.total.formatted(.currency(code: "EUR")))"),
            subtitle: isToday ? String(localized: "Today") : formatter.string(from: order.placedAt),
            isDelivered: order.isDelivered
        )
    }
}
```

The view controller — only what changed:

```swift
final class OrdersViewController: UITableViewController, OrdersView {
    // presenter, rows, viewDidLoad, show(rows:) and numberOfRows are unchanged

    func showLoading(_ isLoading: Bool) {
        if isLoading { refreshControl?.beginRefreshing() } else { refreshControl?.endRefreshing() }
    }

    func showMessage(_ message: String) {
        let alert = UIAlertController(title: nil, message: message, preferredStyle: .alert)
        alert.addAction(UIAlertAction(title: String(localized: "OK"), style: .default))
        present(alert, animated: true)
    }

    func showReturn(for order: Order) {
        let returnScreen = ReturnViewController()
        returnScreen.order = order
        navigationController?.pushViewController(returnScreen, animated: true)
    }

    override func tableView(_ tableView: UITableView, cellForRowAt indexPath: IndexPath) -> UITableViewCell {
        let cell = tableView.dequeueReusableCell(withIdentifier: "OrderCell", for: indexPath)   // key 1
        let row = rows[indexPath.row]
        cell.textLabel?.text = row.title
        cell.detailTextLabel?.text = row.subtitle
        cell.textLabel?.textColor = row.isDelivered ? .systemGreen : .systemOrange              // key 9
        return cell
    }

    override func tableView(_ tableView: UITableView, didSelectRowAt indexPath: IndexPath) {
        presenter.didSelectRow(at: indexPath.row)                                               // key 8
    }
}
```

**Said out loud, not coded:** inject the presenter into the controller through `init` (key 14);
`UIListContentConfiguration` cells (key 15); `Decimal` for money; a retry button instead of an
alert; `async`/`await` in the service, which would let the presenter `await` on the main actor
instead of hopping with `DispatchQueue`; a router object for navigation once there's more than
one destination.

Why each piece:

- **Two init parameters with defaults** — the service protocol and the clock. Both exist only so
  the tests can control them; no call site changes.
- **`showMessage` instead of `showNotReturnable` and `showError`** — the presenter owns the words,
  the view owns the alert. One method covers both.
- **The hop to main is in the presenter, not the view.** The view stays dumb, and with
  `@MainActor` on both, the compiler now refuses a call from the wrong thread.
:::

::: Now write the tests
> "Good. Now show me that the presenter works — without a simulator."

**What I'd test, and why**

1. **The presenter doesn't keep its view alive** — the retain cycle. Give it a view, drop the
   view, and a weak reference must be `nil`.
2. **Rows reach the view on the main thread** — the service replies from a background queue, like
   the real one, and every call to the view must arrive on main, in order: loading on, loading off,
   rows.
3. **A failure stops loading and shows a message** — the "stays empty forever" bug.
4. **Only recent, delivered orders can be returned** — the rule moved out of `didSelect`. With the
   clock fixed, 10 days is returnable, 40 days isn't, not delivered isn't, and a stale index does
   nothing.

This is the classic MVP test: a **spy** for the view and a **fake** for the service. A spy is a
stand-in that records what it was told; a fake is a working stand-in with canned answers. The
presenter imports only Foundation now, so these run on the Mac with `swift test` — no simulator.
The view controller has no logic left to test; it's checked by hand.

```swift
import Foundation
import Testing

// A spy: the view the presenter talks to. It records what it was told, nothing more.
@MainActor
final class OrdersViewSpy: OrdersView {
    enum Call: Equatable {
        case loading(Bool), rows([OrderRow]), message(String), returnFor(String)
    }
    private(set) var calls: [Call] = []
    private(set) var everyCallOnMain = true

    func show(rows: [OrderRow]) { record(.rows(rows)) }
    func showLoading(_ isLoading: Bool) { record(.loading(isLoading)) }
    func showMessage(_ message: String) { record(.message(message)) }
    func showReturn(for order: Order) { record(.returnFor(order.id)) }

    private func record(_ call: Call) {
        everyCallOnMain = everyCallOnMain && Thread.isMainThread
        calls.append(call)
    }
}

// A fake service: replies from a background queue, like the real one.
final class FakeOrderService: OrderFetching {
    let result: Result<[Order], Error>
    init(result: Result<[Order], Error>) { self.result = result }

    func fetchOrders(completion: @escaping @Sendable (Result<[Order], Error>) -> Void) {
        let result = result
        DispatchQueue.global().async { completion(result) }
    }
}

/// Gives the main queue turns until `condition` holds. Bounded by a count, not a clock.
@MainActor
func waitUntil(maxYields: Int = 1_000, _ condition: () -> Bool) async -> Bool {
    for _ in 0..<maxYields {
        if condition() { return true }
        await Task.yield()
    }
    return condition()
}

@MainActor
struct OrdersPresenterTests {
    let now = Date(timeIntervalSince1970: 1_790_000_000)       // a fixed "now"

    func order(_ id: String, daysAgo: Double, delivered: Bool = true) -> Order {
        Order(id: id, total: 12.5, placedAt: now.addingTimeInterval(-daysAgo * 86_400), isDelivered: delivered)
    }

    @Test func presenterDoesNotKeepItsViewAlive() {
        let presenter = OrdersPresenter(service: FakeOrderService(result: .success([])))
        weak var weakView: OrdersViewSpy?
        do {
            let view = OrdersViewSpy()
            presenter.view = view
            weakView = view
        }
        #expect(weakView == nil)
    }

    @Test func rowsReachTheViewOnTheMainThread() async {
        let view = OrdersViewSpy()
        let presenter = OrdersPresenter(service: FakeOrderService(result: .success([order("A1", daysAgo: 3)])),
                                        now: { self.now })
        presenter.view = view

        presenter.viewDidLoad()

        #expect(await waitUntil { view.calls.count == 3 })
        #expect(view.everyCallOnMain)
        guard case .rows(let rows) = view.calls.last else {
            Issue.record("Expected rows, got \(view.calls)")
            return
        }
        #expect(view.calls.prefix(2) == [.loading(true), .loading(false)])
        #expect(rows.map(\.isDelivered) == [true])
        #expect(rows.first?.subtitle != "Today")
    }

    @Test func failureStopsLoadingAndShowsAMessage() async {
        let view = OrdersViewSpy()
        let presenter = OrdersPresenter(service: FakeOrderService(result: .failure(URLError(.notConnectedToInternet))))
        presenter.view = view

        presenter.viewDidLoad()

        #expect(await waitUntil { view.calls.count == 3 })
        #expect(view.calls == [.loading(true), .loading(false), .message("We couldn't load your orders.")])
    }

    @Test func onlyRecentDeliveredOrdersCanBeReturned() async {
        let view = OrdersViewSpy()
        let orders = [order("recent", daysAgo: 10), order("old", daysAgo: 40), order("onTheWay", daysAgo: 2, delivered: false)]
        let presenter = OrdersPresenter(service: FakeOrderService(result: .success(orders)), now: { self.now })
        presenter.view = view
        presenter.viewDidLoad()
        #expect(await waitUntil { view.calls.count == 3 })

        presenter.didSelectRow(at: 0)
        presenter.didSelectRow(at: 1)
        presenter.didSelectRow(at: 2)
        presenter.didSelectRow(at: 9)                          // a stale index does nothing

        #expect(view.calls.suffix(3) == [
            .returnFor("recent"),
            .message("This order can't be returned."),
            .message("This order can't be returned."),
        ])
    }
}
```

Ran with Swift 6.4: 4 tests, all passed.
:::

::: What I'd ask next
- *"MVP or MVVM — what's the difference?"* — In MVP the presenter *calls* the view through a
  protocol ("show these rows"). In MVVM the view model *exposes state* and the view observes it
  (Combine, `@Observable`). Same goal — logic out of the view — different direction of the arrow.
- *"Why `weak` and not `unowned` for `view`?"* — The presenter could outlive the view: a request
  can answer after the screen is gone. `weak` becomes `nil`; `unowned` would crash.
- *"Where does navigation go as the app grows?"* — Behind a router or coordinator the presenter
  calls (`router.showReturn(for:)`), so the presenter decides *that* we navigate and the router
  decides *how*.
- *"Would you test the view controller?"* — Only that it forwards: a tap calls
  `didSelectRow(at:)`, and `show(rows:)` fills the table. With a passive view there's little else;
  a snapshot test covers how it looks.
- *"How would `async`/`await` change this?"* — `func viewDidLoad() async` on a `@MainActor`
  presenter: `let orders = try await service.orders()` resumes on main, so the `DispatchQueue` hop
  and `[weak self]` dance go away; cancel the task when the screen disappears.
:::
