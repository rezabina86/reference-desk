---
title: 29 · The means of payment that never loads
summary: A "clean architecture" use case that fetches a member's card — layered on paper, but it hangs on two paths, imports UIKit into the domain and builds its own dependencies. Review it.
minutes: 20
group: Review this PR
sources:
- Robert C. Martin · The Clean Architecture — the dependency rule: source code points only inwards | https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html
- Apple · UIImage init(named:) — returns nil when no image with that name is found | https://developer.apple.com/documentation/uikit/uiimage/init(named:)
- Apple · Result — one value that is either a success or a failure | https://developer.apple.com/documentation/swift/result
- Apple · Swift Testing — expecting a thrown error with #expect(throws:) | https://developer.apple.com/documentation/testing/testing-for-errors-in-swift-code
---

*Shape: review this PR · Reported: a European fintech's Payments team, 2026 — 10–15 minutes of live
review after a behavioural round, judged on SOLID, clean architecture, testability and error handling
· Verified: the snippet compiles clean in Swift 5 and Swift 6 mode for iOS; the original was run
through its dead ends against stub services; the fix and its four tests run with Swift 6.4*

> "This is the domain layer behind our means-of-payment screen. The presenter and view controller
> exist, but you don't need them. Walk me through what you'd change — and why it matters."

```swift
// MARK: - PRESENTATION LAYER (Using MVP)

// PaymentMethodViewController
// MeansOfPaymentPresenter

// MARK: - DOMAIN LAYER

import UIKit

class MeansOfPaymentEntity {
    var membership: Membership?
    var card: Card?

    var cardIcon: UIImage! {
        switch card?.cardLevel {
        case .standard:
            return UIImage(named: "ic_card_standard")
        default:
            return UIImage(named: "ic_card_plus")
        }
    }
}

class CardUseCase {
    // MARK: - Properties
    var cardService = CardServiceImpl()
    var membershipService = MembershipServiceImpl()
    var analytics = AnalyticsImpl()

    // MARK: - Fetch
    func meansOfPayment(userId: String?,
                        completion: @escaping (MeansOfPaymentEntity?, Error?) -> Void) {
        analytics.track(event: "did_show_meansOfPayment_screen")
        if let userId = userId {
            membershipService.membership(userId: userId) { membership, error in
                if let error = error {
                    completion(nil, error)
                    return
                }
                if let membershipId = membership?.id {
                    self.cardService.card(membershipId: membershipId) { card, error in
                        if let error = error {
                            completion(nil, error)
                            return
                        }

                        let meansOfPaymentEntity = MeansOfPaymentEntity()
                        meansOfPaymentEntity.card = card
                        meansOfPaymentEntity.membership = membership
                        completion(meansOfPaymentEntity, nil)
                    }
                }
            }
        }
    }
}


// MARK: - DATA LAYER

// MARK: Data
// Membership and Card are Data model

enum CardLevel {
    case standard
    case plus
}

class Card {
    var id: String?
    var name: String?
    var cardLevel: CardLevel?
}

class Membership {
    var id: String?
}

// MARK: Service

protocol CardService {
    func card(membershipId: String,
              completion: @escaping (Card?, Error?) -> Void)
}

protocol MembershipService {
    func membership(userId: String,
                    completion: @escaping (Membership?, Error?) -> Void)
}

// MARK: - Third Party

protocol Analytics {
    func track(event: String)
}
```

::: A hint, if you're stuck
- Follow `completion`. Count every path through `meansOfPayment` and ask, for each one: *is it
  called?* Then ask the same of the spinner on the screen.
- The `// MARK:` comments promise layers. Read each `import` and each type a layer mentions, and ask
  which way the arrows point.
- The service protocols exist. Who uses them?
- `card?.cardLevel` is optional. What does the `default:` branch catch besides `.plus`?
:::

::: The key — what I expect a senior to find
The compiler says nothing — it builds clean in Swift 5 *and* Swift 6 mode. Every finding is about
behaviour and design, which is exactly what this round is for. By severity:

**First, what the user feels**

1. **Two paths never call `completion`: the screen loads forever.** If `userId` is `nil`, or the
   membership comes back without an `id` (and without an error), the function just ends. No result,
   no error — the presenter's spinner never stops (run: both paths delivered *zero* callbacks).
   Every path through an async function must call its completion exactly once.
