---
title: 08 · The ad that clicks itself
summary: A feed with an ad cell whose tap handlers pile up on reused cells — find why ads open when nobody tapped them, and why clicks are counted twice.
minutes: 20
group: Find the bug
sources:
- Blind · eBay iOS debugging round — "why does the ad keep clicking when user didn't click it" | https://www.teamblind.com/post/ebay-ios-debugging-round-mb2odkpv
---

*Shape: find the bug · Reported: eBay — a debugging round built around "why does the ad keep
clicking when user didn't click it" · UIKit — the fix typechecks against the iOS SDK (iOS 18
target) in Swift 6 mode; the handler pile-up and the fix were run on a single cell in the iOS
simulator, the rest checked by hand*

> "This is our home feed. Posts, with an ad every few rows. Users say an ad sometimes opens when
> they tapped a normal post, and the ads team says our click numbers are higher than the ad
> network's. Every so often it crashes after pull-to-refresh. Find out why."

```swift
final class FeedCell: UITableViewCell {
    let titleLabel = UILabel()
    let ctaButton = UIButton(type: .system)
    var onTap: (() -> Void)?

    @objc func cardTapped() { onTap?() }
}

final class FeedViewController: UITableViewController {
    private var items: [FeedItem] = []          // enum FeedItem { case post(Post), ad(Ad) }
    private let analytics = Analytics.shared

    override func tableView(_ tableView: UITableView, numberOfRowsInSection section: Int) -> Int {
        items.count
    }

    override func tableView(_ tableView: UITableView, cellForRowAt indexPath: IndexPath) -> UITableViewCell {
        let cell = tableView.dequeueReusableCell(withIdentifier: "FeedCell", for: indexPath) as! FeedCell
        switch items[indexPath.row] {
        case .post(let post):
            cell.titleLabel.text = post.title
            cell.ctaButton.isHidden = true
        case .ad(let ad):
            cell.titleLabel.text = ad.headline
            cell.ctaButton.isHidden = false
            cell.ctaButton.setTitle(ad.callToAction, for: .normal)
            cell.ctaButton.addAction(UIAction { [weak self] _ in
                self?.openAd(at: indexPath)
            }, for: .touchUpInside)
            let tap = UITapGestureRecognizer(target: cell, action: #selector(FeedCell.cardTapped))
            cell.contentView.addGestureRecognizer(tap)
            cell.onTap = { [weak self] in
                self?.openAd(at: indexPath)
            }
        }
        return cell
    }

    override func tableView(_ tableView: UITableView, willDisplay cell: UITableViewCell,
                            forRowAt indexPath: IndexPath) {
        if case .ad(let ad) = items[indexPath.row] {
            analytics.track("ad_impression", ["id": ad.id])
        }
    }

    override func tableView(_ tableView: UITableView, didSelectRowAt indexPath: IndexPath) {
        if case .post(let post) = items[indexPath.row] {
            show(PostViewController(post: post), sender: self)
        }
    }

    func didRefresh(with newItems: [FeedItem]) {
        items = newItems
        tableView.reloadData()
    }

    private func openAd(at indexPath: IndexPath) {
        guard case .ad(let ad) = items[indexPath.row] else { return }
        analytics.track("ad_click", ["id": ad.id, "position": indexPath.row])
        UIApplication.shared.open(ad.url)
    }
}
```

This compiles cleanly in Swift 6 mode (checked, with small stubs for `Post`, `Ad` and a
main-actor `Analytics`). Nothing here is a compiler problem. It's a lifecycle problem.

::: A hint, if you're stuck
- How many `FeedCell` objects exist when 200 rows have scrolled past? Fewer than you think.
- Read the `.post` branch and list what it *doesn't* reset.
- `addAction` and `addGestureRecognizer` both *add*. What removes?
- `indexPath` is captured when the cell is configured. When is the closure run?
:::

