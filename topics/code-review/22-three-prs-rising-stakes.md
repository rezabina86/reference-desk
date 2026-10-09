---
title: 22 · Three PRs, rising stakes
summary: Three small pull requests in one round — a naming PR with a hidden float bug, a threading PR and an architecture PR — and how to split your time.
minutes: 45
group: Review this PR
sources:
- Blind · Airbnb iOS code review round — a repo with three PRs; points per comment, the last PR worth the most | https://www.teamblind.com/post/Airbnb-Code-Review-Round-OnE7Ex7H
- LeetCode Discuss · Deliveroo iOS — "A PR was provided and I had to review it and put comments" | https://leetcode.com/discuss/interview-experience/3917354/
- Apple · NSManagedObjectContext — a context must be used on its own queue | https://developer.apple.com/documentation/coredata/nsmanagedobjectcontext
---

*Shape: review this PR, three times · Reported: Airbnb — a repo with three PRs, points per comment,
the last PR worth the most; Deliveroo — "a PR was provided and I had to review it and put comments" ·
Verified: PR 1 run with Swift 6.4; the UIKit fixes and all tests run on the iOS Simulator (Swift 6
mode)*

> "Three PRs from the same teammate, in this repo. Leave comments the way you would at work — each
> good comment scores, and each PR is worth more than the one before. You have forty-five minutes
> for all three. Go."

**PR 1 — "Add upload progress model"**

```swift
// + added: UploadProgress.swift
struct upload_progress {
    var chunk_sizes: [Double]          // fraction of the file in each chunk
    var Uploaded = 0.0

    mutating func chunkDone(_ i: Int) {
        Uploaded += chunk_sizes[i]
    }

    func isDone() -> Bool {
        return Uploaded == 1.0
    }
}
```

**PR 2 — "Cache document thumbnails"**

```swift
// + added: ThumbnailCache.swift
final class ThumbnailCache {
    static let shared = ThumbnailCache()
    private var images: [URL: UIImage] = [:]
    private let queue = DispatchQueue(label: "thumbnails", attributes: .concurrent)

    func thumbnail(for url: URL, completion: @escaping (UIImage?) -> Void) {
        if let cached = images[url] {
            completion(cached)
            return
        }
        queue.async {
            let image = UIImage(contentsOfFile: url.path)?
                .preparingThumbnail(of: CGSize(width: 120, height: 120))
            self.images[url] = image
            completion(image)
        }
    }
}

// DocumentCell.swift
  func configure(with url: URL) {
+     ThumbnailCache.shared.thumbnail(for: url) { image in
+         self.imageView?.image = image
+         self.setNeedsLayout()
+     }
  }
```

**PR 3 — "Order history screen"**

```swift
// + added: OrderHistoryViewController.swift
final class OrderHistoryViewController: UITableViewController {
    private var orders: [OrderEntity] = []

    override func viewDidLoad() {
        super.viewDidLoad()
        let context = (UIApplication.shared.delegate as! AppDelegate)
            .persistentContainer.viewContext
        orders = try! context.fetch(OrderEntity.fetchRequest())
        tableView.reloadData()

        let email = UserSession.shared.currentUser!.email
        let url = URL(string: "https://api.example.com/orders?email=\(email)")!
        URLSession.shared.dataTask(with: url) { data, _, _ in
            guard let data else { return }
            let dtos = try! JSONDecoder().decode([OrderDTO].self, from: data)
            for dto in dtos {
                let order = OrderEntity(context: context)
                order.id = dto.id
                order.total = dto.total
            }
            try? context.save()
            self.orders = try! context.fetch(OrderEntity.fetchRequest())
            self.tableView.reloadData()
        }.resume()

        Analytics.shared.track("order_history_viewed", properties: ["email": email])
    }
}
```

::: A hint, if you're stuck
- PR 1: add ten chunks of `0.1` in your head. Then report the same chunk twice, as a retry would.
- PR 2: the queue is *concurrent*. How many blocks can write `images` at the same moment? And who
  reads it outside the queue?
- PR 3: list every *kind* of thing the view controller talks to. A screen should talk to one.
- Timing: read all three before commenting on any. The last one pays most.
:::

