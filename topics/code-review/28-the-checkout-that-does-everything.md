---
title: 28 · The checkout that does everything
summary: A payment class that prices, stores, logs, calls the network and formats text — review it for SOLID and clean architecture.
minutes: 25
group: Review this PR
sources:
- Glassdoor · fintech manager rounds: 10–15 minute live code review judged on design, not only bugs | https://www.glassdoor.com/Interview/The-interview-format-was-changed-on-the-day-to-lead-with-the-code-review-instead-of-the-project-discussion-The-code-review-QTN_8942673.htm
- PCI Security Standards Council · PCI DSS — card numbers must not be stored or logged in the clear | https://www.pcisecuritystandards.org/standards/pci-dss/
- Stripe · Idempotent requests — retrying a payment without charging twice | https://docs.stripe.com/api/idempotent_requests
- Swift.org · Typed throws (SE-0413) | https://github.com/swiftlang/swift-evolution/blob/main/proposals/0413-typed-throws.md
---

*Shape: review this PR · Reported: not reported — **likely**, as fintech code reviews are judged on
maintainability, architecture, testability, error handling and separation of concerns, with SOLID and
clean architecture named as the lens · Verified: the snippet compiles in Swift 5 mode and is rejected
in Swift 6; the fix compiles in Swift 6 mode and was run against fakes, Swift 6.4*

> "This is how our checkout works today. Product wants two more payment methods next quarter. Walk
> me through what you'd change — and why it matters. You have ten minutes."

```swift
final class Analytics {
    static let shared = Analytics()
    func track(_ name: String, _ properties: [String: Any]) { /* … */ }
}

final class CheckoutManager {
    static let shared = CheckoutManager()

    var amount: Double = 0
    var lastError: String?
    var onUpdate: ((String) -> Void)?

    func pay(method: String, cardNumber: String?, completion: @escaping (Bool) -> Void) {
        if amount <= 0 { completion(false); return }

        var fee = 0.0
        switch method {
        case "card": fee = amount * 0.008
        case "link": fee = 0.25
        case "qr":   fee = 0
        default:     break
        }

        UserDefaults.standard.set(cardNumber, forKey: "lastCard")
        print("Paying \(amount) with card \(cardNumber ?? "")")

        var request = URLRequest(url: URL(string: "https://api.example.com/payments")!)
        request.httpMethod = "POST"
        request.httpBody = try? JSONSerialization.data(withJSONObject: [
            "amount": amount + fee, "method": method, "card": cardNumber ?? ""
        ])

        URLSession.shared.dataTask(with: request) { data, response, error in
            if error != nil {
                self.lastError = "Something went wrong"
                completion(false)
                return
            }
            let json = try! JSONSerialization.jsonObject(with: data!) as! [String: Any]
            let ok = json["status"] as! String == "ok"
            Analytics.shared.track("payment", ["method": method, "ok": ok])
            self.onUpdate?(ok ? "Paid \(self.amount + fee)€" : "Failed")
            completion(ok)
        }.resume()
    }
}
```

::: The key — what I expect a senior to find
**First, the ones that hurt users or the business**

1. **Card numbers stored and logged.** The full card number goes into UserDefaults (an unencrypted
   plist) and into `print`, which ends up in device logs. That breaks PCI DSS. The app should never
   hold the card number at all — it should get a token from the payment provider's SDK.
2. **Double charges.** No idempotency key. If the request times out after the server charged, a retry
   or a double tap charges again. Send one key per checkout attempt and reuse it on retry.
3. **Unknown methods are free.** `default: break` means a typo like `"Card"` is charged with no fee —
   silently. Stringly-typed input with a silent fallback.
4. **Crashes on any unexpected response.** `try!`, `data!` and two `as!` casts.
5. **Money as `Double`.** Fees and totals drift; use `Decimal`, round explicitly, keep the currency.

**Then the design — SOLID and clean architecture**

6. **Single responsibility: it does eight jobs.** Validation, fee pricing, persistence, logging,
   networking, response parsing, analytics and UI text, in one method. Each changes for a different
   reason and a different person — pricing for finance, text for design.
