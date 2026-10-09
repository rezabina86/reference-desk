---
title: 27 · The SwiftUI screen inside a UIKit app
summary: A UIKit account screen that hosts a SwiftUI header through UIHostingController — the everyday mid-migration setup — with a crash, a leak, stacked headers and two copies of the same number. Review it and fix it without leaving UIKit.
minutes: 20
group: Review this PR
sources:
- Apple · UIHostingController | https://developer.apple.com/documentation/swiftui/uihostingcontroller
- Apple · sizingOptions — intrinsicContentSize invalidates when the ideal size changes | https://developer.apple.com/documentation/swiftui/uihostingcontrollersizingoptions/intrinsiccontentsize
- Apple · Creating a custom container view controller — addChild and didMove(toParent:) | https://developer.apple.com/documentation/uikit/creating-a-custom-container-view-controller
- Apple · ObservedObject — "Don't specify a default or initial value for the observed object" | https://developer.apple.com/documentation/swiftui/observedobject
- Apple · StateObject | https://developer.apple.com/documentation/swiftui/stateobject
- Apple · EnvironmentObject | https://developer.apple.com/documentation/swiftui/environmentobject
---

*Shape: review this PR · Reported: a common senior-round topic; no specific company report found ·
Verified: the snippet and the fix typecheck against the iOS SDK in Swift 6 mode (the snippet with
one warning, key 9); the view model's tests ran with Swift 6.4; the hosting wiring is checked by hand*

> "We're moving to SwiftUI one piece at a time. This PR puts a SwiftUI profile header at the top of
> our UIKit account screen. On the device: open Orders and come back, and there are two headers.
> Sometimes the app crashes on open. Review it."

```swift
import SwiftUI
import UIKit

@MainActor
final class ProfileViewModel: ObservableObject {
    @Published private(set) var name = ""
    @Published private(set) var orderCount = 0
    private let api: ProfileLoading

    init(api: ProfileLoading = LiveProfileAPI()) {
        self.api = api
    }

    func load() async {
        let profile = try? await api.profile()
        name = profile?.name ?? ""
        orderCount = profile?.orderCount ?? 0
    }
}

struct ProfileHeader: View {
    @ObservedObject var viewModel = ProfileViewModel()
    @EnvironmentObject var session: Session
    var onOpenOrders: () -> Void = {}

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(viewModel.name).font(.title2.bold())
            Text(session.email).foregroundStyle(.secondary)
            Button("Your orders (\(viewModel.orderCount))") { onOpenOrders() }
        }
        .padding()
        .onAppear {
            Task { await viewModel.load() }
        }
    }
}

final class AccountViewController: UIViewController {
    private let session: Session
    private let stackView = UIStackView()
    private var orderCount = 0

    init(session: Session) {
        self.session = session
        super.init(nibName: nil, bundle: nil)
    }

    required init?(coder: NSCoder) { fatalError("init(coder:) has not been implemented") }

    override func viewDidLoad() {
        super.viewDidLoad()
        stackView.axis = .vertical
        stackView.frame = view.bounds
        stackView.autoresizingMask = [.flexibleWidth, .flexibleHeight]
        stackView.addArrangedSubview(UIButton(configuration: .plain(), primaryAction: UIAction(title: "Log out") { _ in }))
        view.addSubview(stackView)
    }

    override func viewWillAppear(_ animated: Bool) {
        super.viewWillAppear(animated)
        var header = ProfileHeader()
        header.onOpenOrders = {
            self.navigationController?.pushViewController(OrdersViewController(), animated: true)
        }
        let hosting = UIHostingController(rootView: header)
        stackView.insertArrangedSubview(hosting.view, at: 0)

        Task {
            orderCount = try await LiveProfileAPI.shared.profile().orderCount
            tabBarItem.badgeValue = "\(orderCount)"
        }
    }
}
```

It compiles in Swift 6 mode with one warning, on the last `Task`: *unstructured throwing task …
is not used, which may accidentally ignore errors thrown inside the task* (checked).

::: A hint, if you're stuck
- How many times does `viewWillAppear` run in a screen's life? What does each run add?
- Where does `session` come from inside the SwiftUI view?
- Who owns the `ProfileViewModel`? What happens to it when SwiftUI rebuilds `ProfileHeader`?
- Count the places that know the order count.
:::

