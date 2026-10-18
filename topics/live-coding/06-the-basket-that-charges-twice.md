---
title: 06 · The basket that charges twice
summary: A SwiftUI basket with a Pay button, reviewed the way a payments team reviews a pull request. It doesn't build, it says €50.00 and still charges shipping, totals go stale, quantities go negative, an empty basket can be paid for, and two taps charge the card twice. Fix it, then add promotion codes, where every rule needs a question first, and test the money.
minutes: 60
group: Rounds
sources:
- Uber · iOS developer, São Paulo (2024) — "iOS specialization": code review plus a live feature | https://www.jointaro.com/interviews/companies/uber/experiences/ios-developer-sao-paulo-sao-paulo-august-1-2024-no-offer-positive-90b310a5/
- Revolut · Android and iOS loop — correctness, concurrency and tests expected | https://ophyai.com/blog/company-guides/revolut-android-ios-interview
- Apple · Decimal — base-10 numbers for money | https://developer.apple.com/documentation/foundation/decimal
- Apple · Stepper — onIncrement and onDecrement, and a nil closure disables that side | https://developer.apple.com/documentation/swiftui/stepper
- Apple · ContentUnavailableView — the empty and error states | https://developer.apple.com/documentation/swiftui/contentunavailableview
- Apple · Mutex — a Sendable lock for the test fake's records | https://developer.apple.com/documentation/synchronization/mutex
---

*Shape: C · Review it, then extend it — 60 minutes, your Xcode, screen shared, no AI assistant · Reported: Uber
São Paulo's iOS round (code review, then a live feature), with the money-correctness focus and tests that
fintech loops like Revolut's are reported to expect · Verified: Xcode 27.1, iOS 26 target, Swift 6 language
mode with main-actor default isolation. The starter fails with the two build errors below. On the iPhone 17
simulator, every runtime bug in the key was reproduced. The screenshots show the totals, and the charges are
quoted from the package's own log. The fix and the feature build with no warnings, and the six tests pass.
`tappingPayTwiceChargesOnce` fails when the in-flight guard is removed.*

**How the hour runs**

| Time | The interviewer says | You're scored on |
|---|---|---|
| 0:00–0:05 | "Get it running." | Reading the errors; not reaching for the quickest fix |
| 0:05–0:30 | "Review it like a payments PR. What do you block?" | Severity order: money first, then state, then the rest |
| 0:30–0:50 | "Product wants promo codes." | The questions you ask before writing a line |
| 0:50–1:00 | "Test the money." | Exact `Decimal` assertions, a fake that records charges |

> "This is our checkout basket. The service is a local package and it logs every charge, so you can
> see what the card would see. Get it running, then review it as if it were a PR on the payments team.
> Tell me what you'd block and why, and fix what matters."

The project is in `LiveCodingLab/Round06-Checkout`. It's modern SwiftUI: `@Observable` with `@State`,
`NavigationStack`, `List` with `ForEach` bindings, `Stepper`, `.task`, `.sheet(item:)`, currency format
styles. The bugs are the ones that survive in modern code.

```swift
// CheckoutKit/Sources/CheckoutKit/CheckoutService.swift — a package: no default isolation
public struct BasketItem: Sendable {
    public let id: String
    public let name: String
    public let unitPrice: Double        // the backend sends prices as JSON numbers
    public let quantity: Int
    // public init(…)
}

public struct Receipt: Identifiable, Sendable {
    public let id: String               // the order number
    public let amountCharged: Double
}

public struct Promotion: Sendable {
    public enum Kind: Sendable {
        case percentOff(Int)
        case amountOff(Double)
    }

    public let code: String
    public let kind: Kind
    public let minimumSubtotal: Double
}

// CheckoutError: .unknownPromotion ("This code isn't valid."), .paymentDeclined

public final class CheckoutService: Sendable {
    public init() {}

    private let charges = Mutex<[String: Receipt]>([:])     // idempotency key → receipt
    private let chargeCount = Atomic(0)
    private let logger = Logger(subsystem: "CheckoutKit", category: "payments")

    public func fetchBasket() async throws -> [BasketItem] {
        try await Task.sleep(for: .milliseconds(500))   // simulate the network
        return [
            BasketItem(id: "bottle", name: "Water bottle", unitPrice: 10.20, quantity: 1),
            BasketItem(id: "cap", name: "Running cap", unitPrice: 21.90, quantity: 1),
            BasketItem(id: "socks", name: "Running socks", unitPrice: 8.95, quantity: 2),
        ]
    }

    /// Looks up a promotion code: RUN10 (10 % off), SAVE5 (€5 off from €30), GIFT25 (€25 off).
    public func promotion(for code: String) async throws -> Promotion { ... }

    /// Charges the customer's card. A repeated `idempotencyKey` returns the first receipt and
    /// charges nothing, like Stripe's idempotent requests.
    public func charge(amount: Double, idempotencyKey: String?) async throws -> Receipt {
        if let idempotencyKey, let earlier = charges.withLock({ $0[idempotencyKey] }) {
            logger.notice("replayed \(idempotencyKey, privacy: .public): no new charge")
            return earlier
        }
        try await Task.sleep(for: .milliseconds(1200))
        let number = chargeCount.add(1, ordering: .relaxed).newValue
        let receipt = Receipt(id: "ORD-\(1000 + number)", amountCharged: amount)
        logger.notice("charge #\(number): \(amount.formatted(.currency(code: "EUR")), privacy: .public)")
        if let idempotencyKey {
            charges.withLock { $0[idempotencyKey] = receipt }
        }
        return receipt
    }
}
```