2. **`(Entity?, Error?)` allows nonsense.** Four combinations, two of them illegal: both `nil`, or
   both set. The snippet already produces one: a card service that answers `(nil, nil)` turns into a
   "success" entity with no card (run: `entity=true card=false error=false`). Use
   `Result<MeansOfPaymentEntity, Error>` — one value, success *or* failure.
3. **The icon lies when there's no card.** `switch card?.cardLevel` with `default:` sends `nil` — and
   any level added later, say `.metal` — to the Plus icon. A user with no card sees a Plus card. Switch
   exhaustively over the non-optional level, so the compiler flags a new case.
4. **`UIImage!` is a crash in waiting.** `UIImage(named:)` returns `nil` when the asset is missing or
   renamed, and the implicitly unwrapped return turns that into a crash wherever it's read.

**Then the architecture — SOLID and the dependency rule**

5. **The domain imports UIKit.** An entity that returns a `UIImage` and knows asset names is
   presentation code living in the domain. The dependency rule says inner layers know nothing about
   outer ones. Map `cardLevel` to an image in the presenter; the domain stays pure Swift, testable
   on any platform without a simulator.
6. **Dependency inversion, half done.** `CardService` and `MembershipService` are protocols — and the
   use case ignores them and builds `CardServiceImpl()`, `MembershipServiceImpl()` and
   `AnalyticsImpl()` itself. That's the whole testability problem in three lines: no test can make
   the membership call fail. Inject the protocols through `init`. The seam already exists; it's just
   not used.
7. **Analytics in the use case: wrong place, wrong moment.** `did_show_meansOfPayment_screen` is a
   screen event, so it belongs to the presenter (on appear). Here it fires on every *fetch* — every
   retry or refresh — and even when there's no user and nothing is shown (run: it fired on all three
   failed paths). Single responsibility: fetching doesn't also report screen views.
8. **The domain depends on data models.** `MeansOfPaymentEntity` holds `Membership` and `Card`,
   which the snippet itself labels *data* models. Clean architecture points the other way: the
   domain owns its types, the data layer maps DTOs into them. Say it, and judge whether it's worth it
   for two small types.
9. **Everything is optional and mutable.** `id: String?` — an id that can be missing is how the
   silent path in finding 1 exists. An entity built with `MeansOfPaymentEntity()` then filled in can
   be half-empty forever. Make entities structs with non-optional `let`s, built complete or not at
   all.
10. **`userId: String?` pushes a question into the wrong layer.** Why would a signed-out screen ask
    for means of payment? Make it `String` and let the caller decide what "not signed in" means.

**Then the API shape and naming**

11. **Errors leave untyped.** The presenter gets a raw `Error` and can't tell "no membership" (a
    normal state for some users? ask the PM) from "network down". Name the dead ends.
12. **`CardUseCase` doesn't say what it does.** It fetches a member's means of payment —
    `GetMeansOfPaymentUseCase`. The screen is `PaymentMethodViewController`, the presenter
    `MeansOfPaymentPresenter`: one concept, two names. Pick one.
13. **Classes that should be `final`, properties that should be `private`.** `var cardService` is
    publicly replaceable after init — the opposite of injection.
14. **Which thread does `completion` run on?** Nothing says. The presenter will update UI with it.
    Document it, or hop to main in the presenter.

**What's right — say it:** the two calls are correctly sequential (the card needs the membership
id), errors from each service are propagated, and the layers *exist*. This is a codebase that
meant well; the review is about making it keep its promises.

The one-minute summary to end on: *"Two paths never call back, so the screen can spin forever; the
domain reaches into UIKit and builds its own services, so the protocols that would make it testable
go unused; and the result type lets impossible states through — fix those three and the rest is
naming."*
:::

::: The idea behind it
**An async function makes a promise: "I will call you back exactly once."** With completion
handlers, the compiler doesn't check it. Every `if let` without an `else`, every early `return`, is
a path where the promise can quietly break. Two habits keep it: turn each `if let` into a
`guard … else { completion(.failure(…)); return }`, and use `Result`, so "success with nothing" and
"failure with a value" can't be written at all. (With `async throws` the compiler *does* check it —
every path must return or throw. That's the strongest reason to migrate.)

**Clean architecture is mostly one rule: dependencies point inwards.** Picture three rings: data on
the outside, presentation beside it, the domain in the middle. The domain is plain Swift that
describes the business — "a member has a membership and a card". It must not know about `UIImage`,
asset names, analytics SDKs or `…Impl` classes, because then a change in any of them reaches the
business logic, and testing the business logic needs all of them.

