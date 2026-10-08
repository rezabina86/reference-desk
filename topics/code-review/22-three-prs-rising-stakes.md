---
title: 22 · Three PRs, rising stakes
summary: Three small pull requests in one round — a naming PR with a hidden float bug, a threading PR and an architecture PR — and how to split your time.
minutes: 30
group: Review this PR
sources:
- Blind · Airbnb iOS code review round — a repo with three PRs; points per comment, the last PR worth the most | https://www.teamblind.com/post/Airbnb-Code-Review-Round-OnE7Ex7H
- LeetCode Discuss · Deliveroo iOS — "A PR was provided and I had to review it and put comments" | https://leetcode.com/discuss/interview-experience/3917354/
- Apple · NSManagedObjectContext — a context must be used on its own queue | https://developer.apple.com/documentation/coredata/nsmanagedobjectcontext
---

*Shape: review this PR, three times · Reported: Airbnb — a repo with three PRs, points per comment,
the last PR worth the most; Deliveroo — "a PR was provided and I had to review it and put comments" ·
PR 1 (Foundation) compiled and run with Swift 6.4, broken and fixed, real output below. PR 2 and
PR 3 are UIKit: the broken versions were typechecked against the iOS SDK (iOS 18 deployment target)
in Swift 5 and Swift 6 mode; the fixes typecheck in Swift 6 mode with zero warnings, and their
Foundation-only parts (the cache actor, the view model) were run in harnesses. On-screen behaviour
checked by hand*

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

1. **`Uploaded == 1.0` is never true for ten chunks.** `Double` can't store 0.1 exactly, so ten of
   them add up to `0.9999999999999999` — run, not guessed. The upload finishes and the UI waits
   forever. A test with chunks of 0.5, 0.25, 0.25 passes, because those are exact in binary.
   My comment — *Blocking:* "Summing fractions in `Double` drifts — ten chunks of 0.1 sum to
   0.9999999999999999, so `isDone()` never returns true. Could we track which chunks finished
   (integers) and decide 'done' from that? Keep the fraction for the progress bar only."
2. **A retried chunk counts twice.** Report chunk 1 twice and skip chunk 2: the real output was
   `1.0 true` — "done" with a chunk never sent.
   My comment — *Blocking:* "If a chunk is retried and reports twice, it's added twice, and we can say 'done'
   with a chunk missing. A `Set` of finished chunk indices makes this idempotent."
3. **Out-of-range index traps.** `chunk_sizes[i]` crashes on a bad index. A `precondition` with a
   message makes the crash say why.
4. **Naming.** `upload_progress` and `chunk_sizes` aren't Swift style (types are `UpperCamelCase`,
   properties `lowerCamelCase`), and `Uploaded` reads like a type. `isDone()` reads better as a
   property, `isComplete`.
   My comment — *Nit:* "Swift API guidelines: `UploadProgress`, `chunkSizes`, `uploaded`. Happy to pair on a
   SwiftLint rule so this isn't on you to remember."
5. **Public mutable state.** Anyone can set `Uploaded` directly. `private(set)`.

**PR 2 — threading (worth more)**

1. **Data race on `images`.** A *concurrent* queue runs many blocks at once, so several can write the
   dictionary together, while `thumbnail(for:)` reads it from the caller's thread. A Swift
   `Dictionary` isn't thread-safe: this is a crash during a resize, or silently corrupt state.
   Swift 6 refuses the file (verified: `static let shared` is an error, plus two
   `Sendable`-capture warnings); Swift 5 mode compiles it without a word.
   My comment — *Blocking:* "`images` is written from a concurrent queue and read off-queue, which is a data
   race — it can crash on a resize. An `actor` would make the compiler enforce exclusive access,
   and it's a small change; sketch below."
2. **UI updated off main.** `completion` runs on the background queue, and the cell sets
   `imageView.image` there.
   My comment — *Blocking:* "The completion arrives on the thumbnails queue, so the cell touches UIKit off the
   main thread. If the cache becomes `async`, the cell can await it from a main-actor `Task`."