```swift
// Checkout/Checkout/BasketViewModel.swift — the target's default isolation is MainActor
import CheckoutKit
import Foundation
import Observation

@Observable
final class BasketViewModel {
    var items: [BasketItem] = []
    var subtotal: Double = 0
    var shipping: Double = 0
    var total: Double = 0
    var isPaying = false
    var receipt: Receipt?
    var errorMessage: String?

    var amountToFreeShipping: Double { 50 - subtotal }

    private let service = CheckoutService()

    func load() async {
        do {
            items = try await service.fetchBasket()
            recalculate()
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func remove(at offsets: IndexSet) {
        items.remove(atOffsets: offsets)
        recalculate()
    }

    func pay() async {
        isPaying = true
        do {
            receipt = try await service.charge(amount: total, idempotencyKey: nil)
        } catch {
            errorMessage = error.localizedDescription
        }
        isPaying = false
    }

    private func recalculate() {
        subtotal = items.reduce(0) { $0 + $1.unitPrice * Double($1.quantity) }
        shipping = subtotal >= 50 ? 0 : 4.95       // free shipping from €50
        total = subtotal + shipping
    }
}
```

```swift
// Checkout/Checkout/BasketView.swift
struct BasketView: View {
    @State private var viewModel = BasketViewModel()

    var body: some View {
        NavigationStack {
            List {
                Section {
                    ForEach($viewModel.items) { $item in
                        HStack {
                            VStack(alignment: .leading) {
                                Text(item.name)
                                Text(item.unitPrice, format: .currency(code: "EUR"))
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                            Spacer()
                            Stepper("\(item.quantity)", value: $item.quantity)
                                .fixedSize()
                        }
                    }
                    .onDelete { offsets in
                        viewModel.remove(at: offsets)
                    }
                }

                Section {
                    LabeledContent("Subtotal", value: viewModel.subtotal, format: .currency(code: "EUR"))
                    LabeledContent("Shipping", value: viewModel.shipping, format: .currency(code: "EUR"))
                    LabeledContent("Total", value: viewModel.total, format: .currency(code: "EUR"))
                        .fontWeight(.semibold)
                } footer: {
                    if viewModel.subtotal < 50 {
                        Text("Add \(viewModel.amountToFreeShipping, format: .currency(code: "EUR")) more for free shipping.")
                    }
                }

                if let errorMessage = viewModel.errorMessage {
                    Text(errorMessage)
                        .foregroundStyle(.red)
                }
            }
            .navigationTitle("Basket")
            .safeAreaInset(edge: .bottom) {
                Button {
                    Task { await viewModel.pay() }
                } label: {
                    if viewModel.isPaying {
                        ProgressView()
                            .frame(maxWidth: .infinity)
                    } else {
                        Text("Pay \(viewModel.total, format: .currency(code: "EUR"))")
                            .frame(maxWidth: .infinity)
                    }
                }
                .buttonStyle(.borderedProminent)
                .controlSize(.large)
                .padding()
            }
            .task {
                await viewModel.load()
            }
            .sheet(item: $viewModel.receipt) { receipt in
                ContentUnavailableView("Order \(receipt.id) placed",
                                       systemImage: "checkmark.circle",
                                       description: Text("We charged \(receipt.amountCharged, format: .currency(code: "EUR")).")
                )
            }
        }
    }
}
```