::: The key — what I expect a senior to find
**PR 1 — style, plus one real bug (worth least, quick points)**

1. **Out-of-range index traps.** `chunk_sizes[i]` crashes on a bad index. A `precondition` with a
   message makes the crash say why.
2. **`Uploaded == 1.0` is never true for ten chunks.** `Double` can't store 0.1 exactly, so ten of
   them add up to `0.9999999999999999` — run, not guessed. The upload finishes and the UI waits
   forever. A test with chunks of 0.5, 0.25, 0.25 passes, because those are exact in binary.
   My comment — *Blocking:* "Summing fractions in `Double` drifts — ten chunks of 0.1 sum to
   0.9999999999999999, so `isDone()` never returns true. Could we track which chunks finished and
   decide 'done' by counting them? Keep the fraction for the progress bar only."
3. **A retried chunk counts twice.** With chunks `[0.5, 0.25, 0.25]`, report chunk 1 twice and skip
   chunk 2: the real output was `1.0 true` — "done" with a chunk never sent.
   My comment — *Blocking:* "If a chunk is retried and reports twice, it's added twice, and we can
   say 'done' with a chunk missing. A `Set` of finished chunk indices makes this idempotent."
4. **Public mutable state.** Anyone can set `Uploaded` directly. `private(set)`.
5. **Naming.** `upload_progress` and `chunk_sizes` aren't Swift style (types are `UpperCamelCase`,
   properties `lowerCamelCase`), and `Uploaded` reads like a type. `isDone()` reads better as a
   property, `isComplete`.
   My comment — *Nit:* "Swift API guidelines: `UploadProgress`, `chunkSizes`, `uploaded`. Happy to
   pair on a SwiftLint rule so this isn't on you to remember."

**PR 2 — threading (worth more)**

1. **Data race on `images`.** A *concurrent* queue runs many blocks at once, so several can write the
   dictionary together, while `thumbnail(for:)` reads it from the caller's thread. A Swift
   `Dictionary` isn't thread-safe: this is a crash during a resize, or silently corrupt state.
   Swift 6 refuses the file (verified: `static let shared` is an error, plus two
   `Sendable`-capture warnings); Swift 5 mode compiles it without a word.
   My comment — *Blocking:* "`images` is written from a concurrent queue and read off-queue, which
   is a data race — it can crash on a resize. Could the queue be serial, with the lookup and the
   write both inside `queue.async`?"
2. **UI updated off main.** On a miss, `completion` runs on the background queue, and the cell sets
   `imageView.image` there.
   My comment — *Blocking:* "The completion arrives on the thumbnails queue, so the cell touches
   UIKit off the main thread. Could the cache always call back on main?"
3. **Two threading behaviours in one API.** A hit calls `completion` at once, on the caller's thread;
   a miss calls it later, on a background queue. Callers can't write correct code against both.
   Always call back the same way: later, on main.
4. **Wrong thumbnail in a reused cell.** No identity check: a slow render for row 3 lands in the cell
   after it's been reused for row 40 (the bug from chapter 01). Remember the URL; check it on return.
5. **It can't render a PDF.** The cell is for documents, but `UIImage(contentsOfFile:)` only reads
   images, so a PDF gets `nil`. QuickLook Thumbnailing (`QLThumbnailGenerator`) renders both.
6. **The cache key ignores size and scale.** Ask for the same URL at 120 pt and 300 pt and you get
   the small one. Key by URL, size and scale.
7. **Duplicate work.** Ten cells asking for the same URL miss together and render ten times.
8. **Unbounded memory.** Every thumbnail is kept forever and nothing listens for memory warnings.
   Fine for twenty; not for a vault of two thousand. `NSCache` evicts on its own.
9. **Failures are cached as nothing.** A `nil` render is stored as `nil` — which is the same as "not
   cached", so it retries every time. Harmless here, but say it, and decide on purpose.
10. **Singleton.** `ThumbnailCache.shared` can't be replaced in a test. Keep `.shared` for the app if
    you like, but let the test build its own.

**PR 3 — architecture (worth most)**

1. **Crashes waiting to happen.** `as! AppDelegate` (breaks in a test host or an extension),
   `currentUser!` (logged out, or session expired), `try!` on fetch and decode (a 500 with an HTML
   body traps).
