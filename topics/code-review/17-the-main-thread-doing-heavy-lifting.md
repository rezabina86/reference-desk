---
title: 17 · The main thread doing heavy lifting
summary: An articles list that freezes on open and stutters on scroll — find the work that shouldn't be on the main thread, and move it.
minutes: 20
group: Find the bug
sources:
- Glassdoor · Uber iOS — debugging round on "standard iOS problems (sync/async, main thread violations)" | https://static.glassdoor.nl/Interview/Uber-IOS-Developer-Interview-Questions-EI_IE575263.0,4_KO5,18_IP2.htm
- Blind · Apple iOS — "Multi threading / Performance round" | https://www.teamblind.com/post/apple-ios-multi-threading-performance-round-avjtmkcj
---

*Shape: find the bug · Reported: Uber — a debugging round on "standard iOS problems (sync/async,
main thread violations)" (from a Glassdoor search snippet); Apple — a "Multi threading /
Performance round" · UIKit — the snippet and the fix typecheck against the iOS SDK (iOS 18
target) in Swift 6 mode, the fix with zero warnings; the formatter and decoding timings were
compiled and run as a Foundation-only program with Swift 6.4; the scrolling behaviour was checked
by hand*

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

This compiles in Swift 6 mode with no warnings at all (checked). Swift 6 checks that data isn't
shared unsafely between threads; it doesn't check *how long* the main thread is kept busy.

::: A hint, if you're stuck
- Which of these lines wait for something outside the app — the network, the disk?
- `viewDidLoad` and `cellForRowAt` both run on the main thread. What else does the main thread do?
- How many times does `cellForRowAt` run during one fast scroll?
- `UIImage(data:)` returns quickly. When does the real work happen?
:::

::: The key — what I expect a senior to find
1. **`try!` on the network and the decode.** Offline, on a captive Wi-Fi page, or with one bad
   field in the JSON, the app crashes on open. Use `try` and show an error state with Retry.
2. **A network request that blocks the main thread (the freeze).** `Data(contentsOf:)` with an
   `https` URL is a *synchronous* download: the main thread stops and waits for the whole response.
   Nothing redraws and no touch is handled until it returns — a second or two on a good network,
   many seconds on a bad one. If this is the first screen at launch, the system can kill the app
   for taking too long to start. Recent Xcode versions can also flag synchronous URL loading
   on the main thread as a purple runtime issue.
3. **A network request per cell, on main (the stutter).** The same call in `cellForRowAt` downloads
   every thumbnail while the user scrolls, one row at a time, with nothing cached — scroll back up
   and they all download again. This is the worst line in the file.
4. **Full-size image decoding on main.** `UIImage(data:)` doesn't decode yet; the pixels are
   unpacked the first time the image is drawn — on the main thread, at full size, in the middle of
   the scroll. A 3,000-pixel photo shown at 60 points is mostly wasted work. Shrink and decode off
   main (`byPreparingThumbnail(ofSize:)`).
5. **JSON decoded on main.** On my M1 Pro Mac, decoding 5,000 small articles (about 2 MB) took
   23 ms — more than a whole frame at 60 Hz, nearly three at 120 Hz. Phones are not faster.
6. **A synchronous file read on main.** Usually tiny, but the main thread has no business waiting
   on the disk, and the file only grows.
7. **`reloadData()` once per article.** For 500 articles that's 500 reloads to show one result:
   each throws away the visible rows and asks the data source again. Fill the array, reload once
   (or apply one diffable snapshot).
8. **A new `DateFormatter` for every cell.** Formatters are expensive to create. Measured: creating
   one per row cost about 96 µs, reusing one cost about 1 µs, a reused `Date.FormatStyle` about
   2–3 µs. On its own it rarely drops a frame, but it's the cheapest fix here. Make it `static`.
9. **A fixed `dateFormat` ignores the user's region.** `"dd MMM yyyy"` forces day-month-year on a
   US user. Use a style (`.abbreviated`) and let the locale decide the order.
10. **Nothing can be tested or cancelled.** The URL, `FileManager.default` and the decoding are
    inside the controller; leave the screen mid-load and the work carries on.
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

How to find it: Instruments' *Time Profiler* shows what the main thread was busy with; the *Hangs*
and *Animation Hitches* instruments mark the exact moments it fell behind. *Main Thread Checker*
catches the opposite mistake — UI touched *off* the main thread — and is silent about this code.
:::

