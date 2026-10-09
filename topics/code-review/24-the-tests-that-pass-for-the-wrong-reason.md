---
title: 24 · The tests that pass for the wrong reason
summary: A PR that only adds tests — green on the author's Mac, red on CI once a day. Review the tests themselves, fix them minimally, then write the one that was missing.
minutes: 20
group: Review this PR
sources:
- Apple · Asynchronous tests and expectations | https://developer.apple.com/documentation/xctest/asynchronous-tests-and-expectations
- Apple · wait(for:timeout:enforceOrder:) | https://developer.apple.com/documentation/xctest/xctestcase/wait(for:timeout:enforceorder:)
- Apple · XCTAssertEqual | https://developer.apple.com/documentation/xctest/xctassertequal
- Apple · Migrating a test from XCTest to Swift Testing | https://developer.apple.com/documentation/testing/migratingfromxctest
- Point-Free · swift-snapshot-testing — record modes, traits and devices | https://github.com/pointfreeco/swift-snapshot-testing
- Martin Fowler · Eradicating non-determinism in tests | https://martinfowler.com/articles/nonDeterminism.html
---

*Shape: review this PR · Reported: a common senior-round topic; no specific company report found ·
Verified: the PR's seven XCTest tests were run as written (6 pass; the network test fails offline);
the fixed file and the new tests ran with Swift 6.4; the snapshot test is reviewed, not run*

> "This PR only adds tests for the product screen. The author says they're all green on their Mac.
> CI goes red about once a day and nobody knows why. Review the tests — not the code under test."

The code under test, for context (not part of the PR):

```swift
final class ProductViewModel {
    private(set) var title = ""
    private(set) var price = ""
    private(set) var errorMessage: String?
    var onChange: (() -> Void)?            // called twice per load: "loading", then "done"

    init(loader: ProductLoading, analytics: AnalyticsTracking) { … }

    func load(id: String)                  // the real ProductLoader replies on URLSession's queue
    func retry()                           // loads the last id again; does nothing before a load
}

final class FavouritesStore {
    static let shared = FavouritesStore()
    private(set) var ids: [String] = []
    init() {}
    func toggle(_ id: String) { … }
}
```

The PR:

```swift
import XCTest
import SnapshotTesting
@testable import Shop

final class ProductViewModelTests: XCTestCase {
    let analytics = AnalyticsSpy()

    func testLoadShowsTitle() {
        let viewModel = ProductViewModel(loader: ProductLoader(), analytics: analytics)
        viewModel.load(id: "42")
        sleep(2)
        XCTAssertTrue(viewModel.title == "Coffee grinder")
    }

    func testLoadFailureShowsError() {
        let loader = LoaderStub(result: .failure(URLError(.notConnectedToInternet)))
        let viewModel = ProductViewModel(loader: loader, analytics: analytics)
        let failed = XCTestExpectation(description: "failed")
        viewModel.onChange = { failed.fulfill() }
        viewModel.load(id: "42")
        XCTAssertEqual(viewModel.errorMessage, "No connection")
    }

    func testPriceIsFormatted() {
        let viewModel = ProductViewModel(loader: LoaderStub(result: .success(.grinder)), analytics: analytics)
        let loaded = expectation(description: "loaded")
        loaded.assertForOverFulfill = false
        viewModel.onChange = { loaded.fulfill() }
        viewModel.load(id: "42")
        wait(for: [loaded], timeout: 1)
        XCTAssertEqual(viewModel.price, "€89.00")
    }

    func testLoadTracksAnalytics() {
        let viewModel = ProductViewModel(loader: LoaderStub(result: .success(.grinder)), analytics: analytics)
        viewModel.load(id: "42")
        XCTAssertEqual(analytics.events.count, 1)
    }

    func testFavouritesStartEmpty() {
        XCTAssertTrue(FavouritesStore.shared.ids.isEmpty)
    }

    func testFavouritesToggleAdds() {
        FavouritesStore.shared.toggle("42")
        XCTAssertEqual(FavouritesStore.shared.ids.first!, "42")
    }

    func testRetry() {
        let viewModel = ProductViewModel(loader: LoaderStub(result: .success(.grinder)), analytics: analytics)
        viewModel.retry()
    }
}

final class ProductCardSnapshotTests: XCTestCase {
    func testProductCard() {
        isRecording = true
        let card = ProductCardView(product: .grinder)
        card.frame = CGRect(x: 0, y: 0, width: 375, height: 120)
        assertSnapshot(of: card, as: .image)
    }
}

// LoaderStub calls completion(result) straight away. AnalyticsSpy appends to `events`.
```

