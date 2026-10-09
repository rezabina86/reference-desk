---
title: 17 · The main thread doing heavy lifting
summary: An articles list that freezes on open and stutters on scroll — find the work that shouldn't be on the main thread, and move it.
minutes: 20
group: Find the bug
sources:
- Glassdoor · Uber iOS — debugging round on "standard iOS problems (sync/async, main thread violations)" | https://static.glassdoor.nl/Interview/Uber-IOS-Developer-Interview-Questions-EI_IE575263.0,4_KO5,18_IP2.htm
- Blind · Apple iOS — "Multi threading / Performance round" | https://www.teamblind.com/post/apple-ios-multi-threading-performance-round-avjtmkcj
- Apple · Improving app responsiveness (hitches and hangs) | https://developer.apple.com/documentation/xcode/improving-app-responsiveness
- Apple · UIImage.byPreparingThumbnail(ofSize:) | https://developer.apple.com/documentation/uikit/uiimage/byPreparingThumbnail(ofSize:)
- SE-0461 · Run nonisolated async functions on the caller's actor by default | https://github.com/swiftlang/swift-evolution/blob/main/proposals/0461-async-function-isolation.md
---

*Shape: find the bug · Reported: Uber — a debugging round on "standard iOS problems (sync/async,
main thread violations)"; Apple — a "Multi threading / Performance round" · Verified: snippet and
fix typecheck in Swift 6 mode with zero warnings, Swift 6.4; the timings were run on an M1 Pro Mac*

> "Users say the articles screen freezes for a second or two when it opens, and then the list
> stutters when they scroll. Nothing crashes in our tests. What's wrong, how would you prove it, and
> how would you fix it?"

```swift
struct Article: Decodable {
    let id: String
    let title: String
    let publishedAt: Date
    let thumbnailURL: URL
}

final class ArticlesViewController: UITableViewController {
    private var articles: [Article] = []
    private var favourites: Set<String> = []

    override func viewDidLoad() {
        super.viewDidLoad()
        tableView.register(UITableViewCell.self, forCellReuseIdentifier: "ArticleCell")

        let url = URL(string: "https://api.example.com/articles")!
        let data = try! Data(contentsOf: url)
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        let loaded = try! decoder.decode([Article].self, from: data)

        let documents = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
        if let saved = try? Data(contentsOf: documents.appendingPathComponent("favourites.json")) {
            favourites = (try? decoder.decode(Set<String>.self, from: saved)) ?? []
        }

        for article in loaded {
            articles.append(article)
            tableView.reloadData()
        }
    }

    override func tableView(_ tableView: UITableView, numberOfRowsInSection section: Int) -> Int {
        articles.count
    }

    override func tableView(_ tableView: UITableView, cellForRowAt indexPath: IndexPath) -> UITableViewCell {
        let cell = tableView.dequeueReusableCell(withIdentifier: "ArticleCell", for: indexPath)
        let article = articles[indexPath.row]

        let formatter = DateFormatter()
        formatter.dateFormat = "dd MMM yyyy"

        var content = cell.defaultContentConfiguration()
        content.text = article.title
        content.secondaryText = formatter.string(from: article.publishedAt)
        if let imageData = try? Data(contentsOf: article.thumbnailURL) {
            content.image = UIImage(data: imageData)
        }
        cell.contentConfiguration = content
        cell.accessoryType = favourites.contains(article.id) ? .checkmark : .none
        return cell
    }
}
```

This compiles in Swift 6 mode with no warnings at all. Swift 6 checks that data isn't shared
unsafely between threads; it doesn't check *how long* the main thread is kept busy.

::: A hint, if you're stuck
- Which of these lines wait for something outside the app — the network, the disk?
- `viewDidLoad` and `cellForRowAt` both run on the main thread. What else does the main thread do?
- How many times does `cellForRowAt` run during one fast scroll?
- `UIImage(data:)` returns quickly. When does the real work happen?
:::

::: How I'd debug it
I don't guess, I profile. Run on a real device, ideally an older one, with Instruments' *Time
Profiler* and *Hangs*. Open the screen: a hang marker appears, and the main thread's heaviest stack
is `Data(contentsOf:)` under `viewDidLoad`. Scroll: the hitches line up with `Data(contentsOf:)`
and image decoding under `cellForRowAt`. The fix is right when those stacks leave the main thread
and the markers go away.
:::

::: The key — what I expect a senior to find
The two reported bugs come first, right after the crash.

1. **`try!` on the network and the decode.** Offline, behind a captive Wi-Fi page, or with one bad
   field in the JSON, the app crashes on open. Use `try` and show an error state.