2. **Core Data used on the wrong queue.** `viewContext` belongs to the main queue. The completion
   handler inserts into it and saves from URLSession's background queue. That breaks Core Data's
   threading rule — corrupt object graphs, crashes that never reproduce. Run with
   `-com.apple.CoreData.ConcurrencyDebug 1` and it traps on the spot.
   My comment — *Blocking:* "This writes to `viewContext` from URLSession's queue. Contexts must be
   used on their own queue; this tends to show up as rare, unreproducible crashes. Could the import
   use `performBackgroundTask`?"
3. **UI updated off main** — `orders` and `reloadData()` from the background queue. Swift 6 mode
   warns about exactly these two lines (verified).
4. **Personal data in a URL and in analytics.** The email goes into a query string — which ends up
   in server logs, proxies and crash reports — and is sent to the analytics vendor. That's a privacy
   bug and possibly a compliance one. It's also not encoded: many servers decode `+` as a space, so
   `ana+orders@…` asks for a different address. The auth token already says who the user is.
   My comment — *Blocking:* "The email goes into the URL and into analytics. Query strings get
   logged server-side, and our analytics vendor shouldn't receive personal data. Could we call
   `/me/orders` and let the token identify the user, and drop the property from the event?"
5. **Duplicates on every visit.** Each load inserts every order again with no upsert by `id`. Open
   the screen three times, see each order three times.
6. **The HTTP status is ignored.** A 401 or a 500 with a JSON error body goes straight to the decoder.
   Check for a 2xx before decoding.
7. **Errors and empty state ignored.** No network, a 500, no orders — all show the same blank list.
8. **No sort descriptor.** A Core Data fetch without one comes back in no promised order, so the
   list can reshuffle between visits. Sort by date, newest first.
9. **Money as `Double`.** `total` can't hold 12.99 exactly, and sums drift. Use `Decimal` (a Core
   Data migration), and format it with the order's own currency, not a hard-coded one.
10. **The request isn't cancelled.** Leave the screen and the task still runs, saves and reloads a
    table nobody sees. Keep the task and cancel it in `deinit` or on disappear.
11. **The layering problem underneath all of it.** One view controller knows the app delegate, the
    Core Data stack, the URL scheme, JSON, the session singleton and the analytics SDK. That's why
    every bug above lives here, and why none of it can be tested.
    My comment — *Suggestion (the comment that matters most):* "This screen does six jobs. What if
    it only talked to a presenter, which asks an `OrderRepository` for orders? The repository owns
    network and Core Data; analytics goes behind a protocol with a typed event. Then each piece gets
    a unit test with a fake. Happy to pair on it."
12. **Hidden singletons break tests.** `UserSession.shared` and `Analytics.shared` mean a test of
    this screen hits real global state, and tests can affect each other. Inject them.

**How I'd split forty-five minutes.** Read all three first (five minutes) — you need to know where
the points are. Then go in order but spend time by value: PR 1 in about seven minutes (the float
bug, the retry bug, one comment for naming — don't write five nits), PR 2 in about twelve (race,
main thread, reuse), and the rest on PR 3. Write blocking comments first in each PR, so if time runs
out the important ones are already posted. Group style nits into one comment. And label every
comment — *Blocking*, *Suggestion*, *Nit* — so the author knows what must change before merge.
:::

::: The idea behind it
A good review comment does three jobs. It says **what** is wrong, **why** it matters to a user or
the team, and **what to do** instead. "This is bad" does none of them. "This races" does one.

It also has a *severity label*. A blocker must be fixed before merge; a suggestion is worth doing;
a nit is a small style point the author may skip. Labels stop a reviewer's twelve comments from all
feeling equally urgent.

Then the stakes. A *style* problem costs a few seconds of reading. A *bug* costs one feature. A
*threading* problem costs crashes nobody can reproduce. An *architecture* problem — a screen that
reaches into the database and the network itself, called a *layering violation* — costs every
future change to that screen, because each one drags the database and the network along. That's
why the last PR is worth the most: its fix makes the other bugs impossible, not just fixed.

Kindness isn't decoration. A review is how a team teaches. Ask questions ("could we…?"), offer to
pair, and say what's good when something is.
:::