::: The key — what I expect a senior to find
1. **The environment object is never provided: a crash.** `ProfileHeader` reads
   `@EnvironmentObject var session`, and nothing up the tree calls `.environmentObject(session)` —
   the controller *has* a session and never passes it. SwiftUI stops the app with a fatal error as
   soon as the header reads `session`. Inject it on the root view.
2. **A new header on every appearance.** `viewWillAppear` runs every time the screen comes back,
   so push Orders, pop, and a second hosting controller (with a second view model) goes into the
   stack above the first. That's the "two headers". Build the hosted view once, in `viewDidLoad`.
3. **The hosting controller isn't a child.** Only its view is added; nothing but a local variable
   holds the controller, and UIKit doesn't know it exists. Without `addChild(_:)` and
   `didMove(toParent:)` it isn't in the view-controller tree, so appearance calls, trait changes
   and safe area aren't forwarded to it the way UIKit promises a child.
4. **`sizingOptions` is left at its default.** In a stack view the header's height comes from its
   intrinsic size. By default that isn't updated when the SwiftUI content changes — the name
   arriving, a bigger Dynamic Type size — so the header can clip. Set
   `sizingOptions = .intrinsicContentSize` (iOS 16+).
5. **`@ObservedObject` with a default value.** `@ObservedObject` watches an object it doesn't own;
   Apple's docs say "don't specify a default or initial value". SwiftUI can rebuild the
   `ProfileHeader` struct at any time, and each rebuild makes a fresh, empty view model. Here the
   UIKit side should own it and pass it in (or the view owns it with `@StateObject`).
6. **Loading too often.** `.onAppear` fires on every appearance of every hosting controller, the
   controller fetches separately in `viewWillAppear`, and nothing stops two loads overlapping. Load
   in one place, and ignore a load while one is in flight.
7. **A retain cycle through the closure.** `onOpenOrders` captures `self` strongly. The closure
   lives in the root view, the root view in the hosting view, the hosting view in `stackView`,
   which `self` owns. The account screen is never freed. `[weak self]`.
8. **Two copies of the order count.** The badge comes from the controller's own fetch, the header
   from the view model's. Two requests, and they can disagree — one fails, or an order is placed
   between them. Keep one view model, owned by the controller, and have the badge observe it.
9. **The throwing `Task` hides errors.** If `profile()` throws, the task ends silently and the
   badge is never set. The compiler warns about exactly this.
10. **`LiveProfileAPI.shared` inside the controller.** It bypasses the view model's injected API,
    so no test can control it. It goes away once the badge reads the view model.
11. **A failed refresh blanks the screen.** `try?` plus `?? ""` means one dropped connection
    replaces a good name with nothing and the count with 0, and there's no error to show. Keep
    what you had and surface the error.
12. **The stack ignores the safe area.** `stackView.frame = view.bounds` puts the header under the
    navigation bar and the notch. Pin it to `safeAreaLayoutGuide` with constraints.
13. **`onOpenOrders` is a `var` set after init.** Style: pass it in the initializer so a caller
    can't forget it. Note what's *right* here, too: navigating back into UIKit through a closure
    is the standard bridge — the SwiftUI view doesn't need to know about `UINavigationController`.
:::

::: The idea behind it
A `UIHostingController` is a normal view controller whose view happens to be drawn by SwiftUI. So
all of UIKit's rules for putting one controller inside another still apply. A *container*
controller must call `addChild(_:)` before adding the child's view, and the child's
`didMove(toParent:)` after. That's what links them: the parent then forwards appearance, size and
trait changes to the child, and holds it alive. Adding only the view is like hiring someone and
never telling HR — they're in the building, but nobody passes them the memos.

Inside SwiftUI, the question is always **who owns the object**. A SwiftUI view is a cheap struct
that's thrown away and rebuilt all the time. `@StateObject` means "this view owns the object —
create it once and keep it across rebuilds". `@ObservedObject` means "someone else owns it; I just
watch". `@EnvironmentObject` means "someone above me put it in the environment" — and if nobody
did, it's a crash, not a nil.

In a mixed app the clean shape is: **UIKit owns the state, SwiftUI draws it.** The controller
creates one view model, hands it to the SwiftUI view, and observes the same object for its own
needs (the tab badge). One copy of the truth, read by both sides, so they can't drift.