## Part 1 — make it run, then review it

::: A hint, if you're stuck
Both build errors are about the package's model. Before you make `quantity` a `var`, ask who should be
allowed to change a quantity, and what else has to happen when it changes. Once it runs, read the summary
out loud, line by line, and check that it adds up. Then try to break it like a customer would: tap
everything twice, go below one, delete everything, and pay anyway. Keep the console filtered on `CheckoutKit`.
:::

::: The key — what I expect a senior to find
On a payments PR I go in this order: wrong money, double money, then state, then the rest.

**It doesn't build**

1. **`initializer 'init(_:content:)' requires that 'BasketItem' conform to 'Identifiable'`.** It already has an
   `id`. Declare `Identifiable` in the package (and `Hashable`, which tests and diffing will want).
2. **`cannot assign to property: 'quantity' is a 'let' constant`**, from `Stepper(value: $item.quantity)`.
   The quick fix is `public var quantity`, and it compiles, but the binding writes straight into the
   array. Nothing recalculates, nothing checks a range, and nothing else learns that the basket changed.
   Make it `var`, but change it only through view-model methods (`increment`, `decrement`). That's how
   findings 4, 5 and 7 get fixed in one place.

**The money is wrong**

3. **"Subtotal €50.00 · Shipping €4.95 · Total €54.95", with "Add €0.00 more for free shipping."** under it.
   That's on screen with the starter basket. 10.20 + 21.90 + 2 × 8.95 is 50.00, but in `Double` it's
   49.99999999999999, so `subtotal >= 50` is false and the customer pays shipping they shouldn't. The
   formatter rounds it to "€50.00", so the screen hides the problem. Money is `Decimal`, end to end:
   in the package's model, in the API, in the view model. A `Decimal` built from a literal goes through
   `Double` first. `let price: Decimal = 3.133` gives `3.132999999999999488`. So build money from strings
   or integer cents. (`Decimal(string: "8.95")`, or `Decimal(895) / 100`.)

**The money is charged twice**

4. **Two taps on Pay, two charges.** I tapped twice. The log shows `charge #1: €54.95` and `charge #2: €54.95`,
   and the sheet shows the second order, ORD-1002. The button stays enabled while it shows a spinner, and
   `pay()` has no guard. There's also no idempotency key (`idempotencyKey: nil`), so a retry after a
   timeout, when the server already charged, also charges twice. Fix both. Put a guard in `pay()` that's
   checked and set *before* the first `await`. Two taps make two `Task`s, but both run on the main actor
   one after the other, so the second sees `.paying` and returns. Also send one key per payment attempt,
   reuse it on retry, and replace it when the basket changes.
5. **It charged the wrong amount.** Before that payment I'd tapped + on the socks. The row said 3, but the
   summary still said €50.00 / €54.95, and the card was charged €54.95. The basket was really €58.95,
   with free shipping. `subtotal`, `shipping` and `total` are stored copies, updated only in `load()` and
   `remove(at:)`. The `Stepper` binding never calls `recalculate()`. Delete the stored copies and make
   them computed from `items`. Then there's nothing to keep in sync.

**State the customer can break**

6. **Quantity goes to 0 and then −1.** The stepper has no range. After a deletion triggered a
   recalculation, the "−1 × Water bottle" took €10.20 *off* the subtotal (€16.65 for three socks and minus one
   bottle). Use `1...10`. At 1, the minus side is disabled (`Stepper` takes an optional `onDecrement`), and
   removing an item is a swipe. Ask product whether minus at 1 should remove the line instead.
7. **An empty basket can be paid for.** I deleted every row. The screen showed "Subtotal €0.00 · Shipping
   €4.95 · Pay €4.95", and Pay logged `charge #3: €4.95`. Shipping must be 0 for an empty basket, Pay must
   be disabled, and the empty basket needs its own `ContentUnavailableView`.
8. **After paying, the basket is still there.** Dismiss the receipt, and the same items can be paid for again.
   A paid order clears the basket. That's part of the payment state, not something the view should
   remember to do.

**Read the code**