3. **Wrong thumbnail in a reused cell.** No cancellation and no identity check: a slow render for
   row 3 lands in the cell after it's been reused for row 40 (the bug from chapter 01).
4. **Duplicate work.** Ten cells asking for the same URL miss together and render ten times.
5. **Unbounded memory.** Every thumbnail is kept forever and nothing listens for memory warnings.
   Fine for twenty; not for a vault of two thousand.
6. **Singleton.** `ThumbnailCache.shared` can't be replaced in a test.
7. **Failures are cached as nothing.** A `nil` render is stored as `nil` — which is the same as "not
   cached", so it retries forever. Harmless here, but say it, and decide on purpose.

**PR 3 — architecture (worth most)**

1. **Core Data used on the wrong queue.** `viewContext` belongs to the main queue. The completion
   handler inserts into it and saves from URLSession's background queue. That breaks Core Data's
   threading rule — corrupt object graphs, crashes that never reproduce. Run with
   `-com.apple.CoreData.ConcurrencyDebug 1` and it traps on the spot.
   My comment — *Blocking:* "This writes to `viewContext` from URLSession's queue. Contexts must be used on their
   own queue; this tends to show up as rare, unreproducible crashes. Could the import move into a
   repository that uses `performBackgroundTask`?"
2. **Personal data in a URL and in analytics.** The email goes into a query string — which ends up
   in server logs, proxies and crash reports — and is sent to the analytics vendor. That's a privacy
   bug and possibly a compliance one. It's also not encoded: many servers decode `+` as a space, so
   `ana+orders@…` asks for a different address. The auth token already says who the user is.
   My comment — *Blocking:* "The email goes into the URL and into analytics. Query strings get logged
   server-side, and our analytics vendor shouldn't receive personal data. Could we call
   `/me/orders` and let the token identify the user, and drop the property from the event?"
3. **Crashes waiting to happen.** `as! AppDelegate` (breaks in a test host or an extension),
   `currentUser!` (logged out, or session expired), `try!` on fetch and decode (a 500 with an HTML
   body traps).
4. **UI updated off main** — `orders` and `reloadData()` from the background queue. Swift 6 mode
   warns about exactly these two lines (verified).
5. **Duplicates on every visit.** Each load inserts every order again with no upsert by `id`. Open
   the screen three times, see each order three times.
6. **Errors and empty state ignored.** No network, a 500, no orders — all show the same blank list.
7. **The layering problem underneath all of it.** One view controller knows the app delegate, the
   Core Data stack, the URL scheme, JSON, the session singleton and the analytics SDK. That's why
   every bug above lives here, and why none of it can be tested.
   My comment — *Suggestion (the comment that matters most):* "This screen does six jobs. What if it only knew
   an `OrderHistoryViewModel`, which asks an `OrderRepository` protocol for orders? The repository
   owns network and Core Data; analytics goes behind a protocol with a typed event. Then each piece
   gets a unit test with a fake. Happy to pair — I've sketched it below."
8. **Hidden singletons break tests.** `UserSession.shared` and `Analytics.shared` mean a test of this
   screen hits real global state, and tests can affect each other. Inject them.

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
**PR 1** — decide "done" with integers, keep the fraction for display:

```swift
struct UploadProgress {
    let chunkByteCounts: [Int]
    private(set) var uploadedChunks: Set<Int> = []

    init(chunkByteCounts: [Int]) {
        self.chunkByteCounts = chunkByteCounts
    }

    /// Idempotent: a retried chunk that reports twice is counted once.
    mutating func markChunkUploaded(at index: Int) {
        precondition(chunkByteCounts.indices.contains(index), "No chunk \(index)")
        uploadedChunks.insert(index)
    }

    var isComplete: Bool { uploadedChunks.count == chunkByteCounts.count }

    /// For the progress bar only — never for the "done" decision.
    var fractionCompleted: Double {
        let total = chunkByteCounts.reduce(0, +)
        guard total > 0 else { return 1 }
        let uploaded = uploadedChunks.reduce(0) { $0 + chunkByteCounts[$1] }
        return Double(uploaded) / Double(total)
    }
}
```