::: The fix
```swift
struct Article: Decodable, Sendable {
    let id: String
    let title: String
    let publishedAt: Date
    let thumbnailURL: URL
}

protocol ArticlesLoading: Sendable {
    func articles() async throws -> [Article]
    func favourites() async -> Set<String>
}

struct ArticlesLoader: ArticlesLoading {
    let session: URLSession
    let endpoint: URL
    let favouritesFile: URL

    // @concurrent: always runs on the background pool, never on the caller's actor.
    @concurrent func articles() async throws -> [Article] {
        let (data, _) = try await session.data(from: endpoint)
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        return try decoder.decode([Article].self, from: data)
    }

    @concurrent func favourites() async -> Set<String> {
        guard let data = try? Data(contentsOf: favouritesFile) else { return [] }
        return (try? JSONDecoder().decode(Set<String>.self, from: data)) ?? []
    }
}

protocol ThumbnailLoading: Sendable {
    func thumbnail(for url: URL, fittingPixels size: CGSize) async throws -> UIImage?
}

struct ThumbnailLoader: ThumbnailLoading {
    let session: URLSession

    @concurrent func thumbnail(for url: URL, fittingPixels size: CGSize) async throws -> UIImage? {
        let (data, _) = try await session.data(from: url)
        // Shrinks and decodes now, off the main thread, so drawing it later costs nothing.
        return await UIImage(data: data)?.byPreparingThumbnail(ofSize: size)
    }
}

final class ArticleCell: UITableViewCell {
    static let reuseID = "ArticleCell"
    private static let dateStyle = Date.FormatStyle(date: .abbreviated, time: .omitted)
    private var thumbnailTask: Task<Void, Never>?

    override func prepareForReuse() {
        super.prepareForReuse()
        thumbnailTask?.cancel()
    }

    func configure(with article: Article, isFavourite: Bool, thumbnails: ThumbnailLoading) {
        var content = defaultContentConfiguration()
        content.text = article.title
        content.secondaryText = article.publishedAt.formatted(Self.dateStyle)
        content.image = UIImage(systemName: "photo")   // placeholder until the real one arrives
        contentConfiguration = content
        accessoryType = isFavourite ? .checkmark : .none

        let side = 60 * traitCollection.displayScale    // the thumbnail is 60 pt square
        thumbnailTask?.cancel()
        thumbnailTask = Task { [weak self] in
            guard let image = try? await thumbnails.thumbnail(for: article.thumbnailURL,
                                                              fittingPixels: CGSize(width: side, height: side)),
                  !Task.isCancelled, let self,
                  var content = self.contentConfiguration as? UIListContentConfiguration else { return }
            content.image = image
            self.contentConfiguration = content
        }
    }
}

final class ArticlesViewController: UITableViewController {
    private let loader: ArticlesLoading
    private let thumbnails: ThumbnailLoading
    private var articles: [Article] = []
    private var favourites: Set<String> = []
    private var loadTask: Task<Void, Never>?

    init(loader: ArticlesLoading, thumbnails: ThumbnailLoading) {
        self.loader = loader
        self.thumbnails = thumbnails
        super.init(style: .plain)
    }

    required init?(coder: NSCoder) { fatalError("init(coder:) is not used") }

    override func viewDidLoad() {
        super.viewDidLoad()
        tableView.register(ArticleCell.self, forCellReuseIdentifier: ArticleCell.reuseID)
        loadTask = Task { [weak self, loader] in
            do {
                async let list = loader.articles()
                async let saved = loader.favourites()
                let (articles, favourites) = try await (list, saved)
                guard let self else { return }
                self.articles = articles
                self.favourites = favourites
                self.tableView.reloadData()           // once, with everything
            } catch {
                self?.showError(error)
            }
        }
    }

    override func tableView(_ tableView: UITableView, numberOfRowsInSection section: Int) -> Int {
        articles.count
    }

    override func tableView(_ tableView: UITableView, cellForRowAt indexPath: IndexPath) -> UITableViewCell {
        let cell = tableView.dequeueReusableCell(withIdentifier: ArticleCell.reuseID, for: indexPath) as! ArticleCell
        let article = articles[indexPath.row]
        cell.configure(with: article, isFavourite: favourites.contains(article.id), thumbnails: thumbnails)
        return cell
    }

    private func showError(_ error: any Error) {
        // An empty state with a Retry button; omitted.
    }
}
```

The timings in the key came from a Foundation-only program (`swiftc -swift-version 6 -O`, no
warnings), run twice on an M1 Pro Mac. Its setup, in short:

```swift
let dates = (0..<10_000).map { Date(timeIntervalSince1970: Double($0) * 86_400) }
// ① a new DateFormatter per row   ② one shared DateFormatter   ③ one Date.FormatStyle
// ④ JSONDecoder on 5,000 Article values encoded as ~2 MB of JSON
```

```text
① new DateFormatter per row        total 967.0 ms · per row 96.7 μs
② one shared DateFormatter         total 10.3 ms · per row 1.0 μs
③ one Date.FormatStyle             total 26.8 ms · per row 2.7 μs
④ decode 5,000 articles (2164 KB): 23.3 ms
```

(The second run: 958.4 ms, 10.4 ms, 17.1 ms, 23.1 ms.)

