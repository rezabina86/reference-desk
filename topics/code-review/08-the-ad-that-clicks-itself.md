---
title: 08 · The ad that clicks itself
summary: A feed with an ad cell whose tap handlers pile up on reused cells — find why ads open when nobody tapped them, and why clicks are counted twice.
minutes: 20
group: Find the bug
sources:
- Blind · eBay iOS debugging round — "why does the ad keep clicking when user didn't click it" | https://www.teamblind.com/post/ebay-ios-debugging-round-mb2odkpv
---

*Shape: find the bug · Reported: eBay — a debugging round built around "why does the ad keep
clicking when user didn't click it" · Verified: snippet and fix compiled in Swift 6 mode against
the iOS SDK, and the tests ran on the iOS Simulator, Swift 6.4*

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
   moment it was configured, and old closures are never removed (see 3). Refresh to a shorter feed,
   tap, and an old closure reads `items[indexPath.row]` past the end — crash. Look the ad up at tap
   time, by its id.
2. **Posts open ads (a reported bug).** One cell class and one reuse identifier serve both kinds of
   row. A cell that once showed an ad keeps its tap recogniser and its `onTap` when it's reused for
   a post, because the `.post` branch resets neither. The user taps the post and the old ad opens.
3. **Handlers pile up: one tap, several clicks (the inflated numbers).** `addAction` adds a new
   closure every time the cell is configured as an ad and never removes the old ones (checked: one
   cell reused for three ads logged three clicks from one tap). Gesture recognisers pile up the
   same way.
4. **Clicks for the wrong ad.** A stale row number after a refresh can point at a *different* ad.
   The wrong ad opens and the wrong advertiser is billed — the invalid clicks ad networks penalise.
5. **`didRefresh` may run off the main thread.** If the network layer calls it from its completion
   handler, `reloadData()` runs on a background queue. Swift 6 mode stops that at compile time,
   because the controller is `@MainActor`; Swift 5 mode doesn't.
6. **`ad.url` is opened unchecked.** The URL comes from an ad server, and `open` accepts any scheme
   — `tel:`, another app's deep link. Allow `https` only.
7. **The card tap bypasses the table.** The recogniser on `contentView` cancels the touch, so
   `didSelectRowAt` never runs for a reused post either. And `didSelectRowAt` ignores ads, so the
   ad card only works through the leaked recogniser. No `deselectRow`, so the row stays grey.
8. **Impressions counted on every appearance.** `willDisplay` runs each time the cell scrolls back
   and after every `reloadData()`. Count each ad once (a `Set` of ids); real ad SDKs also wait
   until half the ad has been visible for a second.
9. **No `prepareForReuse`, one cell for two kinds.** There is no place where leftover state is
   cleared. Clear the closure in `prepareForReuse`; ideally give ads their own `AdCell`.
10. **Handlers wired in the wrong place.** Wiring belongs where the cell is created, once.
    `cellForRow` should only *set* values, never *add* things.
11. **Untestable side effects.** `Analytics.shared` is reached directly, so no test can check "one
    tap, one click". Inject the tracker.
12. **`as! FeedCell`.** It crashes if the storyboard prototype's class is wrong. That's a programmer
    error, so the force cast is defensible — say why rather than hide it behind `as?`.
13. **Note: `addTarget` would have hidden this.** Adding the same target and selector twice keeps
    one entry. A fresh `UIAction` closure has no such dedupe, so moving to closures is what made
    this bug appear.
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
Same storyboard cell, same controller, same `Analytics`. Only the marked lines change: the
`addAction` and gesture lines in `cellForRow` are gone, and `cardTapped` with them.