2. **A network request that blocks the main thread (the freeze).** `Data(contentsOf:)` with an
   `https` URL is a *synchronous* download: the main thread stops and waits for the whole response.
   Nothing redraws and no touch is handled until it returns. If this is the first screen at launch,
   the system can kill the app for taking too long to start. Use `URLSession`'s `async` API.
3. **A network request per cell, on main (the stutter).** The same call in `cellForRowAt`
   downloads every thumbnail while the user scrolls, one row at a time. This is the worst line in
   the file. Download in a `Task` and set the image when it arrives.
4. **No loading or error state.** The user stares at an empty list while it loads, and a failure
   would show nothing at all. Show a spinner, then rows or a message.
5. **A fixed `dateFormat` ignores the user's region.** `"dd MMM yyyy"` forces day-month-year on a
   US user. Use a style (`.abbreviated`) and let the locale decide the order.
6. **Nothing can be tested.** The URL, `URLSession`, `FileManager.default` and the decoding all
   live inside `viewDidLoad`, so a test can't feed it data. Inject the loading as one closure.
7. **Full-size image decoding on main.** `UIImage(data:)` doesn't decode yet; the pixels are
   unpacked the first time the image is drawn — on the main thread, at full size, mid-scroll. A
   3,000-pixel photo shown at 60 points is mostly wasted work. Shrink and decode off main with
   `byPreparingThumbnail(ofSize:)`.
8. **No image cache.** Scroll down and back up and every thumbnail downloads again. Keep them in an
   `NSCache` keyed by URL.
9. **JSON decoded on main.** On my M1 Pro Mac, decoding 5,000 small articles took 22–29 ms —
   more than a whole frame at 60 Hz. Treat a phone as the same order of magnitude; an older phone
   is slower.
10. **A synchronous file read on main.** Usually tiny, but the main thread has no business waiting
    on the disk, and the file only grows.
11. **`reloadData()` once per article.** Pointless work that grows with the list. UIKit defers
    building cells to the next layout pass, but each call still invalidates the whole table. Fill
    the array, reload once.
12. **A new `DateFormatter` for every cell.** Creating one per row cost about 100 µs; reusing one,
    or a `Date.FormatStyle`, cost 1–2 µs. Rarely a dropped frame on its own, but the cheapest fix
    here: make it `static`.
13. **Favourites decoded with the articles' decoder.** It works, but a decoder set up for ISO-8601
    dates has nothing to do with a set of IDs. Use a plain `JSONDecoder()`.
14. **Magic strings and a force unwrap.** `"ArticleCell"` is typed twice; one typo crashes at
    dequeue. `URL(string:)!` on a literal is safe but reads as careless — make it a `static let`.

How I measured 9 and 12: a Foundation-only program, `swiftc -O`, run twice on an M1 Pro Mac.
:::

::: The idea behind it
The screen is redrawn many times a second: 60 times on most iPhones, up to 120 on ProMotion
displays. Each new picture is a *frame*. To keep up, every frame must be ready in 1/60 s — about
16.7 milliseconds — or 1/120 s, about 8.3 ms. That's the *frame budget*.

The *main thread* is the one line of work that does all of the UI: it handles your touches, runs
`cellForRowAt`, lays out views and hands the finished frame over. It can only do one thing at a
time. If you give it 40 ms of downloading or decoding, it misses two or more frames, and the
scroll jumps. A late frame is called a *hitch*. If the main thread is stuck long enough that taps
stop working — Apple's tools start reporting at about 250 ms — that's a *hang*.

Picture a waiter who is the only one allowed to talk to customers. If he goes into the kitchen to
cook a steak himself, nobody gets served. The fix is to keep him at the tables: send the cooking
(network, disk, decoding, image shrinking) to the kitchen — background threads — and have him
carry only the finished plate to the table, on the main thread.

*Main Thread Checker* catches the opposite mistake — UI touched *off* the main thread — and is
silent about this code. Slow work *on* the main thread is legal; it's just slow.
:::