::: The key — what I expect a senior to find
1. **The crash after refresh: a stale `indexPath`.** Each closure captures the row number from the
   moment it was configured. Refresh to a shorter feed, tap a button that still carries an old
   closure, and `items[indexPath.row]` reads past the end — out of range, crash. Look the item up
   at tap time instead, by its id.
2. **Posts open ads (the reported bug).** There is one cell class and one reuse identifier for
   both kinds of row. A cell that once showed an ad keeps its tap recogniser and its `onTap` when
   the table reuses it for a post, because the `.post` branch resets neither. The user taps the
   post and the old ad opens and logs a click. Worse, a tap recogniser on `contentView` cancels the
   touch, so `didSelectRowAt` never runs and the post they wanted doesn't open either.
3. **Handlers pile up: one tap, several clicks.** `addAction` adds a new closure every time the cell
   is configured as an ad, and never removes the old ones. I ran exactly these steps on one cell
   reused for rows 2, 9 and 16: a single tap logged `ad_click` for `[2, 9, 16]` — three clicks,
   three `open` calls, two of them for ads no longer on screen. That is the inflated click count.
   The gesture recognisers pile up the same way; after three configures the three added
   recognisers were all still on the cell.
4. **Clicks for the wrong ad.** Even when it doesn't crash, a stale row number after a refresh
   points at a different item. If that item is now an ad, the wrong ad opens and the wrong
   advertiser is billed. Invalid clicks are what ad networks penalise.
5. **Impressions counted on every appearance.** `willDisplay` runs every time the cell scrolls back
   on screen and again after `reloadData()`. Scroll past one ad five times and you log five
   impressions. Count each ad once per feed session (a `Set` of ids); real ad SDKs also wait until
   about half the ad has been visible for a second.
6. **No `prepareForReuse`, no per-kind cell.** The cell has no place where leftover state is
   cleared. Give ads their own `AdCell` with its own reuse identifier, and clear the closure in
   `prepareForReuse`.
7. **Handlers wired in the wrong place.** Wiring belongs in the cell's `init` (or
   `awakeFromNib`), once. `cellForRow` should only *set* values, never *add* things.
8. **Untestable side effects.** `Analytics.shared` and `UIApplication.shared` are reached
   directly, so no test can check "one tap, one click". Inject a tracker and a URL-opening closure.
9. **Note: `addTarget` would have hidden this.** I checked: adding the same target and selector
   twice to a `UIControl` keeps one entry. A fresh `UIAction` closure has no such dedupe (unless you
   give it the same `identifier`), so switching to closures is what made this bug appear.
:::

::: The idea behind it
A table view doesn't make one cell per row. It makes roughly a screenful and *reuses* them: when a
row scrolls off the top, its cell is put in a pool, and the next row coming in from the bottom
gets that same object back from `dequeueReusableCell`. This is *cell reuse*, and it's why a feed of
10,000 rows stays light.

The catch is that a reused cell still carries everything you did to it last time. Setting a
property is safe: the next configure overwrites it. *Adding* something is not: an added action, an
added gesture recogniser or an added subview stays, and the next configure adds another on top.

Think of a hotel room. Housekeeping changes the sheets for each guest — that's setting a value.
But if a guest booked a 6 a.m. wake-up call and nobody cancels it, the next guest gets woken at 6
too. `prepareForReuse` is housekeeping: the one place to cancel what the last guest set up.

The second half is time. A closure that captures `indexPath` remembers a row *number*, not a row.
When the data changes, the number points somewhere else. Remember the item's identity and look it
up when the tap actually happens.
:::

