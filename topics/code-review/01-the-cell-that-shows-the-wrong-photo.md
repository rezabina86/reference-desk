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
(fintech manager rounds) · UIKit — the fix typechecks against the iOS SDK (iOS 18 target) in Swift 6 mode; behaviour checked by hand*

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
- How much memory does a decoded 12-megapixel photo take?
:::

::: The key — what I expect a senior to find
1. **Wrong photo in a row (the reported bug).** Cells are reused. A slow download for row 3
   finishes after the cell has been reused for row 40 and writes row 3's image into it. Nothing
   cancels the old request or checks that the cell still wants that URL.
2. **No `prepareForReuse`.** The old image stays visible until the new one arrives.
3. **The timer leaks the screen.** A target-based `Timer` holds its target strongly, and the run
   loop holds the timer. The controller can never deallocate, so `deinit` — where the only
   `invalidate()` lives — never runs. Classic circular fix that can't fire.
4. **The observer leaks it too.** The block captures `self` strongly, and the returned token is
   thrown away, so it can never be removed. NotificationCenter keeps the block — and the
   controller — alive for the life of the app.
5. **Each leaked controller keeps refreshing.** Open and close the feed five times and five timers
   fire every 30 seconds, each doing network work for an invisible screen. That's the memory growth.
6. **`refresh` updates UI from an unknown thread.** Nothing says `PhotoAPI` calls back on main.
7. **`refresh` captures `self` strongly** — milder than 3–4, but it extends the lifetime for every
   request.
8. **Images decoded at full size.** A 12-megapixel photo becomes ~48 MB of bitmap to show in a
   100-point row. Downsample to the display size, in pixels (points × screen scale).
9. **No caching.** Scrolling back up downloads every image again.
10. **Errors ignored** — no placeholder, no retry.
11. **`as!` on dequeue** — acceptable to many teams, but say you know it crashes on a
    misconfigured identifier.
12. **Singletons** — `URLSession.shared`, `PhotoAPI.shared` — nothing here is testable.
13. **The cell does networking.** A view shouldn't know about URLs and sessions; give it an image
    or an image-loading dependency.
14. **Timer fires while off screen** — start it in `viewWillAppear`, stop it in
    `viewDidDisappear`.
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
object alive. And stop timers and observers when the screen goes away, not in `deinit`.
:::

::: The fix
```swift
final class PhotoCell: UITableViewCell {
    @IBOutlet private var photoView: UIImageView!
    private var loadTask: Task<Void, Never>?

    override func prepareForReuse() {
        super.prepareForReuse()
        loadTask?.cancel()
        photoView.image = nil
    }

    // The caller passes the size the image will be shown at (the row height and the
    // image view's fixed width). Don't read photoView.bounds here: cellForRow runs
    // before layout, so bounds are usually .zero.
    func configure(with url: URL, loader: ImageLoading, displaySize: CGSize) {
        loadTask?.cancel()
        let scale = traitCollection.displayScale
        let pixels = CGSize(width: displaySize.width * scale,
                            height: displaySize.height * scale)
        loadTask = Task { [weak self] in
            guard let image = try? await loader.image(for: url, fittingPixels: pixels),
                  !Task.isCancelled else { return }
            self?.photoView.image = image
        }
    }
}

protocol ImageLoading: Sendable {
    // Cached in an NSCache, downsampled off the main thread
    // (CGImageSource with kCGImageSourceThumbnailMaxPixelSize, or
    // byPreparingThumbnail(ofSize:)). Both take pixels, not points.
    @MainActor func image(for url: URL, fittingPixels size: CGSize) async throws -> UIImage
}
```

```swift
private var timer: Timer?
private var observer: NSObjectProtocol?

override func viewWillAppear(_ animated: Bool) {
    super.viewWillAppear(animated)
    stopRefreshing()   // a cancelled swipe-back calls viewWillAppear again without viewDidDisappear
    // Both closures are nonisolated in Swift 6, but both run on main: the timer is on the
    // main run loop and the observer uses queue: .main. assumeIsolated states that (and traps if wrong).
    timer = Timer.scheduledTimer(withTimeInterval: 30, repeats: true) { [weak self] _ in
        MainActor.assumeIsolated { self?.refresh() }
    }
    observer = NotificationCenter.default.addObserver(
        forName: UIApplication.didBecomeActiveNotification,
        object: nil, queue: .main) { [weak self] _ in
        MainActor.assumeIsolated { self?.refresh() }
    }
}

override func viewDidDisappear(_ animated: Bool) {
    super.viewDidDisappear(animated)
    stopRefreshing()
}

private func stopRefreshing() {
    timer?.invalidate()
    timer = nil
    if let observer { NotificationCenter.default.removeObserver(observer) }
    observer = nil
}
```