::: The fix
```swift
struct Article: Decodable, Sendable {                                    // crosses threads now
    let id: String
    let title: String
    let publishedAt: Date
    let thumbnailURL: URL
}

final class ArticlesViewController: UITableViewController {
    private var articles: [Article] = []
    private var favourites: Set<String> = []
    private static let dateStyle = Date.FormatStyle(date: .abbreviated, time: .omitted)  // key 5, 12
    var load: @Sendable () async throws -> ([Article], Set<String>) = loadArticles  // key 6: the seam

    override func viewDidLoad() {
        super.viewDidLoad()
        tableView.register(UITableViewCell.self, forCellReuseIdentifier: "ArticleCell")

        let load = self.load
        Task { [weak self] in
            do {
                let (loaded, saved) = try await load()          // key 1, 2, 9, 10: off main, no try!
                guard let self else { return }
                articles = loaded
                favourites = saved
                tableView.reloadData()                          // key 11: once
            } catch {
                let label = UILabel()                           // key 1, 4: an error state, not a crash
                label.text = "Couldn't load articles."
                self?.tableView.backgroundView = label
            }
        }
    }

    override func tableView(_ tableView: UITableView, numberOfRowsInSection section: Int) -> Int {
        articles.count
    }

    override func tableView(_ tableView: UITableView, cellForRowAt indexPath: IndexPath) -> UITableViewCell {
        let cell = tableView.dequeueReusableCell(withIdentifier: "ArticleCell", for: indexPath)
        let article = articles[indexPath.row]

        var content = cell.defaultContentConfiguration()
        content.text = article.title
        content.secondaryText = article.publishedAt.formatted(Self.dateStyle)
        content.image = UIImage(systemName: "photo")                         // placeholder
        content.imageProperties.maximumSize = CGSize(width: 60, height: 60)
        cell.contentConfiguration = content
        cell.accessoryType = favourites.contains(article.id) ? .checkmark : .none

        let side = 60 * tableView.traitCollection.displayScale
        Task { [weak tableView] in                                           // key 3, 7
            guard let image = try? await Self.thumbnail(article.thumbnailURL, side: side),
                  let cell = tableView?.cellForRow(at: indexPath),           // nil if scrolled away
                  var content = cell.contentConfiguration as? UIListContentConfiguration else { return }
            content.image = image
            cell.contentConfiguration = content
        }
        return cell
    }

    // @concurrent: always runs on a background thread, never on the caller's actor.
    @concurrent private static func loadArticles() async throws -> ([Article], Set<String>) {
        let (data, _) = try await URLSession.shared.data(from: URL(string: "https://api.example.com/articles")!)
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        let loaded = try decoder.decode([Article].self, from: data)

        let documents = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
        let saved = try? Data(contentsOf: documents.appendingPathComponent("favourites.json"))
        let favourites = saved.flatMap { try? JSONDecoder().decode(Set<String>.self, from: $0) } ?? []  // key 13
        return (loaded, favourites)
    }

    @concurrent private static func thumbnail(_ url: URL, side: CGFloat) async throws -> UIImage? {
        let (data, _) = try await URLSession.shared.data(from: url)
        return await UIImage(data: data)?.byPreparingThumbnail(ofSize: CGSize(width: side, height: side))
    }
}
```

**Said out loud, not coded:** a spinner while loading (key 4) · an `NSCache` for thumbnails
(key 8) · a cell subclass that cancels its download in `prepareForReuse` · a Retry button ·
moving loading out of the controller into a view model · a `static let` for the reuse ID and URL.

Why each piece:

- **`@concurrent`** — guarantees the download, the decoding, the file read and the image shrinking
  run off the main actor. A plain `nonisolated async` function may run on the *caller's* actor
  under the newer `nonisolated(nonsending)` default (SE-0461); `@concurrent` is clear under both.
- **Code after `await` in the `Task` runs on main** — the controller is `@MainActor`, so setting
  `articles` and calling `reloadData()` is on the right thread by construction.
- **`cellForRow(at:)` after the download, not the cell captured earlier** — a captured cell may
  have been reused for another row by then; `cellForRow(at:)` returns `nil` for a row that's gone.
- **`maximumSize` on the image** — a thumbnail made from `Data` has scale 1, so a 180-pixel image
  would otherwise lay out as 180 points. This pins it to the 60-point slot.
:::

::: Now write the tests
> "Good. Now write me a few tests. I know you can't unit-test 'it's smooth' — so what *can* you test?"

**What I'd test, and why**

1. **The screen loads once and reloads once.** The old code reloaded the table once per article.
   A *spy* table — a subclass that counts `reloadData()` calls — pins "once".
2. **A failed load shows an error and no rows** — the old `try!` crashed on open.
3. **A favourite is ticked** — the regression check: moving the loading must not lose the
   favourites.

What a unit test can't prove is the point of the chapter: that the work happens *off* the main
thread and the scroll stays smooth. That's measured with Instruments on a device, before and after.

**The seam.** The `load` closure is a property with a real default, so a test swaps in a fixed
answer — no network, no disk. The test waits for what a user would see (the table reloaded, the
error shown) with `waitUntil(maxYields:_:)`, which gives the main actor a turn up to a fixed number
of times. No clock, so it can't be flaky. One detail: the spy table goes in *after*
`loadViewIfNeeded()`. Assigning `tableView` first creates the view without calling `viewDidLoad`,
and nothing would load.