::: A hint, if you're stuck
- For each test ask: *what change to the app would make this test fail?* If the answer is "none",
  it's not a test.
- Which of these talk to something outside the process? Which read a clock?
- `onChange` is called twice per load. What does each expectation do with that?
- Run the file in a different order, twice in a row, and on a German Mac. What changes?
:::

::: The key — what I expect a senior to find
1. **`first!` can crash the whole run.** If the toggle test runs twice in one process (Xcode's
   "Run repeatedly", or test iterations), the second toggle *removes* "42", `ids` is empty, and the
   crash ends every remaining test with no results. `XCTUnwrap` fails only this test.
2. **A real network call, then `sleep(2)`.** The test depends on Wi-Fi, the server and its data,
   and guesses that two seconds is enough. It also reads `title` while URLSession's queue may be
   writing it — a data race. I ran it offline: it failed after 2.2 seconds. Use the stub.
3. **An expectation nobody waits for.** `XCTestExpectation(description:)` made by hand isn't
   tracked by the test case, so never waiting on it is silently fine. The test passes only because
   the stub replies synchronously; make the loader reply later and the assertion runs first. Use
   `expectation(description:)` and `wait(for:)` — XCTest then also fails a forgotten wait (I
   checked: "Failed due to unwaited expectation").
4. **Fulfilled twice, and the warning switched off.** `onChange` fires for "loading" and again for
   "done". Without `assertForOverFulfill = false`, XCTest stops the test with "API violation —
   multiple calls made to fulfill" (checked). Turned off, `wait` returns on the *first* call, before
   the price exists. It passes only because the stub is synchronous. Fulfill when the thing you
   care about happens.
5. **`testRetry` asserts nothing.** It can't fail. And `retry()` before any load does nothing, so
   it doesn't even run the code it's named after.