And `viewWillAppear` is the wrong place to *build* anything: it runs every time the screen comes
back. `viewDidLoad` runs once per screen.
:::

::: The fix
The view model — only `load()` and two properties change:

```swift
@Published private(set) var errorMessage: String?               // key 11
private var isLoading = false                                    // key 6

func load() async {
    guard !isLoading else { return }                             // key 6
    isLoading = true
    defer { isLoading = false }
    do {
        let profile = try await api.profile()
        name = profile.name
        orderCount = profile.orderCount
        errorMessage = nil
    } catch {
        errorMessage = String(localized: "We couldn't load your profile.")   // key 11: keep what we had
    }
}
```

The header and the controller:

```swift
struct ProfileHeader: View {
    @ObservedObject var viewModel: ProfileViewModel                     // key 5: owned by UIKit, passed in
    @EnvironmentObject var session: Session
    var onOpenOrders: () -> Void = {}

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(viewModel.name).font(.title2.bold())
            Text(session.email).foregroundStyle(.secondary)
            Button("Your orders (\(viewModel.orderCount))") { onOpenOrders() }
        }
        .padding()                                                      // key 6: no .onAppear load
    }
}

final class AccountViewController: UIViewController {
    private let session: Session
    private let viewModel: ProfileViewModel                             // key 5, 8: the one copy
    private let stackView = UIStackView()
    private var badgeSubscription: AnyCancellable?

    init(session: Session, viewModel: ProfileViewModel) {
        self.session = session
        self.viewModel = viewModel
        super.init(nibName: nil, bundle: nil)
    }

    // required init?(coder:) unchanged

    override func viewDidLoad() {
        super.viewDidLoad()
        stackView.axis = .vertical
        stackView.translatesAutoresizingMaskIntoConstraints = false     // key 12
        stackView.addArrangedSubview(UIButton(configuration: .plain(), primaryAction: UIAction(title: "Log out") { _ in }))
        view.addSubview(stackView)
        NSLayoutConstraint.activate([
            stackView.topAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor),
            stackView.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            stackView.trailingAnchor.constraint(equalTo: view.trailingAnchor),
        ])

        var header = ProfileHeader(viewModel: viewModel)                // key 2: built once
        header.onOpenOrders = { [weak self] in                          // key 7
            self?.navigationController?.pushViewController(OrdersViewController(), animated: true)
        }
        let hosting = UIHostingController(rootView: header.environmentObject(session))   // key 1
        hosting.sizingOptions = .intrinsicContentSize                   // key 4
        addChild(hosting)                                               // key 3
        stackView.insertArrangedSubview(hosting.view, at: 0)
        hosting.didMove(toParent: self)                                 // key 3

        badgeSubscription = viewModel.$orderCount.sink { [weak self] count in   // key 8, 10
            self?.tabBarItem.badgeValue = count > 0 ? "\(count)" : nil
        }
        Task { await viewModel.load() }                                 // key 6, 9: one load, can't throw
    }
    // viewWillAppear is gone                                           // key 2
}
```

**Said out loud, not coded:** refresh on return with an explicit pull-to-refresh rather than every
appearance; show `errorMessage` in the header; pass `onOpenOrders` through the initializer (key
13); move navigation to a coordinator; on iOS 17+, `@Observable` instead of `ObservableObject`,
which lets UIKit (iOS 26 and later) track the badge without Combine; drop the default
`LiveProfileAPI()` from the view model's `init` so the composition root decides.

Why each piece:

- **The controller creates nothing it doesn't have to.** The view model comes in through `init`, so
  whoever builds the screen decides the API — and a test or preview can pass a fake.
- **`header.environmentObject(session)`** — the hosting controller's root is now a modified view.
  Its exact type doesn't matter because `hosting` is a local `let`.
- **The badge observes `$orderCount`** — Combine is already what `ObservableObject` uses, so it's
  the smallest way for UIKit to watch the same object SwiftUI watches.
:::

::: Now write the tests
> "Good. What would you test — and what wouldn't you?"

**What I'd test, and why**

1. **A load publishes the count the badge listens to** — the badge and the header now read one
   value, so the test subscribes to `$orderCount` exactly as the controller does.
2. **Two loads at once make one request** — the double load. Two loads start while the first reply
   is still held back; only one request may go out.
3. **A failed reload keeps what was shown** — the "blank screen on a flaky network" bug, and the
   error is set.

