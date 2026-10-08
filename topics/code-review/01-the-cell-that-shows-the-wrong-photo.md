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
