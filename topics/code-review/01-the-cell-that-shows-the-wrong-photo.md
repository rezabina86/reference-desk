---
title: 01 · The cell that shows the wrong photo
summary: A feed screen with an image cell, a refresh timer and a notification observer — review it.
minutes: 20
group: Review this PR
sources:
- Glassdoor · Delivery Hero Senior iOS — "what is a retain cycle, and in which scenarios" | https://www.glassdoor.com/Interview/Delivery-Hero-Senior-IOS-Developer-Interview-Questions-EI_IE504556.0,13_KO14,34.htm
- Apple · Timer — a target-based timer keeps a strong reference to its target | https://developer.apple.com/documentation/foundation/timer
- Apple · NotificationCenter — block-based observers return a token you must keep and remove | https://developer.apple.com/documentation/foundation/notificationcenter
- Apple · UIImage — byPreparingThumbnail(ofSize:) for downsampling | https://developer.apple.com/documentation/uikit/uiimage
---

*Shape: review this PR · Reported: retain-cycle scenarios (Delivery Hero), UIKit code review
(fintech manager rounds) · Verified: the fix builds in Swift 6 mode with no warnings and its
tests ran on the iOS 18.5 Simulator, Swift 6.4*

> "This is a feed screen a teammate opened a PR for. Users say photos sometimes appear in the wrong
> rows, and memory grows every time they open and close the feed. Review it — ten minutes."

```swift
final class PhotoCell: UITableViewCell {
    @IBOutlet var photoView: UIImageView!

    func configure(with url: URL) {
        URLSession.shared.dataTask(with: url) { data, _, _ in
            guard let data else { return }
            DispatchQueue.main.async {
                self.photoView.image = UIImage(data: data)
            }
        }.resume()
    }
}

final class FeedViewController: UIViewController, UITableViewDataSource {
    @IBOutlet var tableView: UITableView!
    private var timer: Timer?
    private var photos: [URL] = []

    override func viewDidLoad() {
        super.viewDidLoad()
        timer = Timer.scheduledTimer(timeInterval: 30, target: self,
                                     selector: #selector(refresh),
                                     userInfo: nil, repeats: true)
        NotificationCenter.default.addObserver(
            forName: UIApplication.didBecomeActiveNotification,
            object: nil, queue: .main) { _ in
            self.refresh()
        }
    }

    deinit {
        timer?.invalidate()
    }

    @objc func refresh() {
        PhotoAPI.shared.latest { urls in
            self.photos = urls
            self.tableView.reloadData()
        }
    }

    func tableView(_ tableView: UITableView, numberOfRowsInSection section: Int) -> Int {
        photos.count
    }

    func tableView(_ tableView: UITableView, cellForRowAt indexPath: IndexPath) -> UITableViewCell {
        let cell = tableView.dequeueReusableCell(withIdentifier: "PhotoCell", for: indexPath) as! PhotoCell
        cell.configure(with: photos[indexPath.row])
        return cell
    }
}
```

::: A hint, if you're stuck
- Table cells are reused. What happens if a download finishes after its cell has moved to another row?
- Who keeps a `Timer` alive, and what does the timer keep alive?
- Where is the only `invalidate()`, and when does that code run?
- The timer and the app coming back to the foreground can both call `refresh()`. Whose answer lands last?
:::

::: The key — what I expect a senior to find
The two reported bugs come first; the rest is by severity.

1. **Wrong photo in a row (the reported bug).** Cells are reused. A slow download for row 3
   finishes after the cell has been reused for row 40 and writes row 3's image into it. Nothing
   cancels the old request or checks that the cell still wants that URL. Keep the load as a task
   and cancel it on reuse.
2. **The timer leaks the screen (the reported memory growth).** A target-based `Timer` holds its
   target strongly, and the run loop holds the timer. So the controller is never freed, and
   `deinit` — where the only `invalidate()` lives — never runs. The cleanup lives in the one place
   that can never run. Invalidate when the screen disappears.
3. **The observer leaks it too.** The block captures `self` strongly, and the returned token is
   thrown away, so it can never be removed. NotificationCenter keeps the block — and the
   controller — alive for the life of the app. Capture `[weak self]`, keep the token, remove it.
4. **Each leaked screen keeps refreshing.** Open and close the feed five times and five timers
   fire every 30 seconds, each doing network work for an invisible screen.