::: The fix
```swift
@MainActor
protocol AdTracking {
    func adImpression(_ ad: Ad, position: Int)
    func adClicked(_ ad: Ad, position: Int)
}

final class AdCell: UITableViewCell {
    static let reuseID = "AdCell"

    private let headlineLabel = UILabel()
    private let ctaButton = UIButton(type: .system)
    private var onCTATap: (() -> Void)?

    override init(style: UITableViewCell.CellStyle, reuseIdentifier: String?) {
        super.init(style: style, reuseIdentifier: reuseIdentifier)
        // Layout omitted. The button gets exactly one action, for the cell's whole life.
        ctaButton.addAction(UIAction { [weak self] _ in self?.onCTATap?() }, for: .touchUpInside)
    }

    required init?(coder: NSCoder) { fatalError("init(coder:) is not used") }

    override func prepareForReuse() {
        super.prepareForReuse()
        onCTATap = nil
        headlineLabel.text = nil
    }

    func configure(with ad: Ad, onCTATap: @escaping () -> Void) {
        headlineLabel.text = ad.headline
        ctaButton.setTitle(ad.callToAction, for: .normal)
        self.onCTATap = onCTATap
    }
}

final class FeedViewController: UITableViewController {
    private var items: [FeedItem] = []
    private var loggedImpressions: Set<Ad.ID> = []
    private let tracker: AdTracking
    private let openURL: (URL) -> Void

    init(tracker: AdTracking, openURL: @escaping (URL) -> Void) {
        self.tracker = tracker
        self.openURL = openURL
        super.init(style: .plain)
    }

    required init?(coder: NSCoder) { fatalError("init(coder:) is not used") }

    override func viewDidLoad() {
        super.viewDidLoad()
        tableView.register(PostCell.self, forCellReuseIdentifier: PostCell.reuseID)
        tableView.register(AdCell.self, forCellReuseIdentifier: AdCell.reuseID)
    }

    override func tableView(_ tableView: UITableView, numberOfRowsInSection section: Int) -> Int {
        items.count
    }

    override func tableView(_ tableView: UITableView, cellForRowAt indexPath: IndexPath) -> UITableViewCell {
        switch items[indexPath.row] {
        case .post(let post):
            let cell = tableView.dequeueReusableCell(withIdentifier: PostCell.reuseID, for: indexPath) as! PostCell
            cell.configure(with: post)
            return cell
        case .ad(let ad):
            let cell = tableView.dequeueReusableCell(withIdentifier: AdCell.reuseID, for: indexPath) as! AdCell
            cell.configure(with: ad) { [weak self] in self?.openAd(id: ad.id) }
            return cell
        }
    }

    override func tableView(_ tableView: UITableView, willDisplay cell: UITableViewCell,
                            forRowAt indexPath: IndexPath) {
        guard case .ad(let ad) = items[indexPath.row],
              loggedImpressions.insert(ad.id).inserted else { return }
        tracker.adImpression(ad, position: indexPath.row)
    }

    override func tableView(_ tableView: UITableView, didSelectRowAt indexPath: IndexPath) {
        tableView.deselectRow(at: indexPath, animated: true)
        switch items[indexPath.row] {
        case .post(let post): show(PostViewController(post: post), sender: self)
        case .ad(let ad): openAd(id: ad.id)
        }
    }

    func didRefresh(with newItems: [FeedItem]) {
        items = newItems
        loggedImpressions.removeAll()   // a new feed session counts impressions afresh
        tableView.reloadData()
    }

    private func openAd(id: Ad.ID) {
        // Look the ad up now, at tap time, not by a row number remembered earlier.
        guard let position = items.firstIndex(where: { $0.adID == id }),
              case .ad(let ad) = items[position] else { return }
        tracker.adClicked(ad, position: position)
        openURL(ad.url)
    }
}

private extension FeedItem {
    var adID: Ad.ID? {
        if case .ad(let ad) = self { ad.id } else { nil }
    }
}
```

What the simulator run showed: the same `AdCell` configured for three different ads, then tapped
once, logged a click for the last ad only (`["c"]`); after `prepareForReuse` a tap logged nothing.

Why each piece:

- **The action is added once, in `init`.** The cell owns one permanent action that calls whatever
  closure it currently holds. Configuring swaps the closure; it never adds a handler.
- **`prepareForReuse` clears the closure.** A cell waiting in the pool can't open anything.
- **A separate `AdCell` and `PostCell`.** A post can never inherit ad behaviour, because a post is
  never shown in an ad cell.
