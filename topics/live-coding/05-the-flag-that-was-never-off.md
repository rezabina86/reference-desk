---
title: 05 · The flag that was never off
summary: A wallet home screen whose features hang on a synchronous, UserDefaults-backed flag singleton. It doesn't build under Swift 6, an unfinished feature is live, hiding the balance doesn't stick, and the existing tests only pass in one order. Fix it, then migrate the screen to an async flag client that can fail, keeping its tests.
minutes: 60
group: Rounds
sources:
- Swift · Mutable global variables — the diagnostic the first build error links to | https://docs.swift.org/compiler/documentation/diagnostics/mutable-global-variable
- Apple · UserDefaults — "thread-safe", which is what makes @unchecked Sendable honest here | https://developer.apple.com/documentation/foundation/userdefaults
- Apple · init(suiteName:) — a UserDefaults of its own for each test | https://developer.apple.com/documentation/foundation/userdefaults/init(suitename:)
- Apple · Swift Testing parallelization — tests run in parallel by default, so order is not a contract | https://developer.apple.com/documentation/testing/parallelization
- Apple · Bindable — bindings into an @Observable model passed in from outside | https://developer.apple.com/documentation/swiftui/bindable
- Dojo · iOS live-coding senior interview — migrate a shipped screen to a new async client; no AI tools | https://github.com/dojo-engineering/ios-live-coding-senior-interview
---

*Shape: C · review it, then extend it — 60 minutes, your Xcode, screen shared, no AI assistant · Reported:
Dojo's published senior exercise (move a shipped screen from a synchronous legacy client to a new async,
failable one, keeping its behaviour and its tests). This project is original; only the shape is copied ·
Verified: Xcode 27.1, iOS 26 target, Swift 6 language mode with main-actor default isolation. The starter fails
with the build errors below, one after the other. On the iPhone 17e simulator, the unfinished section, the flag
reads on every render and the balance that un-hides itself were reproduced, and the console lines are quoted as
logged. The existing tests pass as shipped and fail when two of them swap places. The Part 1 fix and the
migrated app build with no warnings. The migrated app was also run with the flag service slowed down and with
it down. All seven tests pass on the simulator.*

**How the hour runs**

| Time | The interviewer says | You're scored on |
|---|---|---|
| 0:00–0:05 | "Clone it, open it, get it running." | Three concurrency errors, and when `@unchecked` is honest |
| 0:05–0:25 | "Walk me through what you'd change. Fix what matters." | The console, where flags are read, the existing tests |
| 0:25–0:50 | "Move this screen to the new flag client." | What the screen does while loading and when the client fails |
| 0:50–1:00 | "Keep the old tests green and add yours. Then: kill switch?" | A seam that survived the migration, follow-ups |

> "This is the home screen of our wallet app. Some of what it shows depends on feature flags. The flags
> come from an old SDK that we want to retire. It's in a local package together with the new client. Get it
> running and tell me what you'd change. There are existing tests, so run them too. Talk as you go."

The project is in `LiveCodingLab/Round05-FeatureFlags`. The server's values are `new_card_banner: true`,
`instant_transfers: true` and `spending_insights: false`. The insights feature isn't finished.

```swift
// FlagsKit/Sources/FlagsKit/LegacyFlags.swift — the package has no default isolation
import Foundation

public enum LegacyFlagKey: String, CaseIterable, Sendable {
    case newCardBanner = "new_card_banner"
    case instantTransfers = "instant_transfers"
    case spendingInsights = "spending_insigths"
}

/// The flag SDK the app shipped with: synchronous, backed by UserDefaults.
public final class LegacyFlags {
    public static var shared = LegacyFlags()

    private let defaults: UserDefaults

    public init(defaults: UserDefaults = .standard) {
        self.defaults = defaults
    }

    /// Called once at launch. Copies the values the server sent last into UserDefaults.
    public func sync() {
        let fromServer: [String: Bool] = [
            "new_card_banner": true,
            "instant_transfers": true,
            "spending_insights": false,     // still being built
        ]
        for (key, value) in fromServer {
            defaults.set(value, forKey: key)
        }
    }

    public func isEnabled(_ key: LegacyFlagKey) -> Bool {
        print("[LegacyFlags] read \(key.rawValue)")
        // Fail open: we'd rather show a feature than hide one by accident.
        return defaults.object(forKey: key.rawValue) as? Bool ?? true
    }

    public func set(_ value: Bool, for key: LegacyFlagKey) {
        defaults.set(value, forKey: key.rawValue)
    }
}
```

