---
title: 04 · The photo from another row
summary: A modern UIKit product list — diffable data source, cell registrations, list content configurations — with photos loaded async from a local package. It doesn't build, it crashes on launch, rows show other products' photos after a fast scroll, every photo is downloaded three times and memory triples. Fix it, then build a real image loader step by step, the way the interviewer escalates: share in-flight downloads, then cap the memory. Test it by counting downloads.
minutes: 60
group: Rounds
sources:
- Revolut · Android and iOS loop — sequential tasks, each stressing the last design: cache, download, thread safety, tests | https://ophyai.com/blog/company-guides/revolut-android-ios-interview
- Race Condition · Live-coding exercises — image caching as the hidden requirement | https://racecondition.software/blog/live-challenges/
- Apple · Actor — actor isolation; state can change across every await (reentrancy) | https://developer.apple.com/documentation/swift/actor
- Apple · UICollectionView.CellRegistration — cells configured from an item identifier | https://developer.apple.com/documentation/uikit/uicollectionview/cellregistration
- Apple · byPreparingThumbnail(ofSize:) — decode a photo straight to the size you draw it | https://developer.apple.com/documentation/uikit/uiimage/preparingthumbnail(of:)
- Apple · UIContentUnavailableConfiguration — loading, empty and error states in UIKit | https://developer.apple.com/documentation/uikit/uicontentunavailableconfiguration
---