**The protocols are how the arrows turn around.** The domain says "I need something that can fetch
a card" (`CardService`); the data layer provides it; someone outside both — the composition root —
plugs them together. Here the protocols were written, then bypassed by `= CardServiceImpl()`. It's
like installing a power socket and then wiring the lamp straight into the wall: the socket is there,
but you still can't plug in anything else.
:::

::: The fix
Keep completion handlers — that's the snippet's shape. Change only what the findings need. The seam
is the two protocols the code already had; no new protocol is added.

```swift
import Foundation                                       // key 5: no UIKit in the domain

struct MeansOfPaymentEntity {                           // key 9: a value, built complete
    let membership: Membership
    let card: Card
}

enum MeansOfPaymentError: Error, Equatable {            // keys 1, 11: every dead end has a name
    case missingUser
    case noMembership
    case noCard
}

final class CardUseCase {
    private let cardService: CardService                // key 6: the protocols that were
    private let membershipService: MembershipService    // already there, now injected

    init(cardService: CardService, membershipService: MembershipService) {
        self.cardService = cardService
        self.membershipService = membershipService
    }

    func meansOfPayment(userId: String?,
                        completion: @escaping (Result<MeansOfPaymentEntity, Error>) -> Void) {   // key 2
        guard let userId else { return completion(.failure(MeansOfPaymentError.missingUser)) }      // key 1
        membershipService.membership(userId: userId) { [cardService] membership, error in
            if let error { return completion(.failure(error)) }
            guard let membership, let membershipId = membership.id else {
                return completion(.failure(MeansOfPaymentError.noMembership))                       // key 1
            }
            cardService.card(membershipId: membershipId) { card, error in
                if let error { return completion(.failure(error)) }
                guard let card else { return completion(.failure(MeansOfPaymentError.noCard)) }     // key 2
                completion(.success(MeansOfPaymentEntity(membership: membership, card: card)))
            }
        }
    }
}
```

And in the presenter, the two things that left the domain:

```swift
// key 7: a screen event, fired once when the screen appears
func viewDidAppear() { analytics.track(event: "did_show_meansOfPayment_screen") }

// keys 3, 4, 5: exhaustive, non-optional, no force unwrap; the view decides what "no image" means
func iconName(for level: CardLevel) -> String {
    switch level {
    case .standard: "ic_card_standard"
    case .plus: "ic_card_plus"
    }
}
```

**Said out loud, not coded:** make `userId` non-optional (key 10); give the domain its own models
and map from the data layer (key 8); rename to `GetMeansOfPaymentUseCase` and align the screen's
names (key 12); ask the PM whether "no card yet" is an error or a screen state — if it's a state,
it belongs in the entity (`card: Card?`), not in `MeansOfPaymentError`; and move to `async throws`,
where the compiler enforces "every path returns".

Why each piece:

- **`guard … else { completion(…) }` on every branch** — each dead end now reports, so the presenter
  can stop the spinner and show something.
- **`Result`** — the entity exists only on success, with both values in it. The `(nil, nil)` "success"
  can't be written any more.
- **`[cardService]` instead of `self.`** — the inner call needs the service, not the use case. It
  also means nothing keeps the use case alive just to finish a request.
- **Analytics leaves, not injected** — once it moves to the presenter, the use case doesn't need it
  at all. Fewer dependencies beat a better-injected one.
:::

::: Now write the tests
> "Good. There's no QA here, so: what would you test before this ships?"

**What I'd test, and why**

1. **A membership without an id fails instead of hanging** — the bug that would have reached users:
   exactly one callback, with `.noMembership`, and the card service never called.
2. **No user fails without calling the network** — one callback, `.missingUser`, zero requests.
3. **The membership id is what fetches the card** — the happy path, and proof the two calls are
   wired in the right order with the right value.
4. **A card error reaches the caller once** — errors from the second call aren't swallowed or
   doubled.

Each test collects *every* result the use case delivers, so "never called back" (`count == 0`) and
"called twice" (`count == 2`) both fail loudly.

**The seam.** The two service protocols, with fakes that answer immediately with whatever the test
sets and record what they were asked. Because the fakes call back synchronously, the tests need no
waiting at all.