```text
ten chunks:    1.0 true
retry twice:   0.75 false
then the last: 1.0 true
0.1 x 10 sum:  0.9999999999999999
```

**PR 2** — an actor owns the dictionary and joins duplicate requests; the cell awaits on main:

```swift
/// Safe to call from any thread: the actor owns the dictionaries.
actor ThumbnailCache<Image: Sendable> {
    private var images: [URL: Image] = [:]
    private var inFlight: [URL: Task<Image?, Never>] = [:]
    private let render: @Sendable (URL) async -> Image?

    init(render: @escaping @Sendable (URL) async -> Image?) {
        self.render = render
    }

    func thumbnail(for url: URL) async -> Image? {
        if let cached = images[url] { return cached }
        if let running = inFlight[url] { return await running.value }   // join, don't re-render
        let task = Task.detached(priority: .userInitiated) { [render] in await render(url) }
        inFlight[url] = task
        let image = await task.value
        inFlight[url] = nil
        if let image { images[url] = image }
        return image
    }
}

final class DocumentCell: UITableViewCell {
    private var thumbnailTask: Task<Void, Never>?

    override func prepareForReuse() {
        super.prepareForReuse()
        thumbnailTask?.cancel()
        imageView?.image = nil
    }

    func configure(with url: URL, thumbnails: ThumbnailCache<UIImage>) {
        thumbnailTask?.cancel()
        thumbnailTask = Task { [weak self] in          // inherits the main actor
            let image = await thumbnails.thumbnail(for: url)
            guard !Task.isCancelled else { return }    // the cell was reused meanwhile
            self?.imageView?.image = image
            self?.setNeedsLayout()
        }
    }
}

// Composition root: one cache for the app, handed to whoever needs it.
@MainActor
func makeThumbnailCache() -> ThumbnailCache<UIImage> {
    ThumbnailCache { url in
        UIImage(contentsOfFile: url.path)?
            .preparingThumbnail(of: CGSize(width: 120, height: 120))
    }
}
```

The cache, run with a fake image type — 1,000 concurrent requests for 10 URLs:

```text
requests: 1000 renders: 10 distinct: 10
```

**PR 3** — the screen knows one thing, a view model; the view model knows protocols:

```swift
struct Order: Identifiable, Equatable, Sendable {
    let id: String
    let total: Decimal
}

protocol OrderRepository: Sendable {
    func cachedOrders() async throws -> [Order]
    func refreshOrders() async throws -> [Order]
}

enum AnalyticsEvent: Equatable, Sendable { case orderHistoryViewed }

protocol AnalyticsTracking: Sendable {
    func track(_ event: AnalyticsEvent)
}

@MainActor
final class OrderHistoryViewModel {
    enum State: Equatable {
        case loading
        case loaded([Order])
        case failed(String)
    }

    private(set) var state: State = .loading { didSet { onChange?(state) } }
    var onChange: ((State) -> Void)?
    private let repository: OrderRepository
    private let analytics: AnalyticsTracking

    init(repository: OrderRepository, analytics: AnalyticsTracking) {
        self.repository = repository
        self.analytics = analytics
    }

    func load() async {
        analytics.track(.orderHistoryViewed)
        if let cached = try? await repository.cachedOrders(), !cached.isEmpty {
            state = .loaded(cached)                       // show what we have at once
        }
        do {
            state = .loaded(try await repository.refreshOrders())
        } catch {
            if case .loaded = state { return }            // keep stale data over an error
            state = .failed("Couldn't load your orders.")
        }
    }
}

final class OrderHistoryViewController: UITableViewController {
    private let viewModel: OrderHistoryViewModel
    private var orders: [Order] = []

    init(viewModel: OrderHistoryViewModel) {
        self.viewModel = viewModel
        super.init(style: .plain)
    }

    required init?(coder: NSCoder) { fatalError("init(coder:) is not supported") }

    override func viewDidLoad() {
        super.viewDidLoad()
        tableView.register(UITableViewCell.self, forCellReuseIdentifier: "Order")
        viewModel.onChange = { [weak self] state in self?.render(state) }
        Task { [viewModel] in await viewModel.load() }
    }

    private func render(_ state: OrderHistoryViewModel.State) {
        switch state {
        case .loading:
            tableView.backgroundView = nil
        case .loaded(let orders):
            self.orders = orders
            tableView.backgroundView = orders.isEmpty ? Self.message("No orders yet.") : nil
        case .failed(let message):
            tableView.backgroundView = Self.message(message)
        }
        tableView.reloadData()
    }

    private static func message(_ text: String) -> UILabel {
        let label = UILabel()
        label.text = text
        label.textAlignment = .center
        label.numberOfLines = 0
        return label
    }

    override func tableView(_ tableView: UITableView, numberOfRowsInSection section: Int) -> Int {
        orders.count
    }

    override func tableView(_ tableView: UITableView, cellForRowAt indexPath: IndexPath) -> UITableViewCell {
        let cell = tableView.dequeueReusableCell(withIdentifier: "Order", for: indexPath)
        var content = cell.defaultContentConfiguration()
        content.text = orders[indexPath.row].total.formatted(.currency(code: "EUR"))
        cell.contentConfiguration = content
        return cell
    }
}
```

The view model, run against a fake repository (the states it published, then the analytics events):

```text
fresh ok      -> ["loaded(1)", "loaded(2)"] ["orderHistoryViewed"]
offline+cache -> ["loaded(1)"] ["orderHistoryViewed"]
offline empty -> ["failed"] ["orderHistoryViewed"]
```

Why each piece:

- **Integers for "done", `Double` for display (PR 1)** — counting is exact; summing fractions isn't.
  The `Set` makes a duplicate report harmless.
- **An `actor` instead of a concurrent queue (PR 2)** — an actor runs one piece of its code at a
  time, and the compiler stops anything outside from touching `images` directly. The `inFlight`
  dictionary means a second request for the same URL waits for the first render instead of
  starting its own — 10 renders for 1,000 requests.
- **`Task.detached` for the render** — shared work shouldn't inherit one caller's priority or be
  cancelled when one cell scrolls away; the other callers still want the image.
- **A cancellable `Task` in the cell** — it runs on main because the cell is main-actor, and a reused
  cell cancels it, so a late image never lands in the wrong row.
- **`OrderRepository` protocol (PR 3)** — the layering fix. The real one combines an API client
  (`GET /me/orders`, the token names the user) with a Core Data store that imports on a background
  context via `performBackgroundTask` and upserts by `id`. The screen never sees either.
- **A typed `AnalyticsEvent`** — an enum case can't carry an email by accident; a
  `[String: String]` dictionary invites it.
- **Cached first, then fresh, and stale beats an error** — the user sees their orders instantly and
  offline, and only sees "couldn't load" when there is truly nothing to show. Empty and failed get
  their own message, so neither looks like the other (point 6).
- **Everything injected through `init`** — no `UIApplication.shared.delegate`, no `.shared`; the
  harness above is the test the original couldn't have.
:::

::: Now write the tests
> "Good. You have ten minutes left — write me the tests you'd ask for on each PR before you
> approve it."

**What I'd test, and why**

1. **PR 1: ten chunks of a tenth each complete** — the reported bug. Adding `0.1` ten times never
   equalled `1.0`, so the upload never finished.
2. **PR 1: a retried chunk is counted once** — a chunk that reports twice must not push progress
   past the truth. One more test checks the fraction follows bytes, not chunk count.