- **The whole-card tap goes through `didSelectRowAt`.** The table hands you the *current* index
  path at tap time, so there is no gesture recogniser to leak and no swallowed selection.
- **`openAd(id:)` looks the ad up by id.** After a refresh it finds the ad wherever it now is, or
  does nothing if it's gone. No stale row, no out-of-range crash.
- **`loggedImpressions`** turns "every time it appears" into "once per feed session".
- **Injected `tracker` and `openURL`.** A test can tap and assert exactly one `adClicked`.
:::

::: Now write the tests
> "Good. Now write me the tests that would have caught the inflated click numbers."

**What I'd test, and why**

1. **One tap after three configures clicks only the last ad.** The cell is reused for ads a, b and
   c; one tap opens c, once. This is the pile-up bug, so it goes first.
2. **A cell waiting for reuse opens nothing** — `prepareForReuse` really clears the handler.
3. **An impression is logged once per ad per session** — scrolling past three times counts once; a
   refresh starts a new session.
4. **A tap after a refresh opens the ad where it is now** — the ad moved from row 1 to row 0; the
   click reports position 0 and opens the right URL. That's the stale-`indexPath` bug.
5. **A tap on an ad the refresh removed does nothing** — no click, no open, and no out-of-range crash.

I wouldn't test the layout or UIKit's touch handling; `sendActions(for: .touchUpInside)` stands in
for the finger.

**The seam.** The screen takes an `AdTracking` and an `openURL` closure in `init`, so the test passes
*fakes*: a tracker that writes down every event, and a closure that records which URL it was asked
to open. Nothing reaches a real ad SDK or Safari. The button is private, so the test finds it with
`Mirror` — Swift's built-in way to look at an object's stored properties — instead of making it
public just for tests. (With the fix in a separate module you'd mark it `internal` and use
`@testable import`.) `Ad`, `Post` and `FeedItem` are small stand-ins for the app's models.