Why `Task` in the cell: cancellation comes for free and `self` is the main-actor cell, so the
assignment is on main by construction. The `!Task.isCancelled` check is the identity check — a
reused cell has cancelled the old task before it can write.

Why `stopRefreshing()` at the top of `viewWillAppear`: start a swipe-back and let go, and UIKit
calls `viewWillDisappear` then `viewWillAppear` again, but never `viewDidDisappear`. Without the
reset, that creates a second timer and a second observer, and the first ones are never removed.
:::

::: Now write the tests
> "Good. Now write me a few tests — one for the wrong photo, and one that proves the leak is gone."

**What I'd test, and why**

1. **A late reply for the old URL never shows.** Configure the cell for A, reuse it for B, then let
   A's photo arrive. The cell must not show A. This is the reported bug, so it goes first.
2. **Reuse clears the old photo** — no stale image while the new one loads.
3. **A load that finishes after reuse is dropped** — the cell scrolled off before its photo came back.
4. **The cell asks for pixels, not points** — at 3× scale a 100 × 80 row needs a 300 × 240 image.
   That's the downsampling bug from the review.
5. **The screen is freed after it closes.** A *weak reference* (one that doesn't keep the object
   alive) becomes `nil` only if nothing else holds the screen — so the test fails if the timer or
   observer still does.
6. **A closed screen stops refreshing, and a cancelled swipe-back keeps one observer.** One app
   wake-up must mean one refresh, not two.

I wouldn't test `Timer` or `NotificationCenter` themselves, or the image loader's cache — that has
its own tests.

**The seam.** The cell takes an `ImageLoading` in `configure`, so the test passes a *fake*: a
stand-in that records what it was asked and holds each load until the test says which photo
arrives, and when. That's how the test makes A arrive *after* B was asked for — every run, no
timing. The outlet is private, so the test connects it by key, the way a storyboard does. The
chapter shows the controller fix as a fragment; for the test I put it in a minimal
`FeedViewController` whose `refresh()` just counts calls (`refreshCount`), so the test can see how
many refreshes one notification causes. UIKit's `beginAppearanceTransition` drives the appear and
disappear callbacks by hand.