7. **Open/closed: adding a method means editing this function.** Product wants two more methods; each
   one touches the switch, the request body and the analytics. Model methods as a type and inject the
   fee policy, so pricing changes don't touch payment code.
8. **Dependency inversion: everything concrete.** `URLSession.shared`, `UserDefaults.standard`,
   `Analytics.shared` and its own `shared` instance. The business rule depends on infrastructure
   instead of the other way round — so nothing here can be unit tested without the network.
9. **Layers mixed.** Domain (fees), infrastructure (HTTP, JSON) and presentation (`"Paid …€"`) in one
   place. The view can't change its wording without touching payment code.
10. **Shared mutable state in a singleton.** `amount` is a global var; two checkout screens overwrite
    each other. Pass the amount in.

**Then error handling and the API shape**

11. **`Bool` loses the reason.** Declined, network down and invalid amount all become `false`.
12. **Error paths are inconsistent.** On a network error `onUpdate` is never called, so the UI shows
    nothing; `lastError` is set but nobody is told. HTTP status codes are ignored entirely.
13. **Two callbacks for one result** (`completion` and `onUpdate`) — callers can't know which to
    trust, and both fire on a background queue.
14. **Analytics takes `[String: Any]`** — untyped events, and an easy place to leak personal data later.
15. **Hard-coded URL and currency symbol.** "€" after the number is wrong for most locales.

The one-minute summary to end on: *"Three themes — it handles card data unsafely and can charge
twice; one class owns every concern so it can't be tested or extended; and errors collapse into a
Bool, so the user never learns what happened."*
:::

::: The fix
Not a rewrite to recite — a shape to point at. Each type has one reason to change.

```swift
// MARK: - Domain

struct Money: Sendable, Equatable {
    let amount: Decimal
    let currencyCode: String

    static func + (lhs: Money, rhs: Money) -> Money {
        precondition(lhs.currencyCode == rhs.currencyCode)
        return Money(amount: lhs.amount + rhs.amount, currencyCode: lhs.currencyCode)
    }
}

/// An opaque token from the payment provider's SDK. The app never sees the card number.
struct CardToken: Sendable, Equatable { let value: String }

enum PaymentMethod: Sendable, Equatable {
    case card(CardToken)
    case paymentLink
    case qrCode

    var analyticsName: String {
        switch self {
        case .card: "card"
        case .paymentLink: "link"
        case .qrCode: "qr"
        }
    }
}

enum PaymentError: Error, Equatable {
    case invalidAmount
    case declined(reason: String)
    case unavailable
}

struct ChargeRequest: Sendable, Equatable {
    let idempotencyKey: UUID
    let total: Money
    let method: PaymentMethod
}

// MARK: - Ports (what the use case needs, not how it's done)

protocol FeePolicy: Sendable {
    func fee(for amount: Money, method: PaymentMethod) -> Money
}

protocol PaymentsAPI: Sendable {
    func charge(_ request: ChargeRequest) async throws -> ChargeRequest.Outcome
}

extension ChargeRequest {
    enum Outcome: Sendable, Equatable { case approved, declined(reason: String) }
}

protocol PaymentAnalytics: Sendable {
    func paymentFinished(method: String, succeeded: Bool)
}

// MARK: - Policy

struct StandardFeePolicy: FeePolicy {
    func fee(for amount: Money, method: PaymentMethod) -> Money {
        let value: Decimal
        switch method {
        case .card:        value = amount.amount * Decimal(string: "0.008")!
        case .paymentLink: value = Decimal(string: "0.25")!
        case .qrCode:      value = 0
        }
        var unrounded = value, rounded = Decimal()
        NSDecimalRound(&rounded, &unrounded, 2, .bankers)
        return Money(amount: rounded, currencyCode: amount.currencyCode)
    }
}

// MARK: - Use case

struct PayUseCase: Sendable {
    let api: PaymentsAPI
    let fees: FeePolicy
    let analytics: PaymentAnalytics

    func callAsFunction(_ amount: Money,
                        with method: PaymentMethod,
                        idempotencyKey: UUID) async throws(PaymentError) -> Money {
        guard amount.amount > 0 else { throw .invalidAmount }
        let total = amount + fees.fee(for: amount, method: method)
        let request = ChargeRequest(idempotencyKey: idempotencyKey, total: total, method: method)

        let outcome: ChargeRequest.Outcome
        do { outcome = try await api.charge(request) }
        catch {
            analytics.paymentFinished(method: method.analyticsName, succeeded: false)
            throw .unavailable
        }

        analytics.paymentFinished(method: method.analyticsName, succeeded: outcome == .approved)
        switch outcome {
        case .approved: return total
        case .declined(let reason): throw .declined(reason: reason)
        }
    }
}

// MARK: - Presentation

@MainActor
final class CheckoutViewModel {
    enum State: Equatable { case idle, paying, paid(String), failed(String) }

    private(set) var state: State = .idle
    private let pay: PayUseCase
    private var idempotencyKey = UUID()   // one key per checkout attempt, reused on retry

    init(pay: PayUseCase) { self.pay = pay }

    func confirm(_ amount: Money, with method: PaymentMethod) async {
        guard state != .paying else { return }   // double tap does nothing
        state = .paying
        do {
            let total = try await pay(amount, with: method, idempotencyKey: idempotencyKey)
            state = .paid(total.amount.formatted(.currency(code: total.currencyCode)))
            idempotencyKey = UUID()
        } catch {
            state = .failed(Self.message(for: error))
            if error != .unavailable { idempotencyKey = UUID() }   // a confirmed failure ends the attempt
        }
    }

    private static func message(for error: PaymentError) -> String {
        switch error {
        case .invalidAmount: "Enter an amount above zero."
        case .declined(let reason): "Payment declined: \(reason)"
        case .unavailable: "We couldn't confirm the payment. Retrying is safe — you won't be charged twice."
        }
    }
}
```