```swift
import Testing
import UIKit

// Counts how many times the screen asked for articles.
actor LoadCounter {
    private(set) var count = 0
    func increment() { count += 1 }
}

final class TableSpy: UITableView {
    private(set) var reloadCount = 0
    override func reloadData() {
        reloadCount += 1
        super.reloadData()
    }
}

/// Gives the main actor a turn, up to a fixed number of times, until the condition holds.
/// A count of turns, not a clock, so a slow machine can't make it flaky.
@MainActor
func waitUntil(maxYields: Int = 1_000, _ condition: () async -> Bool) async {
    for _ in 0..<maxYields {
        if await condition() { return }
        await Task.yield()
    }
}

func makeArticle(_ id: String) -> Article {
    // /dev/null reads as empty data, so the thumbnail task ends at once, with no network.
    Article(id: id, title: "Article \(id)", publishedAt: Date(timeIntervalSince1970: 0),
            thumbnailURL: URL(fileURLWithPath: "/dev/null"))
}

struct LoadFailed: Error {}

/// Loads the screen, then swaps in a spy table. The order matters: assigning `tableView`
/// first would create the view without calling viewDidLoad, and nothing would load.
@MainActor
func makeScreen(load: @escaping @Sendable () async throws -> ([Article], Set<String>))
    -> (ArticlesViewController, TableSpy) {
    let screen = ArticlesViewController(style: .plain)
    screen.load = load
    screen.loadViewIfNeeded()
    let table = TableSpy()
    table.register(UITableViewCell.self, forCellReuseIdentifier: "ArticleCell")
    screen.tableView = table
    return (screen, table)
}

@Suite(.timeLimit(.minutes(1)))
@MainActor
struct ArticlesViewControllerTests {
    @Test func loadsOnceAndReloadsOnce() async {
        // Given a loader with three articles that counts its calls
        let counter = LoadCounter()
        let (screen, table) = makeScreen {
            await counter.increment()
            return (["1", "2", "3"].map(makeArticle), [])
        }

        // When the load lands
        await waitUntil { table.reloadCount > 0 }

        // Then it asked once, reloaded once, and shows three rows
        #expect(await counter.count == 1)
        #expect(table.reloadCount == 1)
        #expect(screen.tableView(table, numberOfRowsInSection: 0) == 3)
    }

    @Test func failedLoadShowsAnErrorAndNoRows() async {
        let (screen, table) = makeScreen { throw LoadFailed() }

        await waitUntil { table.backgroundView != nil }

        #expect((table.backgroundView as? UILabel)?.text == "Couldn't load articles.")
        #expect(screen.tableView(table, numberOfRowsInSection: 0) == 0)
        #expect(table.reloadCount == 0)
    }

    @Test func favouriteIsTicked() async {
        let (screen, table) = makeScreen { (["1", "2"].map(makeArticle), ["2"]) }
        await waitUntil { table.reloadCount > 0 }

        let first = screen.tableView(table, cellForRowAt: IndexPath(row: 0, section: 0))
        let second = screen.tableView(table, cellForRowAt: IndexPath(row: 1, section: 0))

        #expect(first.accessoryType == .none)
        #expect(second.accessoryType == .checkmark)
    }
}
```

Ran on the iOS Simulator (Swift 6 mode): 3 tests, all passed.
:::

::: What I'd ask next
- *"Why `@concurrent`? Isn't an `async` function already off the main thread?"* — It depends.
  Under the classic Swift 6 rules, a `nonisolated async` function runs on the background pool.
  With the newer setting that Xcode 26 turns on for new projects (*nonisolated(nonsending) by
  default*, SE-0461), it runs on the *caller's* actor — so called from the main actor, the decode
  would be back on main. `@concurrent` states the intent and works under both.
- *"How do you prove the fix worked?"* — Profile before and after on a real device, ideally an
  older one, with the Time Profiler and Hangs instruments: the main thread's heavy stacks should
  disappear and the hang markers on open should go. Xcode Organizer's hang rate shows the same
  for users in the field.
- *"Where does the image cache go?"* — Next to the thumbnail download: an `NSCache` keyed by URL
  and size, checked before the request. Then scrolling back up is free.
- *"A fast scroll starts a download for every row it passes. Then what?"* — Move the `Task` into a
  cell subclass, keep it in a property, and cancel it in `prepareForReuse` (chapter 01).
- *"Is `DateFormatter` safe to share across threads?"* — Yes, on iOS 7 and later it is
  thread-safe for formatting. The real constraint is not mutating its settings while others use it,
  which a `static let` you configure once avoids.
:::