5. **`refresh` updates the UI from an unknown thread.** Nothing says `PhotoAPI` calls back on
   main. Hop to main before touching `photos` and the table.
6. **Overlapping refreshes.** The timer and `didBecomeActive` can both fire close together. Two
   requests run, and the older reply can land last and overwrite the newer list. Allow one refresh
   at a time, or drop a reply that isn't the latest.
7. **`refresh` captures `self` strongly** — milder than 2–3, but every request keeps the screen
   alive until it answers. Use `[weak self]`.
8. **No `prepareForReuse`.** The old photo stays visible in the new row until the new one arrives.
9. **Images decoded at full size, on the main thread.** `UIImage(data:)` doesn't decode yet; the
   decode happens on main at first draw, which is a scroll hitch. And a 12-megapixel photo becomes
   ~48 MB of bitmap for a 100-point row. Prepare the image off main, and downsample it to the
   display size in pixels (points × screen scale).
10. **The timer fires while off screen.** Start it in `viewWillAppear`, stop it in
    `viewDidDisappear` — which is also the leak fix.
11. **No caching.** Scrolling back up downloads every image again.
12. **Errors ignored** — no placeholder, no retry.
13. **The cell does networking.** A view shouldn't know about URLs and sessions. Give it an image
    loader it can be handed — which is also the test seam.
14. **Singletons** — `URLSession.shared`, `PhotoAPI.shared` — make the screen hard to test.
15. **`as!` on dequeue** — acceptable to many teams, but say you know it crashes on a
    misconfigured identifier.
:::

::: The idea behind it
Two ideas carry this whole snippet: cell reuse and retain cycles.

A table view doesn't make one cell per row. It makes just enough to fill the screen, and when a row
scrolls off, its cell is *reused* for the row scrolling on — like a café reusing the same few
tables for a stream of guests. Anything you started for the old guest, such as a download, can
finish after the new guest has sat down. So a cell must cancel, or ignore, old work when it is
reused.

The leak is a *retain cycle*. Swift frees an object when nothing holds a *strong* reference to it
any more — that's ARC, automatic reference counting. A repeating timer is held by the run loop, and
it holds its target strongly. So the screen can't be freed while the timer exists, and the only code
that stops the timer is in `deinit`, which only runs once the screen is freed. Each waits for the
other. A block-based notification observer does the same: NotificationCenter keeps the block, and
the block keeps `self`.

The cure has two parts. Hold `self` *weakly* (`[weak self]`) — a reference that doesn't keep the
object alive. And stop timers and observers when the screen goes away, not in `deinit`. Once
`invalidate()` runs, the run loop lets go of the timer and the timer lets go of the screen.
:::

::: The fix
```swift
protocol ImageLoading: Sendable {                                    // key 13: the one seam
    func image(for url: URL) async throws -> UIImage
}

extension URLSession: ImageLoading {
    func image(for url: URL) async throws -> UIImage {
        let (data, _) = try await data(from: url)
        guard let image = await UIImage(data: data)?.byPreparingForDisplay()   // key 9: decode off main
        else { throw URLError(.cannotDecodeContentData) }
        return image
    }
}

final class PhotoCell: UITableViewCell {
    @IBOutlet var photoView: UIImageView!
    var loader: ImageLoading = URLSession.shared                     // tests pass a fake
    private var loadTask: Task<Void, Never>?                         // key 1

    override func prepareForReuse() {                                // key 8
        super.prepareForReuse()
        loadTask?.cancel()
        photoView.image = nil
    }

    func configure(with url: URL) {
        loadTask?.cancel()                                           // key 1
        loadTask = Task { [weak self, loader] in
            guard let image = try? await loader.image(for: url),
                  !Task.isCancelled else { return }                  // key 1: reused, so cancelled: drop it
            self?.photoView.image = image
        }
    }
}

final class FeedViewController: UIViewController, UITableViewDataSource {
    @IBOutlet var tableView: UITableView!
    private var timer: Timer?
    private var observer: NSObjectProtocol?                          // key 3: keep the token
    private var photos: [URL] = []

    override func viewWillAppear(_ animated: Bool) {                 // key 2, 10: start on appear...
        super.viewWillAppear(animated)
        stopRefreshing()                                             // a cancelled swipe-back appears twice
        timer = Timer.scheduledTimer(timeInterval: 30, target: self,
                                     selector: #selector(refresh),
                                     userInfo: nil, repeats: true)
        observer = NotificationCenter.default.addObserver(
            forName: UIApplication.didBecomeActiveNotification,
            object: nil, queue: .main) { [weak self] _ in            // key 3
            MainActor.assumeIsolated { self?.refresh() }             // queue: .main, so we are on main
        }
    }

    override func viewDidDisappear(_ animated: Bool) {               // ...stop on disappear, not in deinit
        super.viewDidDisappear(animated)
        stopRefreshing()
    }

    private func stopRefreshing() {
        timer?.invalidate()                                          // key 2
        timer = nil
        if let observer { NotificationCenter.default.removeObserver(observer) }
        observer = nil
    }

    @objc func refresh() {
        PhotoAPI.shared.latest { [weak self] urls in                 // key 7
            DispatchQueue.main.async {                               // key 5
                self?.photos = urls
                self?.tableView.reloadData()
            }
        }
    }

    // numberOfRowsInSection and cellForRowAt are unchanged; deinit is gone.
}
```