9. **The service is built inside the view model.** Add a `CheckoutServing: Sendable` protocol in the package
   and inject it, so tests can count charges.
10. **Said, not coded:**
    - The client sends the amount. The server should price the basket itself and check the promo code, and
      treat the client's total as a display value. Say this even if you can't change the backend today.
    - Four separate flags (`isPaying`, `receipt`, `errorMessage`, and the stored totals) can contradict each
      other. A `PaymentState` enum can't.
    - "EUR" is hard-coded in five places. The basket should carry its currency.
    - The `Stepper` label is only a number. VoiceOver needs the item name in it.

What sinks this part: `.disabled(isPaying)` alone, with `isPaying` set inside the `Task`. That's still a
window. Calling `recalculate()` from more places instead of removing the stored totals. Rounding the
`Double` before the comparison (`(subtotal * 100).rounded() / 100 >= 50`), which fixes this basket and
leaves money as `Double`.
:::

::: The idea behind it
Money bugs come from **numbers that aren't exact** and **state that isn't the source of truth**. A `Double`
can't hold 0.10, so €50 isn't €50. A stored `total` copies `items` and then drifts from it. The Pay
button's state lives in two places, the view and a flag set too late, so a second tap gets through. The
fixes: `Decimal` everywhere, one array of items with every total computed from it, and one `PaymentState`
that `pay()` checks before it does anything. The idempotency key covers the case no client guard can:
the network failed *after* the server charged.

What "modern" means in this round:

| Use | Instead of |
|---|---|
| `Decimal`, built from strings or integer cents | `Double` for money, or `Decimal` from a float literal |
| computed `subtotal`/`total` on an `@Observable` | stored totals and a `recalculate()` to remember |
| view-model intents (`increment`, `pay`) | `$binding` into a model from another module |
| `Stepper(_:onIncrement:onDecrement:)` with a nil side | `Stepper(value:)` with no range |
| one `PaymentState` enum, checked before the first `await` | `isPaying` + `receipt` + `errorMessage` |
| an idempotency key per payment attempt | hoping the network doesn't time out |
| `ContentUnavailableView` for empty and error | a summary that shows €4.95 for nothing |
:::

::: The fix
The package: `Decimal` money, the conformances, a seam, and a required idempotency key. The other public
structs get the same treatment: `Receipt` and `Promotion` become `Hashable`, use `Decimal`, and get
public inits.

```swift
public struct BasketItem: Identifiable, Hashable, Sendable {
    public let id: String
    public let name: String
    public let unitPrice: Decimal       // money is never a Double
    public var quantity: Int

    public init(id: String, name: String, unitPrice: Decimal, quantity: Int) {
        self.id = id
        self.name = name
        self.unitPrice = unitPrice
        self.quantity = quantity
    }
}

public protocol CheckoutServing: Sendable {
    func fetchBasket() async throws -> [BasketItem]
    func promotion(for code: String) async throws -> Promotion
    func charge(amount: Decimal, idempotencyKey: String) async throws -> Receipt
}

// CheckoutService: CheckoutServing — prices as Decimal(string: "10.20")!, …;
// charge(amount: Decimal, idempotencyKey: String) always records the key.
```

The view model: computed money, intents, one payment state, a key per attempt:

```swift
import CheckoutKit
import Foundation
import Observation

@Observable
final class BasketViewModel {   // main actor: the target's default isolation
    enum LoadState: Equatable {
        case loading
        case loaded
        case failed(String)
    }

    enum PaymentState: Equatable {
        case idle
        case paying
        case paid(Receipt)
        case failed(String)
    }

    static let freeShippingThreshold: Decimal = 50
    static let shippingFee = Decimal(string: "4.95")!
    static let quantityRange = 1...10

    private(set) var loadState: LoadState = .loading
    private(set) var items: [BasketItem] = []
    private(set) var payment: PaymentState = .idle

    init(service: any CheckoutServing) {
        self.service = service
    }

    // Derived from `items` on every read, so nothing can go stale.
    var subtotal: Decimal {
        items.reduce(0) { $0 + $1.unitPrice * Decimal($1.quantity) }
    }

    var shipping: Decimal {
        items.isEmpty || subtotal >= Self.freeShippingThreshold ? 0 : Self.shippingFee
    }

    var total: Decimal { subtotal + shipping }

    var amountToFreeShipping: Decimal? {
        guard !items.isEmpty, subtotal < Self.freeShippingThreshold else { return nil }
        return Self.freeShippingThreshold - subtotal
    }

    var canPay: Bool { !items.isEmpty && payment != .paying }

    var receipt: Receipt? {
        if case .paid(let receipt) = payment { receipt } else { nil }
    }

    func load() async {
        loadState = .loading
        do {
            items = try await service.fetchBasket()
            loadState = .loaded
        } catch {
            loadState = .failed(error.localizedDescription)
        }
    }

    func canIncrement(_ item: BasketItem) -> Bool { item.quantity < Self.quantityRange.upperBound }
    func canDecrement(_ item: BasketItem) -> Bool { item.quantity > Self.quantityRange.lowerBound }

    func increment(_ id: BasketItem.ID) {
        changeQuantity(of: id, by: 1)
    }

    func decrement(_ id: BasketItem.ID) {
        changeQuantity(of: id, by: -1)
    }

    func remove(at offsets: IndexSet) {
        guard payment != .paying else { return }
        items.remove(atOffsets: offsets)
        basketChanged()
    }

    func pay() async {
        guard canPay else { return }                // a second tap while paying does nothing
        payment = .paying
        do {
            let receipt = try await service.charge(amount: total, idempotencyKey: attemptKey.uuidString)
            payment = .paid(receipt)
            items = []                              // the order is placed
            attemptKey = UUID()
        } catch {
            payment = .failed(error.localizedDescription)   // keep the key: a retry is the same attempt
        }
    }

    func dismissReceipt() {
        payment = .idle
    }

    @ObservationIgnored private let service: any CheckoutServing
    @ObservationIgnored private var attemptKey = UUID()   // one key per basket we try to pay for

    private func changeQuantity(of id: BasketItem.ID, by change: Int) {
        guard payment != .paying, let index = items.firstIndex(where: { $0.id == id }) else { return }
        let quantity = items[index].quantity + change
        guard Self.quantityRange.contains(quantity) else { return }
        items[index].quantity = quantity
        basketChanged()
    }

    /// A different basket is a different payment: it gets a new idempotency key.
    private func basketChanged() {
        attemptKey = UUID()
        if case .failed = payment { payment = .idle }
    }
}
```

The view switches on the load state, and forwards taps. It decides nothing about money:

```swift
import CheckoutKit
import SwiftUI

struct BasketView: View {
    @State private var viewModel: BasketViewModel

    init(service: any CheckoutServing = CheckoutService()) {
        _viewModel = State(initialValue: BasketViewModel(service: service))
    }

    var body: some View {
        NavigationStack {
            content
                .navigationTitle("Basket")
                .task { await viewModel.load() }
                .sheet(item: Binding(get: { viewModel.receipt },
                                     set: { _ in viewModel.dismissReceipt() })) { receipt in
                    ContentUnavailableView("Order \(receipt.id) placed",
                                           systemImage: "checkmark.circle",
                                           description: Text("We charged \(receipt.amountCharged, format: .currency(code: "EUR")).")
                    )
                }
        }
    }

    @ViewBuilder
    private var content: some View {
        switch viewModel.loadState {
        case .loading:
            ProgressView()
        case .failed(let message):
            ContentUnavailableView {
                Label("Couldn't load your basket", systemImage: "exclamationmark.triangle")
            } description: {
                Text(message)
            } actions: {
                Button("Try again") { Task { await viewModel.load() } }
            }
        case .loaded where viewModel.items.isEmpty:
            ContentUnavailableView("Your basket is empty", systemImage: "bag")
        case .loaded:
            basket
        }
    }

    private var basket: some View {
        List {
            Section {
                ForEach(viewModel.items) { item in
                    BasketRow(item: item,
                              onIncrement: viewModel.canIncrement(item) ? { viewModel.increment(item.id) } : nil,
                              onDecrement: viewModel.canDecrement(item) ? { viewModel.decrement(item.id) } : nil)
                }
                .onDelete { offsets in
                    viewModel.remove(at: offsets)
                }
            }

            Section {
                LabeledContent("Subtotal", value: viewModel.subtotal, format: .currency(code: "EUR"))
                LabeledContent("Shipping", value: viewModel.shipping, format: .currency(code: "EUR"))
                LabeledContent("Total", value: viewModel.total, format: .currency(code: "EUR"))
                    .fontWeight(.semibold)
            } footer: {
                if let missing = viewModel.amountToFreeShipping {
                    Text("Add \(missing, format: .currency(code: "EUR")) more for free shipping.")
                }
            }

            if case .failed(let message) = viewModel.payment {
                Text(message)
                    .foregroundStyle(.red)
            }
        }
        .disabled(viewModel.payment == .paying)
        .safeAreaInset(edge: .bottom) {
            Button {
                Task { await viewModel.pay() }
            } label: {
                if viewModel.payment == .paying {
                    ProgressView()
                        .frame(maxWidth: .infinity)
                } else {
                    Text("Pay \(viewModel.total, format: .currency(code: "EUR"))")
                        .frame(maxWidth: .infinity)
                }
            }
            .buttonStyle(.borderedProminent)
            .controlSize(.large)
            .disabled(!viewModel.canPay)
            .padding()
        }
    }
}

struct BasketRow: View {
    let item: BasketItem
    let onIncrement: (() -> Void)?
    let onDecrement: (() -> Void)?

    var body: some View {
        HStack {
            VStack(alignment: .leading) {
                Text(item.name)
                Text(item.unitPrice, format: .currency(code: "EUR"))
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            Spacer()
            Stepper("\(item.quantity)", onIncrement: onIncrement, onDecrement: onDecrement)
                .fixedSize()
                .accessibilityValue("\(item.quantity)")
        }
    }
}
```