```swift
// Wallet/Wallet/WalletApp.swift
import SwiftUI
import FlagsKit

@main
struct WalletApp: App {
    init() {
        LegacyFlags.shared.sync()
    }

    var body: some Scene {
        WindowGroup {
            RootView()
        }
    }
}
```

```swift
// Wallet/Wallet/RootView.swift
import SwiftUI

enum AppTab: Hashable {
    case home
    case settings
}

struct RootView: View {
    @State private var selectedTab = AppTab.home

    var body: some View {
        TabView(selection: $selectedTab) {
            Tab("Home", systemImage: "house", value: AppTab.home) {
                NavigationStack {
                    HomeView(viewModel: HomeViewModel())
                }
            }
            Tab("Settings", systemImage: "gearshape", value: AppTab.settings) {
                NavigationStack {
                    Form {
                        LabeledContent("Version", value: "4.2.0")
                    }
                    .navigationTitle("Settings")
                }
            }
        }
        .sensoryFeedback(.selection, trigger: selectedTab)
    }
}
```

```swift
// Wallet/Wallet/HomeViewModel.swift — the target's default isolation is MainActor
import Foundation
import Observation
import FlagsKit

@Observable
final class HomeViewModel {
    var balance: Decimal = 1240.50
    var isBalanceHidden = false

    var showsInstantTransfer: Bool {
        LegacyFlags.shared.isEnabled(.instantTransfers) && balance > 0
    }
}
```

```swift
// Wallet/Wallet/HomeView.swift
import SwiftUI
import FlagsKit

struct HomeView: View {
    let viewModel: HomeViewModel

    var body: some View {
        @Bindable var viewModel = viewModel
        List {
            if LegacyFlags.shared.isEnabled(.newCardBanner) {
                Section {
                    Label {
                        VStack(alignment: .leading) {
                            Text("Your new card is on its way")
                                .font(.headline)
                            Text("Activate it when it arrives.")
                                .font(.subheadline)
                        }
                    } icon: {
                        Image(systemName: "creditcard")
                    }
                }
            }

            Section("Balance") {
                Text(viewModel.isBalanceHidden ? "••••••" : viewModel.balance.formatted(.currency(code: "EUR")))
                    .font(.largeTitle.bold())
                Toggle("Hide balance", isOn: $viewModel.isBalanceHidden)
            }

            Section("Quick actions") {
                Label("Send money", systemImage: "arrow.up.right")
                if viewModel.showsInstantTransfer {
                    Label("Instant transfer", systemImage: "bolt")
                }
                Label("Top up", systemImage: "plus")
            }

            if LegacyFlags.shared.isEnabled(.spendingInsights) {
                Section("Spending insights") {
                    Text("TODO: monthly chart goes here")
                        .foregroundStyle(.secondary)
                }
            }
        }
        .navigationTitle("Home")
    }
}

#Preview {
    NavigationStack {
        HomeView(viewModel: HomeViewModel())
    }
}
```

```swift
// Wallet/WalletTests/WalletTests.swift — the existing tests
import Testing
import FlagsKit
@testable import Wallet

struct HomeViewModelTests {

    @Test func showsInstantTransferWithAPositiveBalance() {
        let viewModel = HomeViewModel()
        #expect(viewModel.showsInstantTransfer)
    }

    @Test func hidesInstantTransferWhenTheFlagIsOff() {
        LegacyFlags.shared.set(false, for: .instantTransfers)
        let viewModel = HomeViewModel()
        #expect(!viewModel.showsInstantTransfer)
    }

    @Test func hidesInstantTransferWithAnEmptyBalance() {
        let viewModel = HomeViewModel()
        viewModel.balance = 0
        #expect(!viewModel.showsInstantTransfer)
    }
}
```