```swift
import Testing
import UIKit

// A fake loader: it records what it was asked for, and each load waits
// until the test says which photo arrives, and when.
@MainActor
final class FakeImageLoader: ImageLoading {
    private(set) var requestedPixels: [CGSize] = []
    private var waiting: [URL: CheckedContinuation<UIImage, any Error>] = [:]

    func image(for url: URL, fittingPixels size: CGSize) async throws -> UIImage {
        requestedPixels.append(size)
        return try await withCheckedThrowingContinuation { waiting[url] = $0 }
    }

    func finish(_ url: URL, with image: UIImage) {
        waiting.removeValue(forKey: url)?.resume(returning: image)
    }
}

extension PhotoCell {
    // A storyboard connects outlets by key. The test does the same.
    static func make() -> PhotoCell {
        let cell = PhotoCell(style: .default, reuseIdentifier: "PhotoCell")
        cell.setValue(UIImageView(), forKey: "photoView")
        return cell
    }

    var shownImage: UIImage? { (value(forKey: "photoView") as? UIImageView)?.image }
}

/// Lets the main actor run what is queued, so a finished load can reach the cell. No clock.
func settle() async {
    for _ in 0..<10 { await Task.yield() }
}

@Suite(.timeLimit(.minutes(1)))
@MainActor
struct PhotoCellTests {
    let urlA = URL(string: "https://example.com/a.jpg")!
    let urlB = URL(string: "https://example.com/b.jpg")!
    let photoA = UIImage(systemName: "a.circle")!
    let photoB = UIImage(systemName: "b.circle")!
    let rowSize = CGSize(width: 100, height: 80)

    @Test func lateReplyForTheOldURLNeverShows() async {
        // Given a cell configured for A, then reused for B before A arrived
        let loader = FakeImageLoader()
        let cell = PhotoCell.make()
        cell.configure(with: urlA, loader: loader, displaySize: rowSize)
        cell.configure(with: urlB, loader: loader, displaySize: rowSize)
        await settle()                      // both loads are now in flight

        // When A's photo arrives late
        loader.finish(urlA, with: photoA)
        await settle()

        // Then the cell shows nothing yet, and B's photo once it arrives
        #expect(cell.shownImage == nil)
        loader.finish(urlB, with: photoB)
        await settle()
        #expect(cell.shownImage === photoB)
    }

    @Test func reuseClearsTheOldPhoto() async {
        let loader = FakeImageLoader()
        let cell = PhotoCell.make()
        cell.configure(with: urlA, loader: loader, displaySize: rowSize)
        await settle()
        loader.finish(urlA, with: photoA)
        await settle()
        #expect(cell.shownImage === photoA)

        cell.prepareForReuse()

        #expect(cell.shownImage == nil)
    }

    @Test func loadThatFinishesAfterReuseIsDropped() async {
        let loader = FakeImageLoader()
        let cell = PhotoCell.make()
        cell.configure(with: urlA, loader: loader, displaySize: rowSize)
        await settle()

        cell.prepareForReuse()              // scrolled off before the photo came back
        loader.finish(urlA, with: photoA)
        await settle()

        #expect(cell.shownImage == nil)
    }

    @Test func asksForPixelsNotPoints() async {
        let loader = FakeImageLoader()
        let cell = PhotoCell.make()
        cell.traitOverrides.displayScale = 3

        cell.configure(with: urlA, loader: loader, displaySize: rowSize)
        await settle()

        #expect(loader.requestedPixels == [CGSize(width: 300, height: 240)])
        loader.finish(urlA, with: photoA)
    }
}

extension UIViewController {
    // UIKit's own way to drive the appear and disappear callbacks by hand.
    func appear() { beginAppearanceTransition(true, animated: false); endAppearanceTransition() }
    func disappear() { beginAppearanceTransition(false, animated: false); endAppearanceTransition() }
}

@MainActor
struct FeedViewControllerTests {
    @Test func screenIsReleasedAfterItCloses() {
        weak var weakScreen: FeedViewController?
        autoreleasepool {
            let screen = FeedViewController()
            screen.appear()                    // starts the timer and the observer
            screen.disappear()
            weakScreen = screen
        }
        #expect(weakScreen == nil)
    }

    @Test func closedScreenStopsRefreshing() {
        let screen = FeedViewController()
        screen.appear()
        screen.disappear()

        NotificationCenter.default.post(name: UIApplication.didBecomeActiveNotification, object: nil)

        #expect(screen.refreshCount == 0)
    }

    @Test func cancelledSwipeBackKeepsOneObserver() {
        let screen = FeedViewController()
        screen.appear()
        // A swipe-back the user let go of: will-disappear, then will-appear again.
        screen.beginAppearanceTransition(false, animated: true)
        screen.beginAppearanceTransition(true, animated: true)
        screen.endAppearanceTransition()

        NotificationCenter.default.post(name: UIApplication.didBecomeActiveNotification, object: nil)

        #expect(screen.refreshCount == 1)
        screen.disappear()
    }
}
```

Ran on the iOS Simulator (iOS 18.5, Swift 6 mode): 7 tests, all passed.
:::

::: What I'd ask next
- *"Where would you put the cache, and what's its limit?"* — In the loader, an `NSCache` with a
  `totalCostLimit` in bytes; it also evicts under memory pressure.
- *"Why not just check `cell.url == url` before setting the image?"* — Works for correctness, but
  the download still runs and wastes data; cancellation fixes both.
- *"How would you prove the leak is gone?"* — Open and close the feed in the Memory Graph
  debugger or Instruments' Leaks; or a test that holds a `weak` reference and asserts it's `nil`
  after the screen is dismissed.
- *"Two rows show the same URL. What happens?"* — Two downloads; dedupe in-flight requests in the
  loader (see chapter 05).
:::