```swift
import Foundation
import Testing

/// Answers straight away with whatever the test set, and records what it was asked.
final class FakeMembershipService: MembershipService {
    var answer: (Membership?, Error?) = (nil, nil)
    private(set) var requestedUserIds: [String] = []
    func membership(userId: String, completion: @escaping (Membership?, Error?) -> Void) {
        requestedUserIds.append(userId)
        completion(answer.0, answer.1)
    }
}

final class FakeCardService: CardService {
    var answer: (Card?, Error?) = (nil, nil)
    private(set) var requestedMembershipIds: [String] = []
    func card(membershipId: String, completion: @escaping (Card?, Error?) -> Void) {
        requestedMembershipIds.append(membershipId)
        completion(answer.0, answer.1)
    }
}

struct CardUseCaseTests {
    let memberships = FakeMembershipService()
    let cards = FakeCardService()
    var useCase: CardUseCase { CardUseCase(cardService: cards, membershipService: memberships) }

    /// Runs the use case and returns every result it delivered, so a test can see "never" and "twice".
    func results(for userId: String?) -> [Result<MeansOfPaymentEntity, Error>] {
        var delivered: [Result<MeansOfPaymentEntity, Error>] = []
        useCase.meansOfPayment(userId: userId) { delivered.append($0) }
        return delivered
    }

    @Test
    func aMembershipWithoutAnIdFailsInsteadOfHanging() throws {
        let membership = Membership()                    // id is nil: the original never called back
        memberships.answer = (membership, nil)

        let delivered = results(for: "user-1")

        #expect(delivered.count == 1)
        #expect(throws: MeansOfPaymentError.noMembership) { try delivered[0].get() }
        #expect(cards.requestedMembershipIds.isEmpty)
    }

    @Test
    func noUserFailsWithoutCallingTheNetwork() throws {
        let delivered = results(for: nil)

        #expect(delivered.count == 1)
        #expect(throws: MeansOfPaymentError.missingUser) { try delivered[0].get() }
        #expect(memberships.requestedUserIds.isEmpty)
    }

    @Test
    func theMembershipIdIsUsedToFetchTheCard() throws {
        let membership = Membership(); membership.id = "m-42"
        let card = Card(); card.cardLevel = .plus
        memberships.answer = (membership, nil)
        cards.answer = (card, nil)

        let delivered = results(for: "user-1")

        let entity = try #require(delivered.first).get()
        #expect(delivered.count == 1)
        #expect(memberships.requestedUserIds == ["user-1"])
        #expect(cards.requestedMembershipIds == ["m-42"])
        #expect(entity.card === card && entity.membership === membership)
    }

    @Test
    func aCardErrorReachesTheCallerOnce() throws {
        struct Offline: Error {}
        let membership = Membership(); membership.id = "m-42"
        memberships.answer = (membership, nil)
        cards.answer = (nil, Offline())

        let delivered = results(for: "user-1")

        #expect(delivered.count == 1)
        #expect(throws: Offline.self) { try delivered[0].get() }
    }
}
```

All four pass. Run the first two against the original and they can't even be written — the
original builds its own services, so there's nothing to fake. That's finding 6, proved.
:::

::: What I'd ask next
- *"Rewrite `meansOfPayment` with async/await."* — `func meansOfPayment(userId: String) async throws
  -> MeansOfPaymentEntity`: two `try await` calls and two `guard … else { throw … }`. The compiler now
  rejects a path that neither returns nor throws, so finding 1 can't come back.
- *"Could the two calls run in parallel?"* — Not as designed: the card needs the membership id. If
  this screen is slow, the better question is for the backend — one endpoint, "means of payment for
  user", so the app makes one round trip.
- *"Is 'no membership' an error?"* — Depends on the product. If some users legitimately have none,
  it's a screen state ("Get a card"), not a failure. That's a question for the PM, and the answer
  decides whether it lives in the entity or in the error enum.
- *"Where should `PaymentMethodViewController` get its presenter, and the presenter its use case?"*
  — From a composition root (a factory or coordinator) that builds the real services once. Nothing
  in the chain says `…Impl()` except that root.
- *"How would you test the presenter?"* — The same way: inject the use case behind a small protocol
  (or a closure), fake its result, and check what the presenter told the view — including that the
  spinner stops on every failure.
- *"Swift 6 doesn't complain about any of this. Should it?"* — The completion closures aren't
  `@Sendable`, so the compiler trusts them. Once these services really call back on a background
  queue, marking the closures `@Sendable` (or moving to `async`) makes the compiler check what
  crosses threads.
:::