6. **The snapshot is in record mode.** With `isRecording = true` the assertion never compares; it
   writes a new reference and fails every run ("Record mode is on…", from the library's source).
   Worse, `isRecording` is a global: set in one test, it flips every snapshot test that runs after.
7. **Shared state through a singleton.** `FavouritesStore.shared` lives for the whole run, so one
   test's toggle is the next test's starting point. The store has a public `init()` — use a new one.
8. **Order dependence.** The pair passes only because XCTest runs methods alphabetically:
   "StartEmpty" before "ToggleAdds". Turn on random order and it fails about half the time.
9. **A locale-dependent assertion.** `"€89.00"` is the US format. On a German machine the view
   model shows `89,00 €` (checked), so this fails on a CI box with a different region.
10. **The snapshot has no fixed device.** The size is set, but scale, light or dark, and text size
    come from whatever simulator runs it. A reference recorded on one Mac fails on another. Pass
    `traits` and pin the simulator and OS on CI.
11. **Counting calls instead of checking them.** `events.count == 1` passes if the app tracks
    `productFailed`, or the wrong id. Assert the events themselves.
12. **`XCTAssertTrue(a == b)`.** On failure it says only "XCTAssertTrue failed" — I got exactly
    that line. `XCTAssertEqual(a, b)` prints both values.
13. **Not a bug: `let analytics = AnalyticsSpy()`.** It looks shared, but XCTest makes a new
    instance of the test case for every test method, so every test gets its own spy. Say so — it
    shows you know the lifecycle, and it stops a pointless change.
:::

::: The idea behind it
A test has one job: **fail when the behaviour breaks, and only then.** Every finding here breaks
one half of that sentence.

*Tests that can't fail* — a test with no assertion, an expectation nobody waits for, a check that
runs before the result exists, a snapshot that records instead of comparing. They are green
forever and protect nothing. The question that catches them: *what change to the app would turn
this red?*

*Tests that fail for no reason* — they are **non-deterministic**: the result depends on something
outside the code. The network, the clock (`sleep`), another test's leftovers (a singleton), the run
order, the machine's region, the simulator's screen. A test that is red one run in twenty teaches
the team to press "re-run", and then real failures get re-run too.

The cure for both is the same: **the test controls every input.** A stub instead of the network,
a waited expectation (or a synchronous stub) instead of a sleep, a fresh object instead of a
singleton, an explicit locale and explicit traits. Then a failure means one thing: the code changed.

Finally, assert **behaviour**, not how the code got there. "These analytics events were sent" is a
behaviour. "Something was called once" is a guess about the code.
:::

::: The fix
The tests change; the code under test gets one line: an injected `locale` (key 9).

```swift
// ProductViewModel: init(loader:analytics:locale: Locale = .current), and
// price = product.price.formatted(.currency(code: "EUR").locale(locale))              // key 9

final class ProductViewModelTests: XCTestCase {
    let analytics = AnalyticsSpy()                     // fine: a new instance per test (key 13)

    func testLoadShowsTitle() {
        let viewModel = ProductViewModel(loader: LoaderStub(result: .success(.grinder)), analytics: analytics)  // key 2
        viewModel.load(id: "42")
        XCTAssertEqual(viewModel.title, "Coffee grinder")                                      // key 12
    }

    func testLoadFailureShowsError() {
        let loader = LoaderStub(result: .failure(URLError(.notConnectedToInternet)))
        let viewModel = ProductViewModel(loader: loader, analytics: analytics)
        let failed = expectation(description: "failed")                                       // key 3
        viewModel.onChange = { if viewModel.errorMessage != nil { failed.fulfill() } }        // key 4
        viewModel.load(id: "42")
        wait(for: [failed], timeout: 1)
        XCTAssertEqual(viewModel.errorMessage, "No connection")
    }

    func testPriceIsFormatted() {
        let viewModel = ProductViewModel(loader: LoaderStub(result: .success(.grinder)), analytics: analytics,
                                         locale: Locale(identifier: "en_US"))                 // key 9
        viewModel.load(id: "42")                    // the stub is synchronous: nothing to wait for (key 4)
        XCTAssertEqual(viewModel.price, "€89.00")
    }

    func testLoadTracksAnalytics() {
        let viewModel = ProductViewModel(loader: LoaderStub(result: .success(.grinder)), analytics: analytics)
        viewModel.load(id: "42")
        XCTAssertEqual(analytics.events, [.productViewed(id: "42")])                           // key 11
    }

    func testFavouritesStartEmpty() {
        XCTAssertTrue(FavouritesStore().ids.isEmpty)                                           // key 7, 8
    }

    func testFavouritesToggleAdds() throws {
        let store = FavouritesStore()                                                          // key 7, 8
        store.toggle("42")
        XCTAssertEqual(try XCTUnwrap(store.ids.first), "42")                                   // key 1
    }

    // testRetry deleted: it asserted nothing. Its replacement is in "Now add the missing test". // key 5
}

final class ProductCardSnapshotTests: XCTestCase {
    @MainActor                                     // UIKit traits are main-actor
    func testProductCard() {
        let card = ProductCardView(product: .grinder)                                          // key 6: no isRecording
        let traits = UITraitCollection { traits in                                             // key 10
            traits.displayScale = 3
            traits.userInterfaceStyle = .light
            traits.preferredContentSizeCategory = .large
        }
        assertSnapshot(of: card, as: .image(size: CGSize(width: 375, height: 120), traits: traits))
    }
}
```

**Said out loud, not coded:** a separate, opt-in integration test for the real `ProductLoader`
against a local stub server; a dark-mode and an accessibility-size snapshot; recording snapshots
only with `withSnapshotTesting(record: .failed)` on a developer's machine; random test order on CI
(the scheme's "Randomize execution order"); migrating to Swift Testing later.

Why each piece:

- **The stub stays synchronous.** A synchronous stub is the simplest deterministic test, and then
  most tests need no expectation at all. The failure test keeps a real one, fulfilled only when the
  error exists, so it still works if the stub ever replies later.
- **A fresh `FavouritesStore()` per test** fixes keys 7 and 8 together: no shared state, so order
  can't matter.
- **One production change, the `locale` parameter.** It has a default, so no caller changes, and
  the test no longer depends on the machine.

If the team moves to Swift Testing, the same ideas map one-to-one:

| XCTest | Swift Testing |
|---|---|
| `XCTAssertEqual(a, b)` | `#expect(a == b)` — prints both sides |
| `try XCTUnwrap(x)` | `try #require(x)` |
| `expectation` + `wait(for:)` | `await confirmation { … }`, or just `await` the async call |
| a new `XCTestCase` instance per test | a new suite instance per test |
| alphabetical order unless randomized | random order, in parallel, by default |
:::

::: Now add the missing test
> "Good. `testRetry` tested nothing. Write the test it should have been."

**What I'd test, and why**

1. **Retry after a failure shows the product** — the behaviour Retry exists for: the first load
   fails, the network comes back, Retry loads the *same* id, the error clears, and analytics sees
   both attempts.
2. **Retry before any load does nothing** — the edge the old test was accidentally running. Now
   it asserts it: no product, no events.

**The seam.** The existing `LoaderStub`, with its `result` made a `var`, so the test can change the
answer between the first load and the retry. Nothing else is new.

```swift
import XCTest
@testable import Shop

final class ProductViewModelRetryTests: XCTestCase {
    func testRetryAfterAFailureShowsTheProduct() {
        // Given a load that failed
        let loader = LoaderStub(result: .failure(URLError(.notConnectedToInternet)))
        let analytics = AnalyticsSpy()
        let viewModel = ProductViewModel(loader: loader, analytics: analytics)
        viewModel.load(id: "42")
        XCTAssertEqual(viewModel.errorMessage, "No connection")

        // When the network is back and the user taps Retry
        loader.result = .success(.grinder)
        viewModel.retry()

        // Then the same product loads, and the error is gone
        XCTAssertEqual(viewModel.title, "Coffee grinder")
        XCTAssertNil(viewModel.errorMessage)
        XCTAssertEqual(analytics.events, [.productFailed(id: "42"), .productViewed(id: "42")])
    }

    func testRetryBeforeAnyLoadDoesNothing() {
        let analytics = AnalyticsSpy()
        let viewModel = ProductViewModel(loader: LoaderStub(result: .success(.grinder)), analytics: analytics)

        viewModel.retry()

        XCTAssertEqual(viewModel.title, "")
        XCTAssertEqual(analytics.events, [])
    }
}
```

Ran with Swift 6.4: 8 tests (the fixed file's 6 and these 2), all passed.
:::

::: What I'd ask next
- *"When is `sleep` in a test acceptable?"* — Practically never in a unit test. If the code waits on
  time, inject the clock or the delay (a `debounce: .zero`, a fake sleeper) so the test controls it.
- *"How do you find flaky tests you already have?"* — Run the suite repeatedly with random order on
  CI ("Run repeatedly" in Xcode, or test iterations), and track which tests fail without a code
  change. Quarantine them with a ticket; don't just re-run.
- *"Are snapshot tests worth it?"* — For layout regressions that unit tests can't see, yes, with
  fixed traits, one pinned simulator, and references reviewed like code. Not for logic.
- *"Should you mock analytics at all?"* — A spy that records events is fine: "this event was sent"
  is the behaviour the product team cares about. Asserting *which* events, not how many, keeps it a
  behaviour test.
- *"What makes a good test name?"* — The behaviour and the expected outcome, so a red test reads as
  a bug report: `testRetryAfterAFailureShowsTheProduct`, not `testRetry`.
:::