**What I'd check by hand, not unit-test:** the hosting wiring — child controller, sizing, safe
area, no second header after push and pop, and no leak. Open Orders and come back three times:
one header. Increase the text size in Settings: the header grows. Then Debug Memory Graph after
closing the screen: no `AccountViewController` left. A unit test can't see layout, and a UI test
for this costs more than it saves.

**The seam.** The view model already takes a `ProfileLoading`. The fake can *hold* its reply
(a checked continuation — a paused `await` the test resumes by hand) so two loads really overlap,
with no clock. The view model imports only Foundation and Combine, so this runs on the Mac.

```swift
import Combine
import Foundation
import Testing

/// A fake API: answers with `result`, and can hold its replies until the test releases them.
@MainActor
final class FakeProfileAPI: ProfileLoading {
    var result: Result<Profile, Error> = .success(Profile(name: "Ada", orderCount: 3))
    var holdsReplies = false
    private(set) var requestCount = 0
    private var waiting: [CheckedContinuation<Void, Never>] = []

    func profile() async throws -> Profile {
        requestCount += 1
        if holdsReplies { await withCheckedContinuation { waiting.append($0) } }
        return try result.get()
    }

    func releaseReplies() {
        waiting.forEach { $0.resume() }
        waiting = []
    }
}

/// Gives the main actor turns until `condition` holds. Bounded by a count, not a clock.
@MainActor
func waitUntil(maxYields: Int = 1_000, _ condition: () -> Bool) async -> Bool {
    for _ in 0..<maxYields {
        if condition() { return true }
        await Task.yield()
    }
    return condition()
}

@MainActor
struct ProfileViewModelTests {
    @Test func loadPublishesTheCountTheBadgeListensTo() async {
        let viewModel = ProfileViewModel(api: FakeProfileAPI())
        var badgeCounts: [Int] = []
        let subscription = viewModel.$orderCount.sink { badgeCounts.append($0) }

        await viewModel.load()

        #expect(viewModel.name == "Ada")
        #expect(badgeCounts == [0, 3])
        subscription.cancel()
    }

    @Test func twoLoadsAtOnceMakeOneRequest() async {
        let api = FakeProfileAPI()
        api.holdsReplies = true
        let viewModel = ProfileViewModel(api: api)

        let first = Task { await viewModel.load() }
        let second = Task { await viewModel.load() }
        #expect(await waitUntil { api.requestCount == 1 })
        _ = await waitUntil(maxYields: 100) { false }       // give the second load its turn
        api.releaseReplies()
        await first.value
        await second.value

        #expect(api.requestCount == 1)
        #expect(viewModel.orderCount == 3)
    }

    @Test func failedReloadKeepsWhatWasShown() async {
        let api = FakeProfileAPI()
        let viewModel = ProfileViewModel(api: api)
        await viewModel.load()

        api.result = .failure(URLError(.notConnectedToInternet))
        await viewModel.load()

        #expect(viewModel.name == "Ada")
        #expect(viewModel.orderCount == 3)
        #expect(viewModel.errorMessage != nil)
    }
}
```

Ran with Swift 6.4: 3 tests, all passed.
:::

::: What I'd ask next
- *"`@StateObject` or pass it in?"* — If only the SwiftUI view uses the object, `@StateObject` in
  the view. If UIKit also needs it (the badge here), UIKit owns it and passes it in as
  `@ObservedObject`. Never `@ObservedObject` with a default value.
- *"How would the hosted view tell UIKit its size if it were in a sheet or popover?"* —
  `sizingOptions = .preferredContentSize`: the hosting controller keeps `preferredContentSize` in
  step with its SwiftUI content, which a popover or a custom sheet uses.
- *"Why not `.task` instead of `.onAppear { Task { … } }`?"* — `.task` is cancelled when the view
  disappears, so a slow load doesn't outlive the screen. It still runs on every appearance; whether
  that's right is a product decision.
- *"How do you migrate the rest of this screen?"* — Screen by screen, with UIKit still doing the
  navigation, until a whole flow is SwiftUI; then move that flow's navigation to a
  `NavigationStack`. Share state through view models both sides can observe.
- *"Would you UI-test it?"* — One smoke UI test that opens the screen, pushes Orders and comes back,
  and asserts one header exists, is cheap insurance for key 2. Not more.
:::