*Shape: D · Requirements that keep coming, inside a fix-then-extend round — 60 minutes, your Xcode, screen
shared, no AI assistant · Reported: Revolut's loop (tasks that build on each other: cache, download, thread
safety, tests), and image caching as the hidden requirement that live-coding reports keep mentioning ·
Verified: Xcode 27.1, iOS 26 target, Swift 6 language mode with main-actor default isolation and Approachable
Concurrency. The starter fails with the build errors below. On the iPhone 17 simulator, every runtime bug in
the key was reproduced: the launch crash (3 of 5 launches, crash reports quoted), the wrong photos after a fast
scroll (screenshot), the download counts (from the package's own log), and memory with `footprint`. The
fix, step 1 and step 2 each build with no warnings. The five tests pass, and the two de-duplication tests fail
when the in-flight check is removed.*

**How the hour runs**

| Time | The interviewer says | You're scored on |
|---|---|---|
| 0:00–0:10 | "Get it building. Then get it to stop crashing." | Reading isolation errors; reading a crash report, not guessing |
| 0:10–0:30 | "Scroll it hard. What's wrong? Fix what matters." | Cell reuse, ownership of async work, memory, injection |
| 0:30–0:40 | "We download the same photo many times. Fix that." | Actor reentrancy, sharing a `Task` |
| 0:40–0:50 | "Now memory has to stay bounded." | The question you ask first: count or bytes? LRU |
| 0:50–1:00 | "Prove it with tests." | A fake that counts calls, concurrency in tests |

> "It's a product list for a shoe shop. The products and photos come from a local package that pretends
> to be the network, and it logs every download. QA says it crashes sometimes and shows the wrong
> photos. Get it running, then tell me what you'd change. I'll add requirements as we go."

The project is in `LiveCodingLab/Round04-ProductImages`. It's modern UIKit: a `UICollectionView` with
a compositional list layout, `UICollectionViewDiffableDataSource`, `CellRegistration`,
`UIListContentConfiguration`, async/await. The bugs are the ones that survive in modern code.

```swift
// ProductCatalog/Sources/ProductCatalog/ProductCatalog.swift — a package: no default isolation
public struct Product: Identifiable, Sendable {
    public let id: Int
    public let name: String
    public let price: Decimal
    public let imageURL: URL
    // public init(…)
}

public struct ProductService: Sendable {
    public init() {}

    /// 20 shoe models in three colours each. The colours of a model share one photo.
    public func fetchProducts() async throws -> [Product] { ... }   // 500 ms, 60 products
}

public final class ImageService: Sendable {
    public init() {}

    private let downloads = Atomic(0)
    private let logger = Logger(subsystem: "ProductCatalog", category: "images")

    /// Downloads the full-size product photo: 1200 × 1200 px.
    public func imageData(for url: URL) async throws -> Data {
        let number = downloads.add(1, ordering: .relaxed).newValue
        logger.notice("download #\(number) \(url.lastPathComponent, privacy: .public)")
        let model = Int(url.deletingPathExtension().lastPathComponent) ?? 0
        // A real CDN: every third photo isn't in the edge cache yet, and takes 2.5 s.
        try await Task.sleep(for: model.isMultiple(of: 3) ? .milliseconds(2500) : .milliseconds(300))
        return Self.photo(of: model)      // a PNG with the model number on it: "07"
    }
}
```

```swift
// ProductImages/ProductImages/ImageLoader.swift — the target's default isolation is MainActor
import ProductCatalog
import UIKit

enum ImageLoaderError: Error {
    case undecodable
}

/// Downloads product images and keeps them in memory, so scrolling back is instant.
nonisolated final class ImageLoader: @unchecked Sendable {
    private var cache: [URL: UIImage] = [:]
    private let service = ImageService()

    func image(for url: URL) async throws -> UIImage {
        if let cached = cache[url] {
            return cached
        }
        let data = try await service.imageData(for: url)
        // Decode off the main thread, and cache it while we're there.
        return try await Task.detached(priority: .userInitiated) {
            guard let image = UIImage(data: data) else { throw ImageLoaderError.undecodable }
            self.cache[url] = image
            return image
        }.value
    }
}
```

```swift
// ProductImages/ProductImages/ProductsViewController.swift — the root of a UINavigationController
import ProductCatalog
import UIKit

final class ProductsViewController: UIViewController {
    private enum Section {
        case main
    }

    private let productService = ProductService()
    private let imageLoader = ImageLoader()
    private var dataSource: UICollectionViewDiffableDataSource<Section, Product>!
    private lazy var collectionView = UICollectionView(
        frame: view.bounds,
        collectionViewLayout: UICollectionViewCompositionalLayout.list(using: .init(appearance: .plain))
    )

    override func viewDidLoad() {
        super.viewDidLoad()
        title = "Products"
        collectionView.autoresizingMask = [.flexibleWidth, .flexibleHeight]
        view.addSubview(collectionView)
        configureDataSource()
        Task { await loadProducts() }
    }

    private func configureDataSource() {
        let registration = UICollectionView.CellRegistration<UICollectionViewListCell, Product> { [imageLoader] cell, _, product in
            var content = UIListContentConfiguration.subtitleCell()
            content.text = product.name
            content.secondaryText = product.price.formatted(.currency(code: "EUR"))
            content.image = UIImage(systemName: "photo")
            content.imageProperties.maximumSize = CGSize(width: 60, height: 60)
            content.imageProperties.reservedLayoutSize = CGSize(width: 60, height: 60)
            content.imageProperties.cornerRadius = 8
            cell.contentConfiguration = content

            Task {
                guard let image = try? await imageLoader.image(for: product.imageURL),
                      var loaded = cell.contentConfiguration as? UIListContentConfiguration else { return }
                loaded.image = image
                cell.contentConfiguration = loaded
            }
        }
        dataSource = UICollectionViewDiffableDataSource(collectionView: collectionView) { collectionView, indexPath, product in
            collectionView.dequeueConfiguredReusableCell(using: registration, for: indexPath, item: product)
        }
    }

    private func loadProducts() async {
        let products = (try? await productService.fetchProducts()) ?? []
        var snapshot = NSDiffableDataSourceSnapshot<Section, Product>()
        snapshot.appendSections([.main])
        snapshot.appendItems(products)
        await dataSource.apply(snapshot, animatingDifferences: false)
    }
}
```

## Part 1 — make it run, then make it right

::: A hint, if you're stuck
The two build errors are about the same two words: `Hashable` and isolation. For the first, ask what
the diffable data source really needs to identify a row. For the second, ask where `Section` lives by
default in this target. Once it builds, it will probably crash, so read the crash report's thread before
you touch anything. Then scroll hard, keep the console filtered on `ProductCatalog`, and count the downloads.
:::

::: The key — what I expect a senior to find
In the order you'd hit them: build, run, scroll, read.

**It doesn't build**

1. **`generic class 'UICollectionViewDiffableDataSource' requires that 'Product' conform to 'Hashable'`.**
   The quick fix is to add `Hashable` to `Product` in the package. It compiles, and it's the wrong
   identity: a synthesized hash covers *every* field, so a price change makes the item a new row. The
   diffable data source deletes the old cell and inserts a new one, instead of reconfiguring it. Use
   `Product.ID` as the item identifier and keep the products in a dictionary. Identity stays stable, and
   `reconfigureItems` becomes possible later.
2. **`main actor-isolated conformance of 'ProductsViewController.Section' to 'Hashable' cannot satisfy
   conformance requirement for a 'Sendable' type parameter 'SectionIdentifierType'`.** This one is new in
   Swift 6.2. With main-actor default isolation, the nested `enum Section` is main-actor-isolated, so its
   synthesized `Hashable` conformance is isolated too. The data source needs a conformance it can use
   from any thread. Fix: `private nonisolated enum Section`. Value types used as identifiers, keys
   or DTOs in a main-actor target usually want `nonisolated`.

**It runs — and crashes**

3. **It crashed on 3 of 5 launches,** less than a second in. All the crash reports point to the same frame:
   `EXC_BAD_ACCESS` (or an `unrecognized selector` abort) in `Dictionary.subscript.setter` ←
   `closure #1 in ImageLoader.image(for:)`, `ImageLoader.swift:21`, on
   `com.apple.root.user-initiated-qos.cooperative`. That's `self.cache[url] = image` inside
   `Task.detached`. The three colours of a model ask for the same photo at the same moment, so three
   detached tasks write to one dictionary at once. `@unchecked Sendable` didn't make this safe. It only
   stopped the compiler from saying so. Fix: make `ImageLoader` an `actor`, so only the actor touches the
   cache. Then decode in a `@concurrent` function, so decoding doesn't block the actor.

**It runs — now scroll it hard**

4. **After a fast fling, rows show another product's photo:** "Model 19 · Black" with a 09 on it,
   "Model 19 · Sand" with 03, "Model 20 · Olive" with 06. It stays that way. A cell starts a load, gets
   reused for another row, and the old load finishes *after* the new one. Every third photo takes 2.5 s,
   so that happens all the time. The completion writes into whatever the cell shows now. Nobody owns the
   `Task`, so nobody cancels it. Fix: the cell owns its load, a `ProductCell` subclass with an
   `imageTask` that `prepareForReuse` cancels. Check `Task.isCancelled` before you touch the cell.
5. **Every photo is downloaded three times.** On the first screen, the log shows
   `download #1 1.png`, `#2 1.png`, `#3 1.png`, `#4 2.png`, … and scrolling the whole list made 57 downloads
   for 20 photos. The cache only helps *after* a download finishes. Three colours that ask at the same
   time all miss it. Making the loader an actor doesn't change that, and that's Part 2.
6. **Memory: 67 MB on the first screen, 207 MB after scrolling the list once** (`footprint`, simulator).
   Every photo is kept as a full 1200 × 1200 bitmap (about 5.8 MB decoded) to draw it at 60 × 60 points.
   Decode straight to a thumbnail at the size on screen, 180 × 180 px at 3x, with
   `byPreparingThumbnail(ofSize:)`. After that fix, the same scroll ends at 21 MB. The cache still grows
   with every photo, though, and Part 2 bounds it.

**Read the code**

7. **The loader and the service are built inside their users.** `ImageLoader()` in the controller,
   `ImageService()` in the loader. Nothing can be tested without the real 2.5 s CDN. Add
   `ImageDownloading` and `ProductFetching` protocols to the package, inject them, and build the graph in
   the scene delegate. You need this for Part 3.
8. **No loading, error or empty state.** `(try? …) ?? []` turns "offline" into an empty white screen. UIKit
   has `contentUnavailableConfiguration` (iOS 17) with `.loading()` and `.empty()`. Drive it from a
   `State` and add a Try again button.
9. **Said, not coded:**
   - `URLSession` has its own `URLCache` for the *bytes*. Ours is for *decoded* images, which is what
     costs memory and CPU. Say which layer does what.
   - Show the error in plain words, not `NSURLErrorDomain error -1009`.
   - Prefetch with `UICollectionViewDataSourcePrefetching` once the loader de-duplicates (step 1), so a
     prefetch and a cell share one download.
   - The photo needs an accessibility label, or VoiceOver says nothing for it.

What sinks this part: `nonisolated(unsafe)`, a lock, or a serial `DispatchQueue` around the dictionary
when the codebase already speaks actors. Fixing 4 by comparing URLs (two colours share a URL, so the check
passes and the bug stays). Calling `reloadData()` when an image arrives. Leaving 7 for later.
:::

::: The idea behind it
Two ideas carry this round. **Async work needs an owner.** A `Task` started in a cell registration
belongs to nobody, so it can't be cancelled, and it writes into whatever the cell shows when it finishes.
Give it to the cell, and reuse cancels it. **An actor protects state, not logic.** Making the loader an actor
stops the crash, because only one task touches the dictionary at a time. It doesn't stop three downloads of
one photo: between `cache[url]` and the `await`, other calls run. That's reentrancy, and step 1 is about it.

What "modern" means in this round:

| Use | Instead of |
|---|---|
| `Product.ID` as the item identifier, data in a dictionary | the whole model as `Hashable` |
| `nonisolated enum Section` in a main-actor target | fighting the isolated-conformance error with casts |
| an `actor` that owns the cache | `@unchecked Sendable` + a dictionary + `Task.detached` |
| `@concurrent` for decoding | decoding on the actor (or on the main thread) |
| `byPreparingThumbnail(ofSize:)` | keeping the 1200 px original for a 60 pt cell |
| `contentUnavailableConfiguration` | a hand-made empty view, or nothing |
| a cell that owns its `Task` and cancels it on reuse | a fire-and-forget `Task` in the registration |
:::

::: The fix
The package gains two protocols: `ProductService` conforms to `ProductFetching`, and `ImageService` to
`ImageDownloading`.

```swift
public protocol ProductFetching: Sendable {
    func fetchProducts() async throws -> [Product]
}

public protocol ImageDownloading: Sendable {
    func imageData(for url: URL) async throws -> Data
}
```

The loader becomes an actor that decodes thumbnails off the actor:

```swift
import ProductCatalog
import UIKit

enum ImageLoaderError: Error {
    case undecodable
}

/// Downloads product images, shrinks them to thumbnails and keeps them in memory.
actor ImageLoader {
    init(downloader: any ImageDownloading, thumbnailSize: CGSize) {
        self.downloader = downloader
        self.thumbnailSize = thumbnailSize
    }

    func image(for url: URL) async throws -> UIImage {
        if let cached = cache[url] {
            return cached
        }
        let data = try await downloader.imageData(for: url)
        let image = try await Self.thumbnail(from: data, size: thumbnailSize)
        cache[url] = image                      // only the actor touches the cache
        return image
    }

    private let downloader: any ImageDownloading
    private let thumbnailSize: CGSize
    private var cache: [URL: UIImage] = [:]

    /// Decodes straight to the size on screen: 180 × 180 px instead of a 1200 × 1200 bitmap.
    /// `@concurrent` keeps this work off the actor, so other callers aren't blocked behind it.
    @concurrent
    private static func thumbnail(from data: Data, size: CGSize) async throws -> UIImage {
        guard let image = UIImage(data: data),
              let thumbnail = await image.byPreparingThumbnail(ofSize: size) else {
            throw ImageLoaderError.undecodable
        }
        return thumbnail
    }
}
```

The controller: injected, identified by ID, a cell that owns its load, and real states:

```swift
import ProductCatalog
import UIKit

final class ProductsViewController: UIViewController {
    private nonisolated enum Section {
        case main
    }

    private enum State {
        case loading
        case loaded
        case failed(String)
    }

    init(productService: any ProductFetching, imageLoader: ImageLoader) {
        self.productService = productService
        self.imageLoader = imageLoader
        super.init(nibName: nil, bundle: nil)
    }

    required init?(coder: NSCoder) {
        fatalError("init(coder:) is not supported")
    }

    override func viewDidLoad() {
        super.viewDidLoad()
        title = "Products"
        collectionView.autoresizingMask = [.flexibleWidth, .flexibleHeight]
        view.addSubview(collectionView)
        configureDataSource()
        Task { await loadProducts() }
    }

    override func updateContentUnavailableConfiguration(using state: UIContentUnavailableConfigurationState) {
        switch self.state {
        case .loading:
            contentUnavailableConfiguration = UIContentUnavailableConfiguration.loading()
        case .failed(let message):
            var configuration = UIContentUnavailableConfiguration.empty()
            configuration.image = UIImage(systemName: "wifi.exclamationmark")
            configuration.text = "Couldn't load products"
            configuration.secondaryText = message
            configuration.button = .borderedProminent()
            configuration.button.title = "Try again"
            configuration.buttonProperties.primaryAction = UIAction { [weak self] _ in
                Task { await self?.loadProducts() }
            }
            contentUnavailableConfiguration = configuration
        case .loaded where products.isEmpty:
            var configuration = UIContentUnavailableConfiguration.empty()
            configuration.text = "No products yet"
            contentUnavailableConfiguration = configuration
        case .loaded:
            contentUnavailableConfiguration = nil
        }
    }

    private let productService: any ProductFetching
    private let imageLoader: ImageLoader
    private var products: [Product.ID: Product] = [:]
    private var dataSource: UICollectionViewDiffableDataSource<Section, Product.ID>!
    private var state: State = .loading {
        didSet { setNeedsUpdateContentUnavailableConfiguration() }
    }
    private lazy var collectionView = UICollectionView(
        frame: view.bounds,
        collectionViewLayout: UICollectionViewCompositionalLayout.list(using: .init(appearance: .plain))
    )

    private func configureDataSource() {
        let registration = UICollectionView.CellRegistration<ProductCell, Product.ID> { [weak self] cell, _, id in
            guard let self, let product = products[id] else { return }
            var content = UIListContentConfiguration.subtitleCell()
            content.text = product.name
            content.secondaryText = product.price.formatted(.currency(code: "EUR"))
            content.image = UIImage(systemName: "photo")
            content.imageProperties.maximumSize = CGSize(width: 60, height: 60)
            content.imageProperties.reservedLayoutSize = CGSize(width: 60, height: 60)
            content.imageProperties.cornerRadius = 8
            cell.contentConfiguration = content

            let placeholder = content
            cell.imageTask = Task { [imageLoader] in
                guard let image = try? await imageLoader.image(for: product.imageURL),
                      !Task.isCancelled else { return }   // the cell was reused while we waited
                var loaded = placeholder
                loaded.image = image
                cell.contentConfiguration = loaded
            }
        }
        dataSource = UICollectionViewDiffableDataSource(collectionView: collectionView) { collectionView, indexPath, id in
            collectionView.dequeueConfiguredReusableCell(using: registration, for: indexPath, item: id)
        }
    }

    private func loadProducts() async {
        state = .loading
        do {
            let products = try await productService.fetchProducts()
            self.products = Dictionary(uniqueKeysWithValues: products.map { ($0.id, $0) })
            var snapshot = NSDiffableDataSourceSnapshot<Section, Product.ID>()
            snapshot.appendSections([.main])
            snapshot.appendItems(products.map(\.id))
            await dataSource.apply(snapshot, animatingDifferences: false)
            state = .loaded
        } catch {
            state = .failed(error.localizedDescription)
        }
    }
}

/// A list cell that owns its image load, so reuse cancels it.
final class ProductCell: UICollectionViewListCell {
    var imageTask: Task<Void, Never>? {
        willSet { imageTask?.cancel() }
    }

    override func prepareForReuse() {
        super.prepareForReuse()
        imageTask = nil
    }
}
```

The graph is built once, in the scene delegate:

```swift
let imageLoader = ImageLoader(downloader: ImageService(),
                              thumbnailSize: CGSize(width: 180, height: 180))   // 60 pt at 3x
let products = ProductsViewController(productService: ProductService(), imageLoader: imageLoader)
window.rootViewController = UINavigationController(rootViewController: products)
```

`!Task.isCancelled` is race-free here because both `prepareForReuse` and the task's resumption run on the
main actor. Once the cell is reused, the old task can't get past the guard. With this fix, the same
fast fling showed the right photo on every row, and memory after a full scroll was 21 MB. The log still
showed three downloads per photo (60 for 20).
:::

## Part 2 — two more requirements

> "Better. Step one: the log still shows each photo downloaded three times. One download per photo,
> however many cells ask for it at the same time."

::: A hint, if you're stuck
You already have an actor. Read `image(for:)` and mark every `await`. What can another call do while
this one is suspended at the download? What could it find in the actor's state, if you put something
there *before* that `await`?
:::

::: The key — what I expect a senior to find
**Actor reentrancy, explained out loud.** An actor runs one piece of code at a time, but it gives up the
actor at every `await`. Call A checks the cache, misses, and suspends on the download. Call B runs on the
actor, checks the cache, misses too, and starts a second download. The actor protected the dictionary.
It never promised that the check and the use happen together.

The fix is to make "a download is running" part of the actor's state. Keep a dictionary of in-flight
`Task`s, store the task **before** the first `await`, and let later callers await the same task.

The questions worth asking:

- **Does the first caller's cancellation cancel the download?** No. The photo is still wanted by the other
  cells, and it's cheap to cache. `await task.value` doesn't propagate cancellation into an unstructured
  task, so a caller that leaves just stops waiting. The download finishes and is cached for the next row.
  (Cancelling it once *nobody* is waiting needs a waiter count. That's a good follow-up.)
- **What if it fails?** Everyone waiting gets the error, nothing is cached, and the next request tries
  again. Remove the in-flight entry on every path. `defer` does that.
:::

::: The fix
Step one changes only `image(for:)` and adds one property:

```swift
func image(for url: URL) async throws -> UIImage {
    if let cached = cache[url] {
        return cached
    }
    if let running = inFlight[url] {
        return try await running.value      // join the download that's already running
    }
    let download = Task { [downloader, thumbnailSize] in
        let data = try await downloader.imageData(for: url)
        return try await Self.thumbnail(from: data, size: thumbnailSize)
    }
    inFlight[url] = download                // registered before the first await
    defer { inFlight[url] = nil }
    let image = try await download.value
    cache[url] = image
    return image
}

private var inFlight: [URL: Task<UIImage, any Error>] = [:]
```

On the simulator, the first screen now logs `download #1 1.png`, `#2 2.png`, `#3 3.png`, and a fast fling
through the whole list logged 18 downloads for the 18 photos it passed, each once.
:::

> "Good. Step two: memory has to stay bounded. This list will have thousands of products."

::: A hint, if you're stuck
"Bounded" by what? Ask before you write a number. Then ask what "evict" picks.
:::

::: The key — what I expect a senior to find
**The questions to ask first** — each one changes the code:

- **A limit on the number of images, or on bytes?** Bytes. This is the trap: a count limit means nothing when
  one image is about 130 KB and another is 5.8 MB. The answer: 20 MB of *decoded* pixels.
- **Which bytes — the file or the bitmap?** The bitmap. A small PNG becomes `bytesPerRow × height` in memory,
  and that's what the system kills apps for. Measure the `CGImage`, not the `Data`.
- **What gets evicted?** The least recently used. A hit counts as a use, so a photo that's on screen keeps
  being touched and stays.
- **An image bigger than the whole limit?** Don't cache it, and still return it.
- **Why not `NSCache`?** Say it: it has `totalCostLimit`, and it also empties itself on memory pressure.
  But its eviction order isn't documented, and you can't see what it holds, so you can't test the policy.
  Our own LRU inside the actor is 20 lines and testable. In production, I'd
  also clear it on `UIApplication.didReceiveMemoryWarningNotification`.
:::

::: The fix
The final loader. The cache keeps a cost per entry and an order of use:

```swift
import ProductCatalog
import UIKit

enum ImageLoaderError: Error {
    case undecodable
}

/// Downloads product images, shrinks them to thumbnails and keeps the most recently used
/// ones in memory, up to `costLimit` bytes of decoded pixels.
actor ImageLoader {
    init(downloader: any ImageDownloading, thumbnailSize: CGSize, costLimit: Int) {
        self.downloader = downloader
        self.thumbnailSize = thumbnailSize
        self.costLimit = costLimit
    }

    /// Bytes of decoded pixels in the cache right now.
    private(set) var totalCost = 0

    func image(for url: URL) async throws -> UIImage {
        if let cached = cachedImage(for: url) {
            return cached
        }
        if let running = inFlight[url] {
            return try await running.value      // join the download that's already running
        }
        let download = Task { [downloader, thumbnailSize] in
            let data = try await downloader.imageData(for: url)
            return try await Self.thumbnail(from: data, size: thumbnailSize)
        }
        inFlight[url] = download                // registered before the first await
        defer { inFlight[url] = nil }
        let image = try await download.value
        insert(image, for: url)
        return image
    }

    private struct Entry {
        let image: UIImage
        let cost: Int
    }

    private let downloader: any ImageDownloading
    private let thumbnailSize: CGSize
    private let costLimit: Int
    private var cache: [URL: Entry] = [:]
    private var recency: [URL] = []             // least recently used first
    private var inFlight: [URL: Task<UIImage, any Error>] = [:]

    private func cachedImage(for url: URL) -> UIImage? {
        guard let entry = cache[url] else { return nil }
        recency.removeAll { $0 == url }         // O(n): fine for a few hundred thumbnails
        recency.append(url)
        return entry.image
    }

    private func insert(_ image: UIImage, for url: URL) {
        let cost = Self.cost(of: image)
        guard cost <= costLimit else { return }  // bigger than the whole budget: don't cache it
        cache[url] = Entry(image: image, cost: cost)
        recency.append(url)
        totalCost += cost
        while totalCost > costLimit, let oldest = recency.first {
            recency.removeFirst()
            totalCost -= cache.removeValue(forKey: oldest)?.cost ?? 0
        }
    }

    /// What the image costs in memory once decoded: its bitmap, not its file size.
    private static func cost(of image: UIImage) -> Int {
        guard let cgImage = image.cgImage else { return 0 }
        return cgImage.bytesPerRow * cgImage.height
    }

    // thumbnail(from:size:): unchanged, @concurrent.
}
```

The scene delegate passes `costLimit: 20 * 1024 * 1024`. `insert` can't run twice for one URL: the
in-flight check means only the caller that started the download inserts it. If the catalogue grows to
thousands of entries, swap the `recency` array for a linked list with a dictionary of nodes, which makes
every operation O(1). Say it, but don't build it unless they ask.
:::

## Part 3 — test it

> "Prove it. Count the downloads."

::: Now write the tests
A fake downloader that counts requests per URL, can be slow, and can fail the first N requests. The counters
live in `Mutex`, so the fake is `Sendable` without `@unchecked`. It's `nonisolated` because the target's
default isolation would otherwise put it on the main actor.

```swift
import Foundation
import ProductCatalog
import Synchronization
import Testing
import UIKit
@testable import ProductImages

/// Counts downloads per URL. Answers after `delay`, and fails the first `failures` requests.
nonisolated final class FakeDownloader: ImageDownloading {
    let delay: Duration
    let failuresLeft: Mutex<Int>
    let requests = Mutex<[URL: Int]>([:])

    init(delay: Duration = .zero, failures: Int = 0) {
        self.delay = delay
        self.failuresLeft = Mutex(failures)
    }

    func imageData(for url: URL) async throws -> Data {
        requests.withLock { $0[url, default: 0] += 1 }
        try await Task.sleep(for: delay)
        let shouldFail = failuresLeft.withLock { left in
            defer { left = max(0, left - 1) }
            return left > 0
        }
        if shouldFail { throw URLError(.timedOut) }
        return Self.png
    }

    func downloads(of url: URL) -> Int {
        requests.withLock { $0[url, default: 0] }
    }

    static let png = UIGraphicsImageRenderer(size: CGSize(width: 300, height: 300)).pngData { context in
        UIColor.orange.setFill()
        context.fill(CGRect(x: 0, y: 0, width: 300, height: 300))
    }
}

struct ImageLoaderTests {
    let a = URL(string: "https://img.example.com/a.png")!
    let b = URL(string: "https://img.example.com/b.png")!
    let c = URL(string: "https://img.example.com/c.png")!
    let thumbnail = CGSize(width: 60, height: 60)

    @Test func concurrentRequestsForOneURLShareOneDownload() async throws {
        let downloader = FakeDownloader(delay: .milliseconds(100))
        let loader = ImageLoader(downloader: downloader, thumbnailSize: thumbnail, costLimit: .max)
        async let first = loader.image(for: a)
        async let second = loader.image(for: a)
        async let third = loader.image(for: a)
        _ = try await (first, second, third)
        #expect(downloader.downloads(of: a) == 1)
    }

    @Test func aCachedImageIsNotDownloadedAgain() async throws {
        let downloader = FakeDownloader()
        let loader = ImageLoader(downloader: downloader, thumbnailSize: thumbnail, costLimit: .max)
        _ = try await loader.image(for: a)
        _ = try await loader.image(for: a)
        #expect(downloader.downloads(of: a) == 1)
    }

    @Test func aFailedDownloadIsNotCachedSoTheNextRequestRetries() async throws {
        let downloader = FakeDownloader(failures: 1)
        let loader = ImageLoader(downloader: downloader, thumbnailSize: thumbnail, costLimit: .max)
        await #expect(throws: URLError.self) { try await loader.image(for: a) }
        _ = try await loader.image(for: a)
        #expect(downloader.downloads(of: a) == 2)
    }

    @Test func aCancelledCallerDoesNotCancelTheSharedDownload() async throws {
        let downloader = FakeDownloader(delay: .milliseconds(200))
        let loader = ImageLoader(downloader: downloader, thumbnailSize: thumbnail, costLimit: .max)
        let leaving = Task { try await loader.image(for: a) }       // a cell scrolled away
        let staying = Task { try await loader.image(for: a) }       // another cell, same photo
        leaving.cancel()
        _ = try await staying.value
        #expect(downloader.downloads(of: a) == 1)
    }

    @Test func theLeastRecentlyUsedImageIsEvictedOverTheLimit() async throws {
        let probe = ImageLoader(downloader: FakeDownloader(), thumbnailSize: thumbnail, costLimit: .max)
        _ = try await probe.image(for: a)
        let oneImage = await probe.totalCost                         // what one thumbnail costs

        let downloader = FakeDownloader()
        let loader = ImageLoader(downloader: downloader, thumbnailSize: thumbnail,
                                 costLimit: oneImage * 2)              // room for two
        _ = try await loader.image(for: a)
        _ = try await loader.image(for: b)
        _ = try await loader.image(for: a)                            // a is now the most recent
        _ = try await loader.image(for: c)                            // evicts b, not a
        #expect(await loader.totalCost <= oneImage * 2)

        _ = try await loader.image(for: a)
        _ = try await loader.image(for: b)
        #expect(downloader.downloads(of: a) == 1)
        #expect(downloader.downloads(of: b) == 2)
    }
}
```

I removed the `if let running = inFlight[url]` check and ran the tests again. Two of them failed:
`concurrentRequestsForOneURLShareOneDownload` and `aCancelledCallerDoesNotCancelTheSharedDownload`. So the
tests check reentrancy, not just the happy path.

The probe measures one thumbnail's real cost instead of hard-coding `bytesPerRow`, which depends on the
renderer's scale and row alignment. The test doesn't break if that changes.
:::

::: What I'd ask next
- **"Now cancel a download when nobody wants it any more."** Count waiters per URL in the actor. Each caller
  wraps its `await` in `withTaskCancellationHandler`, and its `onCancel` asks the actor to decrement. At zero,
  cancel the task and remove it. Mind the case where a new caller joins while the count is at zero.
- **"Keep images across launches."** Add a disk layer under the memory one, keyed by a hash of the URL, in
  `Caches/`, with a size limit and an eviction pass in the background. Or let `URLCache` keep the bytes and
  decode again. Say what you trade: disk space against CPU for each decode.
- **"Three thumbnail sizes now."** The cache key becomes URL + pixel size. In-flight entries are keyed the
  same way, so one download can still feed several sizes: dedupe on the download, cache per size.
- **"Why not SwiftUI's AsyncImage?"** It gives you no cache of decoded images that you control, no
  de-duplication and no size limit. It's fine for one hero image, not for a list of thumbnails.
- **"The memory warning arrives."** Empty the cache, but keep the in-flight tasks. They're about to be
  shown. Then explain why one loader for the whole app is right here, and one per screen isn't.
:::