```swift
@MainActor
protocol AdTracking {                                           // key 11: the one seam
    func track(_ event: String, _ properties: [String: Any])
}
extension Analytics: AdTracking {}

final class FeedCell: UITableViewCell {
    let titleLabel = UILabel()
    lazy var ctaButton: UIButton = {                            // key 10: wired once, at creation
        let button = UIButton(type: .system)
        button.addAction(UIAction { [weak self] _ in self?.onTap?() }, for: .touchUpInside)
        return button
    }()
    var onTap: (() -> Void)?

    override func prepareForReuse() {                           // key 9
        super.prepareForReuse()
        onTap = nil
    }
}

final class FeedViewController: UITableViewController {
    private var items: [FeedItem] = []          // enum FeedItem { case post(Post), ad(Ad) }
    var analytics: any AdTracking = Analytics.shared            // key 11
    private var loggedImpressions: Set<String> = []             // key 8

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
            cell.onTap = { [weak self] in self?.openAd(id: ad.id) }   // keys 1–4: set, don't add
        }
        return cell
    }

    override func tableView(_ tableView: UITableView, willDisplay cell: UITableViewCell,
                            forRowAt indexPath: IndexPath) {
        if case .ad(let ad) = items[indexPath.row], loggedImpressions.insert(ad.id).inserted {   // key 8
            analytics.track("ad_impression", ["id": ad.id])
        }
    }

    override func tableView(_ tableView: UITableView, didSelectRowAt indexPath: IndexPath) {
        tableView.deselectRow(at: indexPath, animated: true)    // key 7
        switch items[indexPath.row] {
        case .post(let post): show(PostViewController(post: post), sender: self)
        case .ad(let ad): openAd(id: ad.id)                     // key 7: the card tap, no gesture
        }
    }

    func didRefresh(with newItems: [FeedItem]) {
        items = newItems
        tableView.reloadData()
    }

    private func openAd(id: String) {                           // keys 1, 4: look up by id, now
        guard let row = items.firstIndex(where: { if case .ad(let ad) = $0 { ad.id == id } else { false } }),
              case .ad(let ad) = items[row] else { return }
        analytics.track("ad_click", ["id": ad.id, "position": row])
        UIApplication.shared.open(ad.url)
    }
}
```

**Said out loud, not coded:** separate `AdCell` and `PostCell`; allow only `https` ad URLs behind an
injected URL opener; real impression rules (half visible for a second, reset per session); and in
Swift 5 mode, make sure `didRefresh` is called on main.

Why each piece:

- **The button is wired once, when it's created.** A `lazy var` closure runs once, so the cell owns
  one permanent action that calls whatever `onTap` it holds. `[weak self]` because the cell owns
  the button, which owns the action.
- **`prepareForReuse` clears `onTap`.** A cell reused for a post has nothing left to fire.
- **`openAd(id:)` looks the ad up at tap time.** After a refresh it finds the ad wherever it is
  now, or does nothing if it's gone. No stale row, no out-of-range crash.
- **The card tap goes through `didSelectRowAt`.** The table hands you the current index path, so
  there's no recogniser to leak and no swallowed selection.
:::

::: Now write the tests
> "Good. Now write me the tests that would have caught the inflated click numbers."

**What I'd test, and why**

1. **One tap on a reused cell clicks only the ad on screen.** The cell is reused for ads a, b and
   c; one tap logs one click, for c. This is the pile-up, so it goes first.
2. **A cell reused for a post opens nothing** — the reported "posts open ads" bug.
3. **An impression is logged once per ad** — scrolling past three times counts once.
4. **A tap on an ad a refresh removed does nothing** — no click, and no out-of-range crash.

I wouldn't test layout or UIKit's touch handling; `sendActions(for: .touchUpInside)` stands in for
the finger.

**The seam.** `analytics` became a `var` with a default, so the storyboard still builds the screen
and a test swaps in a fake tracker that writes events down. `OneCellTableView` is a table with one
cell in its pool: every dequeue hands back the same cell after `prepareForReuse`, just as UIKit
does, so reuse happens on demand. The fake ads use a URL scheme nothing handles, so `open` does
nothing.