::: The fix
**PR 1** — count finished chunks for "done"; keep the fractions for the bar:

```swift
struct UploadProgress {
    let chunkSizes: [Double]                       // key 5: Swift names; fractions, for the bar only
    private(set) var finished: Set<Int> = []       // key 3, 4: a retry is counted once

    init(chunkSizes: [Double]) { self.chunkSizes = chunkSizes }

    mutating func chunkDone(_ i: Int) {
        precondition(chunkSizes.indices.contains(i), "No chunk \(i)")      // key 1
        finished.insert(i)
    }

    var uploaded: Double { finished.reduce(0) { $0 + chunkSizes[$1] } }    // display only
    var isComplete: Bool { finished.count == chunkSizes.count }           // key 2: count, don't compare
}
```

**PR 2** — a serial queue owns the dictionary; every answer comes back later, on main; the cell
checks it still wants it:

```swift
final class ThumbnailCache: @unchecked Sendable {  // safe: `images` is only touched on `queue`
    static let shared = ThumbnailCache { url in
        UIImage(contentsOfFile: url.path)?.preparingThumbnail(of: CGSize(width: 120, height: 120))
    }
    private var images: [URL: UIImage] = [:]
    private let queue = DispatchQueue(label: "thumbnails")       // key 1: serial, not concurrent
    private let render: @Sendable (URL) -> UIImage?

    init(render: @escaping @Sendable (URL) -> UIImage?) { self.render = render }

    func thumbnail(for url: URL, completion: @escaping @MainActor (UIImage?) -> Void) {
        queue.async {                                            // key 1: read and write on the queue
            let image = self.images[url] ?? self.render(url)
            self.images[url] = image
            DispatchQueue.main.async { completion(image) }       // key 2, 3: always main, always later
        }
    }
}

final class DocumentCell: UITableViewCell {
    private var representedURL: URL?                             // key 4

    func configure(with url: URL) {
        representedURL = url
        imageView?.image = nil
        ThumbnailCache.shared.thumbnail(for: url) { [weak self] image in
            guard let self, self.representedURL == url else { return }   // reused meanwhile
            self.imageView?.image = image
            self.setNeedsLayout()
        }
    }
}
```

**PR 3** — Core Data on its own queue, no email anywhere, no force-anything, an error message:

```swift
protocol OrderLoading: Sendable {                                // the one seam
    func fetchOrders(completion: @escaping @Sendable (Result<[OrderDTO], Error>) -> Void)
}

struct OrderAPI: OrderLoading {
    func fetchOrders(completion: @escaping @Sendable (Result<[OrderDTO], Error>) -> Void) {
        let url = URL(string: "https://api.example.com/me/orders")!     // key 4: the token names the user
        URLSession.shared.dataTask(with: url) { data, response, error in
            guard let data, (response as? HTTPURLResponse)?.statusCode == 200 else {   // key 6
                return completion(.failure(error ?? URLError(.badServerResponse)))
            }
            completion(Result { try JSONDecoder().decode([OrderDTO].self, from: data) })  // key 1
        }.resume()
    }
}

final class OrderHistoryViewController: UITableViewController {
    private var orders: [OrderEntity] = []
    private let container: NSPersistentContainer                 // key 1: no `as! AppDelegate`
    private let loader: OrderLoading

    init(container: NSPersistentContainer, loader: OrderLoading) {
        self.container = container
        self.loader = loader
        super.init(style: .plain)
    }
    required init?(coder: NSCoder) { fatalError("init(coder:) is not supported") }

    override func viewDidLoad() {
        super.viewDidLoad()
        showStoredOrders()
        loader.fetchOrders { result in
            DispatchQueue.main.async { self.handle(result) }     // key 3: back to main first
        }
        Analytics.shared.track("order_history_viewed", properties: [:])  // key 4: no email
    }

    private func handle(_ result: Result<[OrderDTO], Error>) {
        guard case .success(let dtos) = result else { return showMessage("Couldn't load your orders.") }
        container.performBackgroundTask { context in             // key 2: its own queue
            try? Self.importOrders(dtos, into: context)         // a failed import keeps what's shown
            DispatchQueue.main.async { self.showStoredOrders() }
        }
    }

    nonisolated static func importOrders(_ dtos: [OrderDTO], into context: NSManagedObjectContext) throws {
        for dto in dtos {                                        // key 5: upsert by id
            let request = OrderEntity.fetchRequest()
            request.predicate = NSPredicate(format: "id == %@", dto.id)
            let order = try context.fetch(request).first ?? OrderEntity(context: context)
            order.id = dto.id
            order.total = dto.total
        }
        try context.save()
    }

    private func showStoredOrders() {
        orders = (try? container.viewContext.fetch(OrderEntity.fetchRequest())) ?? []
        tableView.backgroundView = nil
        tableView.reloadData()
    }

    private func showMessage(_ text: String) {                  // key 7
        let label = UILabel()
        label.text = text
        label.textAlignment = .center
        tableView.backgroundView = label
    }
}
```