Why each piece:

- **`@concurrent` on the loaders** — guarantees the decoding, the file read and the image
  shrinking run on a background thread. Without it, whether a plain `async` function leaves the
  main actor depends on a build setting (see the follow-ups); with it, the answer is always yes.
- **`URLSession.data(from:)` instead of `Data(contentsOf:)`** — the request is asynchronous: while
  it waits, no thread is blocked, and the main thread keeps drawing.
- **`async let` for the two loads** — the articles and the favourites load at the same time.
- **Code after `await` in the controller's `Task` runs on main** — the controller is `@MainActor`,
  so assigning `articles` and calling `reloadData()` is on the right thread by construction.
- **One `reloadData()`** — the data arrives all at once, so the table is told once.
- **`byPreparingThumbnail(ofSize:)` with a pixel size** — shrinks to what the cell shows (points ×
  screen scale) and decodes in the background, so drawing it during the scroll is cheap.
- **A `Task` per cell, cancelled in `prepareForReuse`** — a reused cell never shows the previous
  row's thumbnail, and a fast scroll cancels downloads for rows already gone (chapter 01).
- **A `static` date style** — created once for the whole app, and locale-aware.
- **Injected loaders** — a test can feed fixed data and check the screen without a network.
:::

::: Now write the tests
> "Good. Now write me a few tests. I know you can't unit-test 'it's smooth' — so what *can* you test?"

**What I'd test, and why**

1. **The screen loads once and shows every article, with one reload.** The old code reloaded the
   table once per article; a *spy* table that counts `reloadData()` calls pins "once". It also
   checks the favourite tick.
2. **A failed load shows no rows and doesn't crash** — the old `try!` crashed on open.
3. **Reusing a cell cancels its thumbnail download** — fast scrolling must not keep downloading
   rows that are gone.
4. **A thumbnail shows when it arrives** — the placeholder is replaced, the title kept.

What a unit test can't prove is the point of the chapter: that the work happens *off* the main
thread and the scroll stays smooth. That's measured with Instruments (Time Profiler, Hangs) on a
real device, before and after. The tests here pin the behaviour that makes it possible.

**The seam.** The screen takes `ArticlesLoading` and `ThumbnailLoading` in `init`, so the tests pass
*fakes*: a loader with a fixed answer that counts its calls, and a thumbnail loader that holds each
download until the test answers it and reports when one is cancelled. The screen keeps its tasks
private, so the tests wait for what a user would see — the table reloaded, the image set — with a
helper that gives the main actor a turn up to a fixed number of times. No clock, so it can't be
flaky; and each suite has a one-minute `.timeLimit` as a backstop. One detail worth knowing: the
spy table is swapped in *after* `loadViewIfNeeded()`. Assigning `tableView` first creates the view
without calling `viewDidLoad`, and nothing would load.