On the simulator, the starter basket now reads "Subtotal €50.00 · Shipping €0.00 · Pay €50.00", and the minus
side is disabled at 1. After one + on the socks and two taps on Pay, the log shows one line,
`charge #1: €58.95`. After the receipt, the basket shows "Your basket is empty".
:::

## Part 2 — add the feature

> "Good. Product wants promo codes: a field under the basket. Some codes are a percentage, some are a
> fixed amount, and some need a minimum basket. RUN10, SAVE5 and GIFT25 exist on the backend."

::: A hint, if you're stuck
The starter basket is exactly €50, and shipping is free from €50. Apply RUN10 in your head before you
write anything. Then apply GIFT25 to a basket with only the €21.90 cap in it.
:::

::: The key — what I expect a senior to find
**The questions to ask first** — each one changes the code:

- **Does the discount come off shipping too?** No, only off the items.
- **Does free shipping use the subtotal before or after the discount?** Before. This is the trap. The
  basket is €50.00, so shipping is free. RUN10 takes off €5.00. If the threshold uses €45.00, shipping
  comes back at €4.95, and the code saves the customer five cents. Product didn't mean that, so ask.
- **Can a code make the total negative?** No. GIFT25 on a €21.90 basket takes €21.90 off, not €25, and the
  customer still pays €4.95 shipping. Nothing is "owed" back.
- **More than one code?** One per order. A new code replaces the old one.
- **The basket drops under a code's minimum after it's applied?** The code stays, takes nothing off, and
  says why: "Add €8.10 more to use SAVE5." The discount is *computed*, so it comes back when the basket
  qualifies again, with no extra code for it.
- **How is a percentage rounded?** To cents, half away from zero, on the order rather than per line. Pick a
  rule, write it down, and test it. The server must use the same rule.

**What I'm looking at while you build:**

- `discount` is another computed property over `items` and `promotion`. Part 1 made that possible. With
  stored totals, every new rule means another place to call `recalculate()`.
- Applying a code changes the amount, so it starts a new payment attempt: a new idempotency key.
- The code field states: applying (disabled), invalid (an error under it), applied (the code with Remove),
  and applied but under the minimum (the notice).
- The server checks the code again at payment time. The client's discount is only for display.
:::

::: The fix
Added to `BasketViewModel`:

```swift
private(set) var promotion: Promotion?
private(set) var promoError: String?
private(set) var isApplyingPromo = false
var promoCode = ""

/// Comes off the items only, never off shipping, and never more than the items cost.
var discount: Decimal {
    guard let promotion, subtotal >= promotion.minimumSubtotal else { return 0 }
    switch promotion.kind {
    case .percentOff(let percent):
        return (subtotal * Decimal(percent) / 100).roundedToCents
    case .amountOff(let amount):
        return min(amount, subtotal)
    }
}

/// Why an applied code isn't taking anything off right now.
var promoNotice: String? {
    guard let promotion, subtotal < promotion.minimumSubtotal else { return nil }
    let missing = (promotion.minimumSubtotal - subtotal).formatted(.currency(code: "EUR"))
    return "Add \(missing) more to use \(promotion.code)."
}

var total: Decimal { subtotal - discount + shipping }      // shipping still uses `subtotal`

/// One code per order: a new code replaces the old one.
func applyPromo() async {
    let code = promoCode.trimmingCharacters(in: .whitespaces).uppercased()
    guard !code.isEmpty, !isApplyingPromo else { return }
    isApplyingPromo = true
    defer { isApplyingPromo = false }
    do {
        promotion = try await service.promotion(for: code)
        promoError = nil
        promoCode = ""
        basketChanged()
    } catch {
        promoError = error.localizedDescription
    }
}

func removePromo() {
    promotion = nil
    basketChanged()
}
```

`pay()` also sets `promotion = nil` after a successful charge. The rounding helper:

```swift
extension Decimal {
    /// Rounded to cents, halves away from zero: 4.495 becomes 4.50.
    var roundedToCents: Decimal {
        var value = self
        var result = Decimal()
        NSDecimalRound(&result, &value, 2, .plain)
        return result
    }
}
```

In the view, a section above the summary, and a discount row in the summary:

```swift
Section {
    if let promotion = viewModel.promotion {
        LabeledContent(promotion.code) {
            Button("Remove", role: .destructive) { viewModel.removePromo() }
        }
    } else {
        HStack {
            TextField("Promo code", text: $viewModel.promoCode)
                .textInputAutocapitalization(.characters)
                .autocorrectionDisabled()
                .onSubmit { Task { await viewModel.applyPromo() } }
            Button("Apply") { Task { await viewModel.applyPromo() } }
                .disabled(viewModel.promoCode.isEmpty || viewModel.isApplyingPromo)
        }
    }
} footer: {
    if let error = viewModel.promoError {
        Text(error).foregroundStyle(.red)
    } else if let notice = viewModel.promoNotice {
        Text(notice)
    }
}
```

```swift
if viewModel.discount > 0 {
    LabeledContent("Discount", value: -viewModel.discount, format: .currency(code: "EUR"))
}
```

On the simulator, typing `run10` and tapping Apply showed "RUN10 · Remove", then "Subtotal €50.00 ·
Discount -€5.00 · Shipping €0.00 · Total €45.00", and the button said "Pay €45.00".
:::

## Part 3 — test it

> "Test the money."

::: Now write the tests
A fake that records each charge's idempotency key and can decline the first N charges. The records live in
`Mutex`, so the fake is `Sendable` without `@unchecked`. It's `nonisolated` because the target's default
isolation would otherwise put it on the main actor. The tests compare `Decimal`s exactly. That's the
point of using `Decimal`.