What running it against fakes showed: a 0.8% card fee on €125 came out as exactly 1; a first attempt
that timed out showed the retry message, the retry succeeded with `€100.25`, and **both attempts sent
the same idempotency key**; a zero amount was rejected before any network call; and after a decline,
the next card got a new key.

Why each piece, mapped to the letter:

- **S** — `FeePolicy` prices, `PaymentsAPI` talks HTTP, `PayUseCase` holds the rule, the view model
  owns state and wording. Each changes for one reason.
- **O** — a new payment method is a new enum case: the compiler then lists every place that must
  handle it. That's *safer* than open/closed by subclassing — the closed set is the point. Pricing
  rules change by injecting a different `FeePolicy`, without touching payment code.
- **L** — any `PaymentsAPI` (real, fake, sandbox) can stand in; the use case never checks which.
- **I** — three small protocols, each with what one caller needs; analytics doesn't see the API.
- **D** — the use case depends on protocols it owns; the HTTP client, storage and analytics depend on
  it, wired once at the composition root.
- **Typed throws** — the use case can only fail in three named ways, so the view model's `switch` is
  exhaustive and every failure gets a real message.
:::

::: What I'd ask next
- *"Isn't this over-engineered for one screen?"* — The rule is cost of change. Payments change often,
  are regulated, and a bug costs money; four small types are cheap insurance. For a settings toggle,
  one view model is enough.
- *"Where does the idempotency key come from, and when does it change?"* — Created per checkout
  attempt, reused across retries, replaced only after a confirmed result.
- *"How do you test the fee rounding?"* — `StandardFeePolicy` is a pure struct: a table of amounts
  and expected fees, no fakes needed.
- *"The server says 'declined' with a code. Where does the code become text?"* — In presentation:
  the domain carries the reason, the view model turns it into words.
- *"Why not a singleton for `PayUseCase`?"* — It has no state worth sharing, and injecting it lets
  each screen get fakes in previews and tests.
:::