```swift
import Testing
import UIKit

// A fake tracker: it only writes down what it was told.
@MainActor
final class FakeAdTracker: AdTracking {
    enum Event: Equatable {
        case impression(Ad.ID, position: Int)
        case click(Ad.ID, position: Int)
    }
    private(set) var events: [Event] = []

    func adImpression(_ ad: Ad, position: Int) { events.append(.impression(ad.id, position: position)) }
    func adClicked(_ ad: Ad, position: Int) { events.append(.click(ad.id, position: position)) }
}

extension AdCell {
    // The button is private. Mirror lets the test reach it without changing the cell.
    var ctaButtonForTest: UIButton? { Mirror(reflecting: self).descendant("ctaButton") as? UIButton }
}

func makeAd(_ id: String) -> Ad {
    Ad(id: id, headline: "Ad \(id)", callToAction: "Open", url: URL(string: "https://ads.example.com/\(id)")!)
}

@MainActor
struct AdCellTests {
    @Test func oneTapAfterThreeConfiguresClicksOnlyTheLastAd() throws {
        // Given one cell reused for three ads
        let cell = AdCell(style: .default, reuseIdentifier: AdCell.reuseID)
        var opened: [Ad.ID] = []
        for id in ["a", "b", "c"] {
            cell.configure(with: makeAd(id)) { opened.append(id) }
        }

        // When the user taps the button once
        try #require(cell.ctaButtonForTest).sendActions(for: .touchUpInside)

        // Then exactly one ad opens: the one on screen
        #expect(opened == ["c"])
    }

    @Test func cellWaitingForReuseOpensNothing() throws {
        let cell = AdCell(style: .default, reuseIdentifier: AdCell.reuseID)
        var opened: [Ad.ID] = []
        cell.configure(with: makeAd("a")) { opened.append("a") }

        cell.prepareForReuse()
        try #require(cell.ctaButtonForTest).sendActions(for: .touchUpInside)

        #expect(opened.isEmpty)
    }
}

@MainActor
struct FeedViewControllerTests {
    let tracker = FakeAdTracker()
    let post = FeedItem.post(Post(title: "Hello"))
    let adA = makeAd("a")

    func makeFeed(opening opened: @escaping (URL) -> Void = { _ in }) -> FeedViewController {
        let feed = FeedViewController(tracker: tracker, openURL: opened)
        feed.loadViewIfNeeded()                // registers the cells
        return feed
    }

    @Test func impressionIsLoggedOncePerAdPerSession() {
        let feed = makeFeed()
        feed.didRefresh(with: [post, .ad(adA)])
        let row1 = IndexPath(row: 1, section: 0)

        // The ad scrolls on screen three times
        for _ in 0..<3 {
            feed.tableView(feed.tableView, willDisplay: UITableViewCell(), forRowAt: row1)
        }
        #expect(tracker.events == [.impression("a", position: 1)])

        // A refresh starts a new session, so the ad counts once more
        feed.didRefresh(with: [post, .ad(adA)])
        feed.tableView(feed.tableView, willDisplay: UITableViewCell(), forRowAt: row1)
        #expect(tracker.events == [.impression("a", position: 1), .impression("a", position: 1)])
    }

    @Test func tapAfterRefreshOpensTheAdWhereItIsNow() throws {
        // Given an ad cell configured while the ad was in row 1
        var opened: [URL] = []
        let feed = makeFeed { opened.append($0) }
        feed.didRefresh(with: [post, .ad(adA)])
        let cell = try #require(feed.tableView(feed.tableView, cellForRowAt: IndexPath(row: 1, section: 0)) as? AdCell)

        // When a refresh moves the ad to row 0, and then the user taps
        feed.didRefresh(with: [.ad(adA), post])
        try #require(cell.ctaButtonForTest).sendActions(for: .touchUpInside)

        // Then the same ad opens, with its current position
        #expect(tracker.events == [.click("a", position: 0)])
        #expect(opened == [adA.url])
    }

    @Test func tapOnAnAdThatARefreshRemovedDoesNothing() throws {
        var opened: [URL] = []
        let feed = makeFeed { opened.append($0) }
        feed.didRefresh(with: [post, .ad(adA)])
        let cell = try #require(feed.tableView(feed.tableView, cellForRowAt: IndexPath(row: 1, section: 0)) as? AdCell)

        feed.didRefresh(with: [post])          // the ad is gone, and the feed is shorter
        try #require(cell.ctaButtonForTest).sendActions(for: .touchUpInside)

        #expect(tracker.events.isEmpty)        // and no out-of-range crash
        #expect(opened.isEmpty)
    }
}
```

Ran on the iOS Simulator (iOS 18.5, Swift 6 mode): 5 tests, all passed.
:::

::: What I'd ask next
- *"How would you have found this without reading the code?"* — Put a breakpoint in `openAd` and
  tap once. If it's hit three times, look at the backtrace: three separate closures. Or log
  `ctaButton.enumerateEventHandlers` in the cell (iOS 14+) to count what's attached.
- *"Why not `tableView.indexPath(for: cell)` at tap time instead of an id?"* — That also works and
  is current. I prefer the id because it survives the cell being off screen (it returns `nil`
  then) and it's what analytics wants anyway.
- *"Would a diffable data source fix the stale index?"* — It helps: you key rows by identifier, so
  you naturally think in ids. It doesn't stop you capturing an `indexPath` in a closure.
- *"How would you test 'one tap, one click'?"* — A fake `AdTracking` that records calls. Configure
  an `AdCell` several times, send `.touchUpInside` to the button, and assert one recorded click
  for the last ad. That's the same check the simulator run did.
- *"What's the SwiftUI version of this bug?"* — Much rarer, because a `Button`'s action is part of
  the view value and is replaced on every update. The stale-data half survives, though: capture an
  index in a closure and it goes stale the same way. Use the item's id.
:::