```swift
import CheckoutKit
import Foundation
import Synchronization
import Testing
@testable import Checkout

/// Records every charge's idempotency key, and can decline the first `declines` charges.
nonisolated final class FakeCheckout: CheckoutServing {
    let basket: [BasketItem]
    let declinesLeft: Mutex<Int>
    let chargedKeys = Mutex<[String]>([])

    init(basket: [BasketItem], declines: Int = 0) {
        self.basket = basket
        self.declinesLeft = Mutex(declines)
    }

    func fetchBasket() async throws -> [BasketItem] { basket }

    func promotion(for code: String) async throws -> Promotion {
        switch code {
        case "RUN10": Promotion(code: code, kind: .percentOff(10), minimumSubtotal: 0)
        case "GIFT25": Promotion(code: code, kind: .amountOff(25), minimumSubtotal: 0)
        default: throw CheckoutError.unknownPromotion
        }
    }

    func charge(amount: Decimal, idempotencyKey: String) async throws -> Receipt {
        chargedKeys.withLock { $0.append(idempotencyKey) }
        try await Task.sleep(for: .milliseconds(50))
        let declined = declinesLeft.withLock { left in
            defer { left = max(0, left - 1) }
            return left > 0
        }
        if declined { throw CheckoutError.paymentDeclined }
        return Receipt(id: "ORD-1", amountCharged: amount)
    }
}

private func item(_ id: String, _ price: String, quantity: Int = 1) -> BasketItem {
    BasketItem(id: id, name: id, unitPrice: Decimal(string: price)!, quantity: quantity)
}

struct BasketViewModelTests {
    let fiftyEuros = [item("bottle", "10.20"), item("cap", "21.90"), item("socks", "8.95", quantity: 2)]

    @Test func fiftyEurosIsExactlyFiftyAndShipsFree() async {
        let viewModel = BasketViewModel(service: FakeCheckout(basket: fiftyEuros))
        await viewModel.load()
        #expect(viewModel.subtotal == 50)
        #expect(viewModel.shipping == 0)
        #expect(viewModel.total == 50)
    }

    @Test func quantityStaysBetweenOneAndTen() async {
        let viewModel = BasketViewModel(service: FakeCheckout(basket: [item("cap", "21.90")]))
        await viewModel.load()
        viewModel.decrement("cap")
        #expect(viewModel.items.first?.quantity == 1)
        for _ in 0..<12 { viewModel.increment("cap") }
        #expect(viewModel.items.first?.quantity == 10)
    }

    @Test func tappingPayTwiceChargesOnce() async {
        let service = FakeCheckout(basket: fiftyEuros)
        let viewModel = BasketViewModel(service: service)
        await viewModel.load()
        async let first: Void = viewModel.pay()
        async let second: Void = viewModel.pay()
        _ = await (first, second)
        #expect(service.chargedKeys.withLock { $0.count } == 1)
    }

    @Test func aRetryAfterADeclineReusesTheIdempotencyKey() async {
        let service = FakeCheckout(basket: fiftyEuros, declines: 1)
        let viewModel = BasketViewModel(service: service)
        await viewModel.load()
        await viewModel.pay()
        #expect(viewModel.payment == .failed("Your bank declined the payment."))
        await viewModel.pay()
        let keys = service.chargedKeys.withLock { $0 }
        #expect(keys.count == 2)
        #expect(keys[0] == keys[1])
        #expect(viewModel.receipt?.amountCharged == 50)
    }

    @Test func aPercentCodeComesOffTheItemsAndKeepsFreeShipping() async {
        let viewModel = BasketViewModel(service: FakeCheckout(basket: fiftyEuros))
        await viewModel.load()
        viewModel.promoCode = "run10"
        await viewModel.applyPromo()
        #expect(viewModel.discount == 5)
        #expect(viewModel.shipping == 0)          // the threshold uses the subtotal before the discount
        #expect(viewModel.total == 45)
    }

    @Test func aFixedCodeNeverMakesTheTotalNegative() async {
        let viewModel = BasketViewModel(service: FakeCheckout(basket: [item("cap", "21.90")]))
        await viewModel.load()
        viewModel.promoCode = "GIFT25"
        await viewModel.applyPromo()
        #expect(viewModel.discount == Decimal(string: "21.90")!)
        #expect(viewModel.total == Decimal(string: "4.95")!)   // shipping is still paid
    }
}
```

`Receipt` needs the public init from Part 1. A public struct gets no public memberwise init, so without it
the fake can't build a receipt: *"'Receipt' initializer is inaccessible due to 'internal' protection level"*.

I removed the `guard canPay` line and ran the tests again: `tappingPayTwiceChargesOnce` failed. Two
`async let`s are the closest a unit test gets to a double tap. Both calls run on the main actor, so the test
proves the guard is set before the first suspension point.
:::

::: What I'd ask next
- **"The app is killed while the payment is in flight."** The key lives only in memory, so a relaunch makes
  a new one. Persist the attempt (key + basket snapshot) before charging. On launch, ask the server
  for that key's status before you offer Pay again.
- **"Prices change while the basket is open."** The server rejects the charge with the new total. Show what
  changed and ask again, never charge silently. This is why the amount the client sends is only a check.
- **"Show prices in yen and in dinars."** Currencies have different minor units (0 for JPY, 3 for KWD). Carry
  the currency on the basket, round to its minor units, and format with its code. Don't hard-code
  `roundedToCents`.
- **"The promo field should check as you type."** Debounce with `.task(id: viewModel.promoCode)` and a short
  `Task.sleep`. The previous request is cancelled when the text changes, so a slow answer for "RUN" can't
  overwrite "RUN10". Still apply only on submit.
- **"Apple Pay."** `PayWithApplePayButton` and a `PKPaymentRequest` built from the same `Decimal` lines. The
  summary items must add up to the total exactly, which is easy now, because nothing is a `Double`.
:::