**Said out loud, not coded:** a presenter and an `OrderRepository` behind the screen · an `actor`
cache with in-flight de-duplication and a bounded `NSCache` · `QLThumbnailGenerator` for PDFs ·
`Decimal` money (a migration) · a sort descriptor · cancel the request on disappear · inject
analytics with a typed event · key the cache by size and scale.

- **Why a serial queue and not an actor (PR 2).** It's the smallest change that removes the race,
  and it keeps the completion-handler API the cells already use. Because the lookup, the render and
  the write all run on one queue, a second request for the same URL waits and then hits the cache.
- **Why `@unchecked Sendable`.** The compiler can't see that `images` is only touched on `queue`, so
  the comment says it. That promise is the price of GCD; an actor would let the compiler check it.
- **Why `OrderLoading` is the one seam (PR 3).** The test needs a load that fails without a network.
  The container is passed in `init` too, which replaces `as! AppDelegate` without a new protocol.
- **Why `importOrders` is `static`.** It runs on the background context's queue, so it must not touch
  the view controller — and a static function can't by accident. It's also what the test calls.
:::

::: Now write the tests
> "Good. You have ten minutes left — write me the tests you'd ask for on each PR before you
> approve it."

**What I'd test, and why**

1. **PR 1: ten chunks of a tenth each complete** — the bug. Adding `0.1` ten times never equalled
   `1.0`, so the upload never finished.
2. **PR 1: a retried chunk is counted once** — the edge case: a retry must not mark the upload done
   with a chunk missing.
3. **PR 2: two requests for one URL render once** — the serial queue is the fix; this proves the
   second request finds the first one's result instead of racing it.
4. **PR 2: a cache hit still calls back later, on main** — the regression guard for "two threading
   behaviours". The result is a `@MainActor` object, so the callback can only touch it on main.
5. **PR 3: a failed load shows an error, not a blank list** — through the one seam, a loader that
   fails.
6. **PR 3: importing the same order twice keeps one** — the upsert, against an in-memory store.

The cache takes its `render` closure in `init`, so the test counts renders and never touches disk.
The view controller takes `OrderLoading`, so a fake fails on demand. I don't unit-test the cell; I'd
check it on screen. `OrderModel.makeInMemoryContainer()` is a small test helper that builds the
Core Data stack in memory. The async waits use `waitUntil(maxYields:_:)`, which counts yields
instead of watching a clock.