## Part 1 — make it run, then review it

::: A hint, if you're stuck
The build errors are all about one line, `shared`. Read every note under each error, and pick the fix you can
defend, not the one that makes the error go away. Once it runs, tap "Hide balance" with the console open, then
switch to Settings and back. Then run the tests, and read them as if you were about to add one.
:::

::: The key — what I expect a senior to find
In the order you'd hit them: build, run, use, read.

**It doesn't build**

1. **`static property 'shared' is not concurrency-safe because it is nonisolated global shared mutable state`.**
   A singleton declared `var` is a global that anyone can replace, from any thread. Someone made it `var` so a
   test could swap it, which is a test seam made of global state. Make it `let`. The compiler also offers
   `@MainActor` and "disable concurrency-safety checks", and you should say why you don't take them:
   `nonisolated(unsafe)` hides the problem, and `@MainActor` on an SDK type forces every caller onto the main
   actor.
2. **`static property 'shared' is not concurrency-safe because non-'Sendable' type 'LegacyFlags' may have
   shared mutable state`.** You only see it after fixing 1. Add `Sendable`, and the compiler moves on to the
   reason: *"stored property 'defaults' of 'Sendable'-conforming class 'LegacyFlags' has non-Sendable type
   'UserDefaults'"*. Here, `@unchecked Sendable` is the honest answer, and you should say why: the class is
   `final`, its only stored property is a `let`, and Apple documents `UserDefaults` as thread-safe. You can
   name the guarantee you're relying on. If you can't name it, `@unchecked` is wrong.

**It runs — look at the screen and the console**

3. **"Spending insights — TODO: monthly chart goes here" is on the home screen.** The server says
   `spending_insights: false`. The console says why:

   ```
   [LegacyFlags] read new_card_banner
   [LegacyFlags] read instant_transfers
   [LegacyFlags] read spending_insigths
   ```

   Two bugs make this happen. The key has a typo, so the value is never found. And a missing value returns
   `true`, because the SDK "fails open". Either one alone would hide the other. Fix the key. Then fail closed:
   a flag you can't find is a feature that isn't ready, and failing open is the wrong default for a flag that
   exists to switch things *off*.
4. **Tap "Hide balance", and the same three lines print again.** Switch tabs, and they print again. The flags
   are read inside `body`, on every render. So the decision about what the screen shows is made in the view,
   where you can't test it. It's re-made at times nobody chose. And it's still not live, because nothing
   observes `UserDefaults`. Read the flags once into a plain value in the view model.
5. **Hide the balance, switch to Settings and back: the balance is shown again.** `RootView` creates
   `HomeViewModel()` inside `body`. Its body runs again on a tab switch, so Home gets a fresh view model, and
   the state goes with the old one. In a wallet, "hide my balance" that undoes itself is a privacy bug. Keep
   the view model in `@State` in `RootView`, and make `HomeView` take it with `@Bindable`.

**Read the code, then the tests**

6. **The view model reaches for `LegacyFlags.shared`.** `showsInstantTransfer` can't be tested without writing
   to the global flags. Inject what the view model needs, and keep the SDK behind one small adapter.
7. **The existing tests share `UserDefaults.standard`, and they pass by luck.**
   `hidesInstantTransferWhenTheFlagIsOff` writes `false` and never puts it back.
   `showsInstantTransferWithAPositiveBalance` writes nothing. It passes only because it runs first, and
   because the test host is the app, whose `init` called `sync()` before any test ran. Move the "off" test above
   it and the suite fails: *"Expectation failed: viewModel.showsInstantTransfer"*. Swift Testing runs tests in
   parallel by default, so order is not something a test may rely on. Give the tests their own input, and the
   problem goes away.
8. **Said, not coded:**
   - `sync()` runs on the main thread in `App.init`. With a real network call, launch would wait for it.
   - The `#Preview` reads the real singleton, so previews show whatever the simulator's defaults hold.
   - The flag keys are strings in an enum. The typo only showed because a feature leaked. A test that checks
     the keys against what the server sends would have caught it earlier.