```swift
import Testing
import UIKit

/// A fake tracker: it only writes down what it was told.
@MainActor
final class FakeAdTracker: AdTracking {
    private(set) var events: [String] = []

    func track(_ event: String, _ properties: [String: Any]) {
        events.append("\(event) \(properties["id"] ?? "")")
    }
}

/// A table with one cell in its reuse pool: every dequeue hands back the same cell, like UIKit.
final class OneCellTableView: UITableView {
    let cell = FeedCell(style: .default, reuseIdentifier: "FeedCell")

    override func dequeueReusableCell(withIdentifier identifier: String,
                                      for indexPath: IndexPath) -> UITableViewCell {
        cell.prepareForReuse()
        return cell
    }
}

@MainActor
struct FeedViewControllerTests {
    let tracker = FakeAdTracker()
    let table = OneCellTableView()

    func makeFeed(_ items: [FeedItem]) -> FeedViewController {
        let feed = FeedViewController(style: .plain)
        feed.tableView = table
        feed.analytics = tracker
        feed.didRefresh(with: items)
        return feed
    }

    func ad(_ id: String) -> FeedItem {
        // A scheme nothing handles, so UIApplication.open does nothing in the test.
        .ad(Ad(id: id, headline: id, callToAction: "Open", url: URL(string: "test-ad://\(id)")!))
    }

    func configureRow(_ row: Int, in feed: FeedViewController) {
        _ = feed.tableView(table, cellForRowAt: IndexPath(row: row, section: 0))
    }

    @Test func oneTapOnAReusedCellClicksOnlyTheAdOnScreen() {
        let feed = makeFeed([ad("a"), ad("b"), ad("c")])
        for row in 0..<3 { configureRow(row, in: feed) }   // one cell, reused three times

        table.cell.ctaButton.sendActions(for: .touchUpInside)

        #expect(tracker.events == ["ad_click c"])
    }

    @Test func cellReusedForAPostOpensNothing() {
        let feed = makeFeed([ad("a"), .post(Post(title: "Hello"))])
        configureRow(0, in: feed)
        configureRow(1, in: feed)                          // the ad's cell now shows the post

        table.cell.ctaButton.sendActions(for: .touchUpInside)

        #expect(tracker.events == [])
    }

    @Test func impressionIsLoggedOncePerAd() {
        let feed = makeFeed([.post(Post(title: "Hello")), ad("a")])

        for _ in 0..<3 {                                   // the ad scrolls on screen three times
            feed.tableView(table, willDisplay: UITableViewCell(), forRowAt: IndexPath(row: 1, section: 0))
        }

        #expect(tracker.events == ["ad_impression a"])
    }

    @Test func tapOnAnAdThatARefreshRemovedDoesNothing() {
        let feed = makeFeed([.post(Post(title: "Hello")), ad("a")])
        configureRow(1, in: feed)

        feed.didRefresh(with: [.post(Post(title: "Hello"))])   // shorter feed, ad gone
        table.cell.ctaButton.sendActions(for: .touchUpInside)

        #expect(tracker.events == [])                     // and no out-of-range crash
    }
}
```

Ran on the iOS Simulator (Swift 6 mode): 4 tests, all passed.
:::

::: What I'd ask next
- *"How would you have found this without reading the code?"* — Put a breakpoint in `openAd` and
  tap once. If it's hit three times, look at the backtrace: three separate closures. Or log
  `ctaButton.enumerateEventHandlers` in the cell (iOS 14+) to count what's attached.
- *"Why not `tableView.indexPath(for: cell)` at tap time instead of an id?"* — That also works: the
  tapped cell is on screen, so it returns its current row. I keep the id because it's what analytics
  needs anyway, and it doesn't depend on the cell at all.
- *"Would a diffable data source fix the stale index?"* — It helps: you key rows by identifier, so
  you naturally think in ids. It doesn't stop you capturing an `indexPath` in a closure.
- *"Why does `[weak self]` matter in the button's action?"* — The cell owns the button, the button
  owns the action, and the action's closure would own the cell. That's a loop, and every cell in the
  pool would leak.
- *"What's the SwiftUI version of this bug?"* — Much rarer, because a `Button`'s action is part of
  the view value and is replaced on every update. The stale-data half survives, though: capture an
  index in a closure and it goes stale the same way. Use the item's id.
:::