```swift
import CoreData
import Synchronization
import Testing
import UIKit

/// Yield-count bounded, no clocks: gives queued main-thread work a turn until `condition` holds.
@MainActor
func waitUntil(maxYields: Int = 1_000, _ condition: () -> Bool) async -> Bool {
    for _ in 0..<maxYields {
        if condition() { return true }
        await Task.yield()
    }
    return condition()
}

// MARK: - PR 1

struct UploadProgressTests {
    @Test func tenChunksOfATenthEachComplete() {
        // The bug: 0.1 added ten times is 0.9999999999999999, so `== 1.0` never fired.
        var progress = UploadProgress(chunkSizes: Array(repeating: 0.1, count: 10))

        for i in 0..<10 { progress.chunkDone(i) }

        #expect(progress.isComplete)
    }

    @Test func retriedChunkIsCountedOnce() {
        var progress = UploadProgress(chunkSizes: [0.5, 0.25, 0.25])

        progress.chunkDone(0)
        progress.chunkDone(1)
        progress.chunkDone(1)                  // the retry reports again; chunk 2 never came

        #expect(!progress.isComplete)
        #expect(progress.uploaded == 0.75)
    }
}

// MARK: - PR 2

/// Counts renders; safe to call from the cache's queue.
final class RenderCounter: Sendable {
    private let count = Mutex(0)
    var renders: Int { count.withLock { $0 } }
    func render(_ url: URL) -> UIImage? {
        count.withLock { $0 += 1 }
        return UIImage()
    }
}

@MainActor
final class CallOrder {
    var events: [String] = []
}

@MainActor
struct ThumbnailCacheTests {
    let url = URL(fileURLWithPath: "/docs/invoice.pdf")

    @Test func twoRequestsForOneURLRenderOnce() async {
        let counter = RenderCounter()
        let cache = ThumbnailCache(render: counter.render)

        await withCheckedContinuation { done in
            cache.thumbnail(for: url) { _ in }
            cache.thumbnail(for: url) { _ in done.resume() }
        }

        #expect(counter.renders == 1)
    }

    @Test func aCacheHitStillCallsBackLaterOnMain() async {
        let cache = ThumbnailCache(render: RenderCounter().render)
        await withCheckedContinuation { done in cache.thumbnail(for: url) { _ in done.resume() } }

        let order = CallOrder()                // @MainActor: the callback can only touch it on main
        await withCheckedContinuation { done in
            cache.thumbnail(for: url) { _ in
                order.events.append("callback")
                done.resume()
            }
            order.events.append("returned")
        }

        #expect(order.events == ["returned", "callback"])
    }
}

// MARK: - PR 3

struct FailingLoader: OrderLoading {
    func fetchOrders(completion: @escaping @Sendable (Result<[OrderDTO], Error>) -> Void) {
        completion(.failure(URLError(.notConnectedToInternet)))
    }
}

@MainActor
struct OrderHistoryTests {
    @Test func failedLoadShowsAnErrorNotABlankList() async {
        let screen = OrderHistoryViewController(container: OrderModel.makeInMemoryContainer(),
                                                loader: FailingLoader())

        screen.loadViewIfNeeded()

        let shown = await waitUntil {
            (screen.tableView.backgroundView as? UILabel)?.text == "Couldn't load your orders."
        }
        #expect(shown)
    }

    @Test func importingTheSameOrderTwiceKeepsOne() async throws {
        let container = OrderModel.makeInMemoryContainer()
        let context = container.newBackgroundContext()
        let order = OrderDTO(id: "o-1", total: 25)

        try await context.perform {            // a second visit imports the same order again
            try OrderHistoryViewController.importOrders([order], into: context)
            try OrderHistoryViewController.importOrders([order], into: context)
        }

        #expect(try container.viewContext.count(for: OrderEntity.fetchRequest()) == 1)
    }
}
```

Ran on the iOS Simulator (Swift 6 mode): 6 tests, all passed.
:::

::: What I'd ask next
- *"The author pushes back: 'the refactor is out of scope, it works'. What do you do?"* — Separate
  the must-fix from the nice-to-have. The wrong-queue Core Data write and the email in the URL block
  merge; the fix above is small. The presenter and repository can be a follow-up ticket. Offer to
  pair on it.
- *"Why not `==` with a tolerance in PR 1?"* — It works (`abs(a - b) < 1e-9`), but you then have to
  pick the tolerance and it still double-counts retries. Counting chunks removes the question.
- *"Why not an actor in PR 2?"* — I'd like one next: the compiler checks the isolation, and an
  `inFlight` table lets ten callers share one render. But it changes the API to `async`, so every
  cell changes too. The serial queue fixes the race today without that.
- *"There's no empty state yet. Add one and test it."* — When the stored orders come back empty,
  show "No orders yet" the same way as the error. The test is a loader that returns `[]`, then
  `waitUntil` the message appears. Same seam, one more fake.
- *"Which one comment would you leave if you only had time for one per PR?"* — PR 1: the float `==`.
  PR 2: the race. PR 3: the view controller owning persistence and network — because fixing it
  fixes the queue bug, the duplicates and the testability with it.
:::