What sinks this part: `nonisolated(unsafe)` on `shared`; fixing the typo and keeping fail-open, so the next
typo leaks the next feature; or "fixing" the tests by adding `.serialized` and leaving the global state.
:::

::: The idea behind it
A flag is a **value read at a moment you choose**, not a function you call whenever you render. Once the
screen gets a plain `HomeFlags` value, everything else follows. The view has nothing to decide. The view model
can be tested with any combination of flags. The SDK lives in one adapter. The tests stop sharing a global,
because they no longer touch it.

That's also what makes Part 2 small. The view model doesn't care *where* `HomeFlags` comes from. Moving to an
async client only changes how the value arrives, and what we use before it does.

| Use | Instead of |
|---|---|
| A plain `HomeFlags` value, read once | calling the flag SDK from `body` |
| A protocol the view model needs, and one adapter for the SDK | `LegacyFlags.shared` inside the view model |
| Fail closed, or a safe default for each flag | `?? true` "so nothing gets hidden" |
| `@State` for a view model the view owns, `@Bindable` to pass it down | building it inside a parent's `body` |
| Inputs given to each test | tests writing to `UserDefaults.standard` |
| `@unchecked Sendable` only with a named guarantee | `nonisolated(unsafe)` to silence the compiler |
:::

::: The fix
In the package: `let`, an honest `@unchecked Sendable`, the right key, and fail closed:

```swift
public enum LegacyFlagKey: String, CaseIterable, Sendable {
    case newCardBanner = "new_card_banner"
    case instantTransfers = "instant_transfers"
    case spendingInsights = "spending_insights"
}

/// The flag SDK the app shipped with: synchronous, backed by UserDefaults.
public final class LegacyFlags: @unchecked Sendable {   // UserDefaults is thread-safe, and `defaults` never changes
    public static let shared = LegacyFlags()

    private let defaults: UserDefaults
    // ... unchanged ...

    public func isEnabled(_ key: LegacyFlagKey) -> Bool {
        print("[LegacyFlags] read \(key.rawValue)")
        // Fail closed: a flag we can't find is a feature that isn't ready.
        return defaults.object(forKey: key.rawValue) as? Bool ?? false
    }
```

A plain value for the screen, and the only file that knows about the SDK:

```swift
// Wallet/Wallet/HomeFlags.swift
import FlagsKit

/// What the home screen needs to know, read once, as plain values.
struct HomeFlags: Equatable {
    var showsCardBanner = false
    var allowsInstantTransfer = false
    var showsSpendingInsights = false
}

protocol HomeFlagsProviding {
    func homeFlags() -> HomeFlags
}

/// The only place in the app that knows about the legacy SDK.
struct LegacyHomeFlags: HomeFlagsProviding {
    let flags: LegacyFlags

    func homeFlags() -> HomeFlags {
        HomeFlags(
            showsCardBanner: flags.isEnabled(.newCardBanner),
            allowsInstantTransfer: flags.isEnabled(.instantTransfers),
            showsSpendingInsights: flags.isEnabled(.spendingInsights)
        )
    }
}
```

```swift
import Foundation
import Observation

@Observable
final class HomeViewModel {   // main actor: the target's default isolation
    var balance: Decimal = 1240.50
    var isBalanceHidden = false
    private(set) var flags: HomeFlags

    init(flags provider: any HomeFlagsProviding) {
        flags = provider.homeFlags()   // once per screen, not once per render
    }

    var showsCardBanner: Bool { flags.showsCardBanner }
    var showsInstantTransfer: Bool { flags.allowsInstantTransfer && balance > 0 }
    var showsSpendingInsights: Bool { flags.showsSpendingInsights }
}
```

`RootView` owns the view model, so it outlives a tab switch:

```swift
struct RootView: View {
    @State private var selectedTab = AppTab.home
    @State private var home: HomeViewModel     // owned here, so it outlives a tab switch

    init(flags: any HomeFlagsProviding = LegacyHomeFlags(flags: .shared)) {
        _home = State(initialValue: HomeViewModel(flags: flags))
    }

    var body: some View {
        TabView(selection: $selectedTab) {
            Tab("Home", systemImage: "house", value: AppTab.home) {
                NavigationStack {
                    HomeView(viewModel: home)
                }
            }
        // ... the Settings tab, unchanged ...
```