```swift
import Testing
import UIKit

// Fakes: fixed answers, no network, no disk.
actor FakeArticlesLoader: ArticlesLoading {
    private(set) var loadCount = 0
    private let result: Result<[Article], any Error>
    private let saved: Set<String>

    init(_ result: Result<[Article], any Error>, favourites: Set<String> = []) {
        self.result = result
        saved = favourites
    }

    func articles() async throws -> [Article] {
        loadCount += 1
        return try result.get()
    }

    func favourites() async -> Set<String> { saved }
}

struct NoThumbnails: ThumbnailLoading {
    func thumbnail(for url: URL, fittingPixels size: CGSize) async throws -> UIImage? { nil }
}

// Each thumbnail waits until the test answers it, and reports when it is cancelled.
actor GatedThumbnails: ThumbnailLoading {
    nonisolated let requests: AsyncStream<URL>
    nonisolated let cancellations: AsyncStream<URL>
    private let requested: AsyncStream<URL>.Continuation
    private let cancelled: AsyncStream<URL>.Continuation
    private var waiting: [URL: CheckedContinuation<UIImage?, any Error>] = [:]

    init() {
        (requests, requested) = AsyncStream.makeStream()
        (cancellations, cancelled) = AsyncStream.makeStream()
    }

    func thumbnail(for url: URL, fittingPixels size: CGSize) async throws -> UIImage? {
        try await withTaskCancellationHandler {
            try await withCheckedThrowingContinuation { continuation in
                waiting[url] = continuation
                requested.yield(url)
            }
        } onCancel: {
            Task { await self.cancel(url) }
        }
    }

    func answer(_ url: URL, with image: UIImage) {
        waiting.removeValue(forKey: url)?.resume(returning: image)
    }

    private func cancel(_ url: URL) {
        cancelled.yield(url)
        waiting.removeValue(forKey: url)?.resume(throwing: CancellationError())
    }
}

final class TableSpy: UITableView {
    private(set) var reloadCount = 0
    override func reloadData() {
        reloadCount += 1
        super.reloadData()
    }
}

extension AsyncStream {
    func first() async -> Element? {
        var iterator = makeAsyncIterator()
        return await iterator.next()
    }
}

/// The screen and the cell keep their tasks private, so the test waits for what the user would
/// see instead: it gives the main actor a turn, up to a fixed number of times, until the condition
/// holds. A count of turns, not a clock, so a slow machine can't make it flaky or hang.
@MainActor
func waitUntil(maxYields: Int = 1_000, _ condition: () async -> Bool) async {
    for _ in 0..<maxYields {
        if await condition() { return }
        await Task.yield()
    }
}

func makeArticle(_ id: String) -> Article {
    Article(id: id, title: "Article \(id)", publishedAt: Date(timeIntervalSince1970: 0),
            thumbnailURL: URL(string: "https://example.com/\(id).jpg")!)
}

struct LoadFailed: Error {}

@Suite(.timeLimit(.minutes(1)))
@MainActor
struct ArticlesViewControllerTests {
    @Test func loadsOnceAndShowsEveryArticle() async throws {
        // Given three articles, one of them a favourite
        let loader = FakeArticlesLoader(.success(["1", "2", "3"].map(makeArticle)), favourites: ["2"])
        let screen = ArticlesViewController(loader: loader, thumbnails: NoThumbnails())

        // When the screen loads (the spy table goes in after viewDidLoad, which starts the load;
        // assigning tableView first would create the view and skip viewDidLoad)
        screen.loadViewIfNeeded()
        let table = TableSpy()
        table.register(ArticleCell.self, forCellReuseIdentifier: ArticleCell.reuseID)
        screen.tableView = table
        await waitUntil { table.reloadCount > 0 }

        // Then it asked once, reloaded once, and shows three rows with the favourite ticked
        #expect(await loader.loadCount == 1)
        #expect(table.reloadCount == 1)
        #expect(screen.tableView(table, numberOfRowsInSection: 0) == 3)
        let second = screen.tableView(table, cellForRowAt: IndexPath(row: 1, section: 0))
        #expect(second.accessoryType == .checkmark)
    }

    @Test func failedLoadShowsNoRowsAndDoesNotCrash() async {
        let loader = FakeArticlesLoader(.failure(LoadFailed()))
        let screen = ArticlesViewController(loader: loader, thumbnails: NoThumbnails())

        screen.loadViewIfNeeded()
        let table = TableSpy()
        screen.tableView = table
        await waitUntil { await loader.loadCount == 1 }
        await waitUntil(maxYields: 50) { false }   // let the failure finish landing

        #expect(screen.tableView(table, numberOfRowsInSection: 0) == 0)
        #expect(table.reloadCount == 0)
    }
}

@Suite(.timeLimit(.minutes(1)))
@MainActor
struct ArticleCellTests {
    @Test func reuseCancelsTheThumbnailDownload() async {
        // Given a cell waiting for its thumbnail
        let thumbnails = GatedThumbnails()
        let cell = ArticleCell(style: .default, reuseIdentifier: ArticleCell.reuseID)
        let article = makeArticle("1")
        cell.configure(with: article, isFavourite: false, thumbnails: thumbnails)
        _ = await thumbnails.requests.first()

        // When the cell is reused
        cell.prepareForReuse()

        // Then the download is cancelled
        #expect(await thumbnails.cancellations.first() == article.thumbnailURL)
    }

    @Test func thumbnailShowsWhenItArrives() async {
        let thumbnails = GatedThumbnails()
        let cell = ArticleCell(style: .default, reuseIdentifier: ArticleCell.reuseID)
        let article = makeArticle("1")
        let photo = UIImage(systemName: "star")!
        cell.configure(with: article, isFavourite: false, thumbnails: thumbnails)
        _ = await thumbnails.requests.first()

        await thumbnails.answer(article.thumbnailURL, with: photo)
        await waitUntil { (cell.contentConfiguration as? UIListContentConfiguration)?.image === photo }

        let content = cell.contentConfiguration as? UIListContentConfiguration
        #expect(content?.image === photo)
        #expect(content?.text == "Article 1")
    }
}
```

Ran on the iOS Simulator (iOS 18.5, Swift 6 mode): 4 tests, all passed.
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
- *"Where does the image cache go?"* — In the thumbnail loader: an `NSCache` keyed by URL and
  size, checked before the request. Then scrolling back up is free.
- *"Main Thread Checker didn't complain about any of this. Why?"* — It only catches UIKit called
  *from a background thread*. Doing slow work *on* the main thread is legal; it's just slow. Those
  are opposite problems with different tools.
- *"Is `DateFormatter` safe to share across threads?"* — Yes, on iOS 7 and later it is
  thread-safe for formatting. The real constraint is not mutating its settings while others use it,
  which a `static let` you configure once avoids.
:::