**Said out loud, not coded:** downsampling to points × screen scale (`CGImageSource` thumbnails)
and an `NSCache` inside the loader; one refresh at a time (key 6); `PhotoAPI` injected instead of
`.shared`; placeholder and retry on error.

Why each piece:

- **A `Task` in the cell** — cancellation comes for free, and the task runs on the main actor (the
  cell is a view), so the image is set on main. The `!Task.isCancelled` check is the identity
  check: a reused cell has cancelled the old task before it can write.
- **The target-based `Timer` stays.** It was never the problem — the problem was invalidating in
  `deinit`. Invalidating in `viewDidDisappear` breaks the cycle, so no closure timer is needed.
- **`MainActor.assumeIsolated` in the observer** — in Swift 6 the block isn't known to be on the
  main actor, so it can't call `refresh()` directly. `queue: .main` means it runs on main;
  `assumeIsolated` says so, and traps if that is ever wrong.
- **`stopRefreshing()` at the top of `viewWillAppear`** — start a swipe-back and let go, and UIKit
  calls `viewWillAppear` again without `viewDidDisappear`. Without the reset, that makes a second
  timer and observer.
:::

::: Now write the tests
> "Good. Now write me a few tests — one for the wrong photo, and one that proves the leak is gone."

**What I'd test, and why**

1. **A late reply for the old URL never shows.** Configure the cell for A, reuse it for B, then let
   A's photo arrive. The cell must not show A. This is the reported bug, so it goes first.
2. **Reuse clears the old photo** — no stale image while the new one loads.
3. **The screen is freed after it closes.** A *weak reference* (one that doesn't keep the object
   alive) becomes `nil` only if nothing else holds the screen — so the test fails if the timer or
   the observer still does. This is the reported leak.
4. **A closed screen stops refreshing.** Post `didBecomeActive` after the screen closed; no
   refresh may happen.

I wouldn't test `Timer` or `NotificationCenter` themselves, or the image loader's cache — that has
its own tests.

**The seam.** The cell's `loader` property defaults to `URLSession.shared`; the test sets a
*fake*: a stand-in that holds each load until the test says which photo arrives, and when. That's
how the test makes A arrive *after* B was asked for — every run, no timing. The snippet doesn't
show `PhotoAPI`, so the test project defines a small stand-in next to the screen that counts
calls to `latest` and never answers. UIKit's `beginAppearanceTransition` drives the appear and disappear callbacks by
hand.

```swift
import Synchronization

// Next to the screen in the test project: a stand-in for PhotoAPI that counts calls and never answers.
final class PhotoAPI: Sendable {
    static let shared = PhotoAPI()
    private let calls = Mutex(0)
    var latestCallCount: Int { calls.withLock { $0 } }

    func latest(_ completion: @escaping @Sendable ([URL]) -> Void) {
        calls.withLock { $0 += 1 }
    }
}
```