`HomeView` takes `@Bindable var viewModel: HomeViewModel`, and its two `if`s become `if viewModel.showsCardBanner`
and `if viewModel.showsSpendingInsights`. The preview gets its own provider. The existing tests keep their names
and their checks, and get a fake instead of the global:

```swift
import Testing
@testable import Wallet

private struct FakeFlags: HomeFlagsProviding {
    var flags: HomeFlags
    func homeFlags() -> HomeFlags { flags }
}

struct HomeViewModelTests {

    @Test func showsInstantTransferWithAPositiveBalance() {
        let viewModel = HomeViewModel(flags: FakeFlags(flags: HomeFlags(allowsInstantTransfer: true)))
        #expect(viewModel.showsInstantTransfer)
    }

    @Test func hidesInstantTransferWhenTheFlagIsOff() {
        let viewModel = HomeViewModel(flags: FakeFlags(flags: HomeFlags(allowsInstantTransfer: false)))
        #expect(!viewModel.showsInstantTransfer)
    }

    @Test func hidesInstantTransferWithAnEmptyBalance() {
        let viewModel = HomeViewModel(flags: FakeFlags(flags: HomeFlags(allowsInstantTransfer: true)))
        viewModel.balance = 0
        #expect(!viewModel.showsInstantTransfer)
    }
}
```

With this fix, the insights section is gone, the console prints the three reads once at launch and never again,
and the balance stays hidden across a tab switch.
:::

## Part 2 — add the feature

> "We're retiring the old SDK. `RemoteFlagsClient` is in FlagsKit: it's async, keys are namespaced, values are
> typed. Move the home screen to it and stop calling `sync()`. Keep the behaviour, and keep the tests passing."

This is the part of the new client you need:

```swift
// FlagsKit/Sources/FlagsKit/RemoteFlagsClient.swift (excerpt)
/// A flag with a namespaced key, `"<area>.<name>"`, and the type its value must have.
public struct Flag<Value: FlagValue>: Sendable {
    public let key: String

    public init(_ key: String) {
        precondition(key.contains("."), "Flag keys are namespaced: \"area.name\"")
        self.key = key
    }
}

/// Everything the server sent, at one moment.
public struct FlagSnapshot: Sendable, Equatable {
    public let values: [String: RawFlagValue]

    public init(_ values: [String: RawFlagValue]) {
        self.values = values
    }

    /// nil when the key is missing, or when its value has another type. Choosing the fallback is the caller's job.
    public func value<Value>(_ flag: Flag<Value>) -> Value? {
        values[flag.key].flatMap(Value.init(raw:))
    }
}

public enum RemoteFlagsError: LocalizedError, Equatable {
    case timedOut
    case unavailable(status: Int)

    public var errorDescription: String? {
        switch self {
        case .timedOut: "The flag service didn't answer in time."
        case .unavailable(let status): "The flag service is unavailable (\(status))."
        }
    }
}

// MARK: - Client

public protocol RemoteFlagsFetching: Sendable {
    func fetchSnapshot() async throws -> FlagSnapshot
}

/// The new flag service. Asynchronous, and it can fail or time out.
public actor RemoteFlagsClient: RemoteFlagsFetching {
    // ...
    public init(latency: Duration = .milliseconds(1200), timeout: Duration = .seconds(3), behaviour: Behaviour = .normal)
    public func fetchSnapshot() async throws -> FlagSnapshot   // prints "[RemoteFlags] GET /v1/flags?app=wallet"
}
// The server sends: "home.card_banner": true, "home.instant_transfers": true, "home.spending_insights": false, ...
```

::: A hint, if you're stuck
The old SDK answered at once. This one takes over a second, and sometimes doesn't answer at all. Before you write
anything, ask what the home screen shows in that second, and what it shows when the answer never comes. Then read
what `value(_:)` returns for a key that's missing.
:::

::: The key — what I expect a senior to find
**The questions to ask first** — each one changes the code:

- **Do we block the home screen until the flags arrive?** No. It's the first screen of the app. A flag service
  outage must not take the app down with it.
- **So what do we show while they load?** The values from the last successful fetch on this device. On the very
  first launch there are none, so each flag uses its own default.
- **What's the default — off for everything?** No, and this is the trap. A default is "what's safe if we know
  nothing", and that differs per flag. The card banner is a promotion: off. Instant transfers are live for
  everyone: on, or the outage removes a feature people use. Insights isn't finished: off. One global rule, on or
  off, is wrong for one of them.
- **And when the client fails or times out?** Keep what's on screen, log it, and try again the next time the
  screen appears. Never jump to "everything on".
- **A key that's missing, or has the wrong type?** That flag's default. `value(_:)` returns `nil` for both and
  leaves the choice to you, and `?? true` is the Part 1 bug again.
- **Can the screen change while the user looks at it?** Once, when the first fetch lands. After that, the last
  known values are the same as the server's, so nothing moves on later launches. Ask whether product accepts
  that. The alternative is to apply new values only on the next launch.

**What I'm looking at while you build:**

- `HomeFlags` is still the view model's only input, so the view model hardly changes and the Part 1 tests keep
  their bodies.
- The client lives in one adapter, `RemoteHomeFlags`. It also remembers the last good values.
- The defaults are written once, as the initial values of `HomeFlags`, next to the reason for each.
- `refreshFlags()` treats `CancellationError` as normal, and fetches once per launch, not on every tab switch.
:::

::: The fix
`HomeFlags` gets its defaults and a mapping from the snapshot. The protocol changes from "give me the flags" to
"what did you know last, and fetch":

```swift
// Wallet/Wallet/HomeFlags.swift
import Foundation
import FlagsKit

/// What the home screen needs to know, as plain values.
/// The initial values are what we show when we know nothing: each flag's own safe value.
struct HomeFlags: Equatable, Codable {
    var showsCardBanner = false          // a promotion: skipping it costs nothing
    var allowsInstantTransfer = true     // live for everyone: hiding it would remove a feature
    var showsSpendingInsights = false    // not finished

    static let defaults = HomeFlags()

    enum Key {
        static let cardBanner = Flag<Bool>("home.card_banner")
        static let instantTransfers = Flag<Bool>("home.instant_transfers")
        static let spendingInsights = Flag<Bool>("home.spending_insights")
    }
}

extension HomeFlags {
    /// A key that is missing, or has another type, keeps its default.
    init(_ snapshot: FlagSnapshot) {
        self.init()
        showsCardBanner = snapshot.value(Key.cardBanner) ?? showsCardBanner
        allowsInstantTransfer = snapshot.value(Key.instantTransfers) ?? allowsInstantTransfer
        showsSpendingInsights = snapshot.value(Key.spendingInsights) ?? showsSpendingInsights
    }
}

protocol HomeFlagsProviding {
    /// The values from the last successful fetch, on this device. nil before the first one.
    var lastKnown: HomeFlags? { get }
    func fetch() async throws -> HomeFlags
}

/// The only place in the app that knows about the flag service.
final class RemoteHomeFlags: HomeFlagsProviding {
    init(client: any RemoteFlagsFetching, store: UserDefaults) {
        self.client = client
        self.store = store
    }

    var lastKnown: HomeFlags? {
        store.data(forKey: storeKey).flatMap { try? JSONDecoder().decode(HomeFlags.self, from: $0) }
    }

    func fetch() async throws -> HomeFlags {
        let flags = HomeFlags(try await client.fetchSnapshot())
        store.set(try JSONEncoder().encode(flags), forKey: storeKey)
        return flags
    }

    private let client: any RemoteFlagsFetching
    private let store: UserDefaults
    private let storeKey = "home.flags.lastKnown"
}
```