3. **PR 2: a hundred concurrent requests for one URL render once** — the actor and its `inFlight`
   table are the fix; this proves duplicate requests join the first render.
4. **PR 2: a failed render (`nil`) is not cached** — otherwise one bad read hides the thumbnail
   forever.
5. **PR 3: cached orders show first, then fresh ones; offline with a cache keeps them; offline
   with nothing shows the error** — the three states the screen promises.
6. **PR 3: the screen view is tracked once, with no email** — the privacy fix.

I ran all of this with SwiftPM, without UIKit. I left out `DocumentCell` and
`OrderHistoryViewController`: they are thin, they only show what the cache and the view model give
them, and they aren't unit-tested. I'd check those on screen.

**The seam.** PR 1 needs none — it's a plain value type. PR 2's cache is generic over the image
type and takes its `render` function in `init`, so the test uses a `FakeImage` and a renderer that
counts its calls; no `UIImage` needed. PR 3's view model takes `OrderRepository` and
`AnalyticsTracking` protocols, so a *fake* repository returns cached or fresh orders or throws, and
a fake tracker records events.

```swift
import Testing
import Foundation
import Synchronization

// MARK: - PR 1

struct UploadProgressTests {
    @Test func tenChunksOfATenthEachComplete() {
        // The bug: 0.1 added ten times is 0.9999999999999999, so `== 1.0` never fired.
        var progress = UploadProgress(chunkByteCounts: Array(repeating: 100, count: 10))

        for index in 0..<10 { progress.markChunkUploaded(at: index) }

        #expect(progress.isComplete)
        #expect(progress.fractionCompleted == 1.0)
    }

    @Test func retriedChunkIsCountedOnce() {
        var progress = UploadProgress(chunkByteCounts: [100, 100, 100, 100])

        progress.markChunkUploaded(at: 0)
        progress.markChunkUploaded(at: 1)
        progress.markChunkUploaded(at: 2)
        progress.markChunkUploaded(at: 2)   // the retry reports again

        #expect(!progress.isComplete)
        #expect(progress.fractionCompleted == 0.75)
    }

    @Test func fractionFollowsBytesNotChunks() {
        var progress = UploadProgress(chunkByteCounts: [300, 100])

        progress.markChunkUploaded(at: 0)

        #expect(progress.fractionCompleted == 0.75)
    }
}

// MARK: - PR 2

/// Stands in for UIImage: the cache is generic, so the test needs no UIKit.
struct FakeImage: Sendable, Equatable {
    let url: URL
}

/// Counts renders and can be told to fail (return nil) for the first few.
final class FakeRenderer: Sendable {
    private let state: Mutex<(renders: Int, failuresLeft: Int)>

    init(failFirst failures: Int = 0) { state = Mutex((0, failures)) }

    var renders: Int { state.withLock { $0.renders } }

    func render(_ url: URL) async -> FakeImage? {
        let fails = state.withLock { state -> Bool in
            state.renders += 1
            guard state.failuresLeft > 0 else { return false }
            state.failuresLeft -= 1
            return true
        }
        await Task.yield()   // a real render suspends; give other callers a chance to pile up
        return fails ? nil : FakeImage(url: url)
    }
}

struct ThumbnailCacheTests {
    let url = URL(fileURLWithPath: "/docs/invoice.pdf")

    @Test func concurrentRequestsForOneURLRenderOnce() async {
        let renderer = FakeRenderer()
        let cache = ThumbnailCache<FakeImage> { await renderer.render($0) }

        let images = await withTaskGroup(of: FakeImage?.self) { group in
            for _ in 0..<100 { group.addTask { [url] in await cache.thumbnail(for: url) } }
            return await group.reduce(into: []) { $0.append($1) }
        }

        #expect(images.count == 100)
        #expect(images.allSatisfy { $0 == FakeImage(url: url) })
        #expect(renderer.renders == 1)
    }

    @Test func failedRenderIsNotCached() async {
        let renderer = FakeRenderer(failFirst: 1)
        let cache = ThumbnailCache<FakeImage> { await renderer.render($0) }

        let first = await cache.thumbnail(for: url)
        let second = await cache.thumbnail(for: url)

        #expect(first == nil)
        #expect(second == FakeImage(url: url))
        #expect(renderer.renders == 2)
    }
}

// MARK: - PR 3

/// A fake repository: each call returns what the test set, or throws.
struct FakeOrderRepository: OrderRepository {
    var cached: Result<[Order], URLError> = .success([])
    var fresh: Result<[Order], URLError> = .success([])

    func cachedOrders() async throws -> [Order] { try cached.get() }
    func refreshOrders() async throws -> [Order] { try fresh.get() }
}

final class FakeAnalytics: AnalyticsTracking {
    private let recorded = Mutex<[AnalyticsEvent]>([])

    var events: [AnalyticsEvent] { recorded.withLock { $0 } }

    func track(_ event: AnalyticsEvent) { recorded.withLock { $0.append(event) } }
}

@MainActor
struct OrderHistoryViewModelTests {
    let old = Order(id: "o-1", total: 10)
    let new = Order(id: "o-2", total: 25)
    let analytics = FakeAnalytics()

    /// Records every state the view model publishes, in order.
    func states(after repository: FakeOrderRepository) async -> [OrderHistoryViewModel.State] {
        let viewModel = OrderHistoryViewModel(repository: repository, analytics: analytics)
        var published: [OrderHistoryViewModel.State] = []
        viewModel.onChange = { published.append($0) }
        await viewModel.load()
        return published
    }

    @Test func showsCachedOrdersThenFreshOnes() async {
        let repository = FakeOrderRepository(cached: .success([old]), fresh: .success([old, new]))

        #expect(await states(after: repository) == [.loaded([old]), .loaded([old, new])])
    }

    @Test func offlineWithACacheKeepsTheCachedOrders() async {
        let repository = FakeOrderRepository(cached: .success([old]),
                                             fresh: .failure(URLError(.notConnectedToInternet)))

        #expect(await states(after: repository) == [.loaded([old])])
    }

    @Test func offlineWithNothingCachedFails() async {
        let repository = FakeOrderRepository(cached: .success([]),
                                             fresh: .failure(URLError(.notConnectedToInternet)))

        #expect(await states(after: repository) == [.failed("Couldn't load your orders.")])
    }

    @Test func screenViewIsTrackedOnceWithNoPersonalData() async {
        _ = await states(after: FakeOrderRepository(fresh: .success([new])))

        // The event is an enum case with no payload, so an email has nowhere to go.
        #expect(analytics.events == [.orderHistoryViewed])
    }
}
```

Ran with Swift 6.4: 9 tests, all passed.
:::

::: What I'd ask next
- *"The author pushes back: 'the refactor is out of scope, it works'. What do you do?"* — Separate
  the must-fix from the nice-to-have. The wrong-queue Core Data write and the email in the URL block
  merge. The full layering refactor can be a follow-up ticket if they move the import into a
  repository now. Offer to pair on it.
- *"Why not `==` with a tolerance in PR 1?"* — It works (`abs(a - b) < 1e-9`), but you then have to pick
  the tolerance and it still double-counts retries. Counting chunks removes the question.
- *"Is a serial queue a fine fix for PR 2?"* — Yes, if every read *and* write goes through it, with
  `sync` for reads. Then say why I'd still pick the actor: the compiler checks it, a queue is a
  convention someone breaks in the next PR.
- *"How would you test PR 3's offline behaviour?"* — A fake repository whose refresh throws, with and
  without cached data, asserting the published states — exactly what the harness printed.
- *"Which one comment would you leave if you only had time for one per PR?"* — PR 1: the float `==`.
  PR 2: the race. PR 3: the view controller owning persistence and network — because fixing it
  fixes the queue bug, the duplicates and the testability with it.
:::