```swift
import Testing
import UIKit

/// A fake loader: each load waits until the test says which photo arrives.
@MainActor
final class FakeImageLoader: ImageLoading {
    private var waiting: [URL: CheckedContinuation<UIImage, any Error>] = [:]
    var requestCount: Int { waiting.count }

    func image(for url: URL) async throws -> UIImage {
        try await withCheckedThrowingContinuation { waiting[url] = $0 }
    }

    func finish(_ url: URL, with image: UIImage) {
        waiting.removeValue(forKey: url)?.resume(returning: image)
    }
}

/// Gives queued main-actor work a turn until `condition` holds. Bounded by a count, not a clock.
@MainActor
func waitUntil(maxYields: Int = 1_000, _ condition: () -> Bool) async {
    for _ in 0..<maxYields where !condition() { await Task.yield() }
}

@MainActor
func makeCell(loader: FakeImageLoader) -> PhotoCell {
    let cell = PhotoCell(style: .default, reuseIdentifier: "PhotoCell")
    cell.photoView = UIImageView()                  // what the storyboard would connect
    cell.loader = loader
    return cell
}

extension UIViewController {
    // UIKit's own way to drive the appear and disappear callbacks by hand.
    func appear() { beginAppearanceTransition(true, animated: false); endAppearanceTransition() }
    func disappear() { beginAppearanceTransition(false, animated: false); endAppearanceTransition() }
}

@MainActor
@Suite(.serialized)
struct FeedTests {
    let urlA = URL(string: "https://example.com/a.jpg")!
    let urlB = URL(string: "https://example.com/b.jpg")!
    let photoA = UIImage(systemName: "a.circle")!
    let photoB = UIImage(systemName: "b.circle")!

    @Test func lateReplyForTheOldURLNeverShows() async {
        // Given a cell configured for A, then reused for B before A arrived
        let loader = FakeImageLoader()
        let cell = makeCell(loader: loader)
        cell.configure(with: urlA)
        cell.prepareForReuse()
        cell.configure(with: urlB)
        await waitUntil { loader.requestCount == 2 }

        // When A's photo arrives late
        loader.finish(urlA, with: photoA)
        await waitUntil(maxYields: 100) { false }   // give the late reply its turns

        // Then the cell ignores it, and shows B once B arrives
        #expect(cell.photoView.image == nil)
        loader.finish(urlB, with: photoB)
        await waitUntil { cell.photoView.image != nil }
        #expect(cell.photoView.image === photoB)
    }

    @Test func reuseClearsTheOldPhoto() async {
        let loader = FakeImageLoader()
        let cell = makeCell(loader: loader)
        cell.configure(with: urlA)
        await waitUntil { loader.requestCount == 1 }
        loader.finish(urlA, with: photoA)
        await waitUntil { cell.photoView.image != nil }

        cell.prepareForReuse()

        #expect(cell.photoView.image == nil)
    }

    @Test func screenIsReleasedAfterItCloses() {
        weak var weakScreen: FeedViewController?
        autoreleasepool {
            let screen = FeedViewController()
            screen.appear()                         // starts the timer and the observer
            screen.disappear()
            weakScreen = screen
        }
        #expect(weakScreen == nil)
    }

    @Test func closedScreenStopsRefreshing() {
        // Given a screen that was shown and closed
        let screen = FeedViewController()
        screen.appear()
        screen.disappear()
        let before = PhotoAPI.shared.latestCallCount

        // When the app becomes active again
        NotificationCenter.default.post(name: UIApplication.didBecomeActiveNotification, object: nil)

        // Then the closed screen doesn't refresh
        #expect(PhotoAPI.shared.latestCallCount == before)
    }
}
```

The suite is `.serialized` because the stand-in `PhotoAPI` and the notification are shared by
every test in the process.

Ran on the iOS Simulator (Swift 6 mode): 4 tests, all passed.
:::

::: What I'd ask next
- *"Where would you put the cache, and what's its limit?"* — In the loader, an `NSCache` with a
  `totalCostLimit` in bytes; it also evicts under memory pressure.
- *"Why not just check `cell.url == url` before setting the image?"* — Works for correctness, but
  the download still runs and wastes data; cancellation fixes both.
- *"How would you stop two refreshes overlapping?"* — Keep a counter: bump it on each refresh,
  capture it in the callback, and ignore a reply whose number isn't the latest. Or skip a refresh
  while one is running.
- *"How would you prove the leak is gone in the app?"* — Open and close the feed, then check the
  Memory Graph debugger or Instruments' Leaks; the test above is the automated version.
- *"Two rows show the same URL. What happens?"* — Two downloads; dedupe in-flight requests in the
  loader (see chapter 05's follow-ups).
:::