```swift
import Foundation
import Observation

@Observable
final class HomeViewModel {   // main actor: the target's default isolation
    var balance: Decimal = 1240.50
    var isBalanceHidden = false
    private(set) var flags: HomeFlags

    init(flags provider: any HomeFlagsProviding) {
        self.provider = provider
        flags = provider.lastKnown ?? .defaults   // never wait for the network to draw the screen
    }

    var showsCardBanner: Bool { flags.showsCardBanner }
    var showsInstantTransfer: Bool { flags.allowsInstantTransfer && balance > 0 }
    var showsSpendingInsights: Bool { flags.showsSpendingInsights }

    /// Once per launch. A failure keeps what's on screen, and the next appearance tries again.
    func refreshFlags() async {
        guard !hasFetched else { return }
        do {
            flags = try await provider.fetch()
            hasFetched = true
        } catch is CancellationError {
            // the screen went away: try again next time
        } catch {
            print("[Home] flag service failed, keeping the values on screen: \(error.localizedDescription)")
        }
    }

    @ObservationIgnored private let provider: any HomeFlagsProviding
    @ObservationIgnored private var hasFetched = false
}
```

`RootView` builds the new adapter, and the Home tab fetches when it appears. `WalletApp` no longer calls
`sync()`, and the app no longer imports the legacy SDK:

```swift
struct RootView: View {
    @State private var selectedTab = AppTab.home
    @State private var home: HomeViewModel     // owned here, so it outlives a tab switch

    init(flags: any HomeFlagsProviding = RemoteHomeFlags(client: RemoteFlagsClient(), store: .standard)) {
        _home = State(initialValue: HomeViewModel(flags: flags))
    }

    var body: some View {
        TabView(selection: $selectedTab) {
            Tab("Home", systemImage: "house", value: AppTab.home) {
                NavigationStack {
                    HomeView(viewModel: home)
                        .task { await home.refreshFlags() }
                }
            }
        // ... the Settings tab, unchanged ...
```

I ran it three ways. With the service slowed to 6 seconds in a scratch copy, a first launch shows the defaults
(no banner, instant transfer shown), and the banner appears when the answer lands. With the service down and
values from an earlier launch, the banner is there from the first frame and stays, and the console says:

```
[RemoteFlags] GET /v1/flags?app=wallet
[Home] flag service failed, keeping the values on screen: The flag service is unavailable (503).
```

With the service down on a fresh install, the screen keeps the defaults.
:::

## Part 3 — test it

> "Run the old tests. Then add yours."

::: Now write the tests
The three tests from Part 1 are unchanged. Only their fake learned the new protocol, which is the point of having
a seam. Four new tests cover what the migration decided. There are two fakes. One stands in for the view
model's protocol, and the other for the package's `RemoteFlagsFetching`. The second protocol is `Sendable`, so
under main-actor default isolation its fake has to be `nonisolated`. Each test that touches storage gets its own
`UserDefaults` suite, which is removed afterwards. That's the fix for finding 7, as a helper.

```swift
import Foundation
import Testing
import FlagsKit
@testable import Wallet

/// The view model's seam. `lastKnown` is what this device saw last; `fetch()` returns `result`.
private final class FakeFlags: HomeFlagsProviding {
    var lastKnown: HomeFlags?
    var result: Result<HomeFlags, any Error>

    init(flags: HomeFlags?, fetching result: Result<HomeFlags, any Error>? = nil) {
        lastKnown = flags
        self.result = result ?? .success(flags ?? .defaults)
    }

    func fetch() async throws -> HomeFlags { try result.get() }
}

/// The package's seam. It's Sendable, so under main-actor default isolation the fake is nonisolated.
nonisolated private struct FakeClient: RemoteFlagsFetching {
    var result: Result<FlagSnapshot, RemoteFlagsError>
    func fetchSnapshot() async throws -> FlagSnapshot { try result.get() }
}

/// A UserDefaults of its own for each test, removed afterwards: nothing leaks into the next test.
private func withStore(_ body: (UserDefaults) async throws -> Void) async rethrows {
    let name = "WalletTests.\(UUID().uuidString)"
    let store = UserDefaults(suiteName: name)!
    defer { store.removePersistentDomain(forName: name) }
    try await body(store)
}

// The three tests from Part 1. Their bodies didn't change in the migration: only the fake did.
struct HomeViewModelTests {

    @Test func showsInstantTransferWithAPositiveBalance() {
        let viewModel = HomeViewModel(flags: FakeFlags(flags: HomeFlags(allowsInstantTransfer: true)))
        #expect(viewModel.showsInstantTransfer)
    }

    @Test func hidesInstantTransferWhenTheFlagIsOff() {
        let viewModel = HomeViewModel(flags: FakeFlags(flags: HomeFlags(allowsInstantTransfer: false)))
        #expect(!viewModel.showsInstantTransfer)
    }

    @Test func hidesInstantTransferWithAnEmptyBalance() {
        let viewModel = HomeViewModel(flags: FakeFlags(flags: HomeFlags(allowsInstantTransfer: true)))
        viewModel.balance = 0
        #expect(!viewModel.showsInstantTransfer)
    }
}

struct FlagMigrationTests {

    @Test func theFirstLaunchShowsEachFlagsDefaultWhileLoading() {
        let viewModel = HomeViewModel(flags: FakeFlags(flags: nil))
        #expect(viewModel.flags == .defaults)
        #expect(viewModel.showsInstantTransfer)       // shipped: on unless the server says off
        #expect(!viewModel.showsSpendingInsights)     // unfinished: off unless the server says on
    }

    @Test func aFailedFetchKeepsTheLastKnownValues() async {
        let lastKnown = HomeFlags(showsCardBanner: true, allowsInstantTransfer: false, showsSpendingInsights: false)
        let viewModel = HomeViewModel(flags: FakeFlags(flags: lastKnown, fetching: .failure(RemoteFlagsError.timedOut)))
        await viewModel.refreshFlags()
        #expect(viewModel.flags == lastKnown)
    }

    @Test func aFetchIsRememberedForTheNextLaunch() async {
        await withStore { store in
            let snapshot = FlagSnapshot(["home.card_banner": .bool(true), "home.instant_transfers": .bool(false),
                                         "home.spending_insights": .bool(true)])
            let today = RemoteHomeFlags(client: FakeClient(result: .success(snapshot)), store: store)
            let viewModel = HomeViewModel(flags: today)
            await viewModel.refreshFlags()

            let tomorrow = RemoteHomeFlags(client: FakeClient(result: .failure(.unavailable(status: 503))), store: store)
            #expect(tomorrow.lastKnown == viewModel.flags)
            #expect(HomeViewModel(flags: tomorrow).showsSpendingInsights)
        }
    }

    @Test func aMissingOrMistypedKeyKeepsItsDefault() async throws {
        try await withStore { store in
            let snapshot = FlagSnapshot(["home.card_banner": .bool(true), "home.instant_transfers": .string("yes")])
            let provider = RemoteHomeFlags(client: FakeClient(result: .success(snapshot)), store: store)
            let flags = try await provider.fetch()
            #expect(flags == HomeFlags(showsCardBanner: true, allowsInstantTransfer: true, showsSpendingInsights: false))
        }
    }
}
```

All seven pass. `aFetchIsRememberedForTheNextLaunch` uses the real adapter with a fake client, so it tests the
round trip through storage, not a mock of it.
:::

::: What I'd ask next
- **"People upgrading from the old version."** On their first launch after the update, there are no last known
  values, but the legacy keys are still in `UserDefaults`. Read them once into `lastKnown`, then delete them, so
  an upgrade doesn't show the defaults for a second.
- **"Insights is causing crashes. Turn it off now, without a release."** That's a kill switch. Fetching once per
  launch isn't enough: refresh when the app becomes active (`scenePhase`), and for this one flag, apply a change
  to off at once, even mid-session.
- **"Run an A/B test on the banner."** The user must stay in the same group every time. Log the exposure when the
  banner is actually shown, not when the flags are fetched.
- **"Ten screens need flags now."** Fetch once at launch into one shared store, and give each feature its own small
  value type like `HomeFlags`. Don't fetch for every screen.
- **"The service is slow, not down."** The client times out after 3 seconds. If it didn't, the `.task` would wait
  forever. Say where you'd put the timeout if the client had none: race the fetch against `Task.sleep` in a task
  group, and cancel the loser.
:::
