---
title: 01 · Image loading and caching library
summary: "Design an image loading library, something like Kingfisher or Nuke."
minutes: 50
sources:
- weeeBox · Mobile system design exercise, Image library | https://github.com/weeeBox/mobile-system-design/blob/master/exercises/image-library.md
- WWDC18 · Image and graphics best practices | https://developer.apple.com/videos/play/wwdc2018/219/
- WWDC21 · Make blazing fast lists and collection views | https://developer.apple.com/videos/play/wwdc2021/10252/
- WWDC19 · Advances in networking, part 1 (Low Data Mode) | https://developer.apple.com/videos/play/wwdc2019/712/
- Apple · CGImageSourceCreateThumbnailAtIndex | https://developer.apple.com/documentation/imageio/cgimagesourcecreatethumbnailatindex(_:_:_:)
- Apple · UIImage.preparingForDisplay() | https://developer.apple.com/documentation/uikit/uiimage/3750834-preparingfordisplay
- Apple · NSCache | https://developer.apple.com/documentation/foundation/nscache
- Apple · allowsConstrainedNetworkAccess | https://developer.apple.com/documentation/foundation/urlsessionconfiguration/allowsconstrainednetworkaccess
- Apple · UICollectionViewDataSourcePrefetching | https://developer.apple.com/documentation/uikit/uicollectionviewdatasourceprefetching
- SE-0461 · Run nonisolated async functions on the caller's actor by default | https://github.com/swiftlang/swift-evolution/blob/main/proposals/0461-async-function-isolation.md
- Nuke · request coalescing and the pipeline | https://github.com/kean/Nuke
---

*A recurring senior mobile prompt. The answer below stays small on purpose: seven parts, one shared download per picture, one idea per part.*

> **Interviewer:** "We show a lot of images — feeds, avatars, a photo grid. Design the image loading library we'd build for that. Something like Kingfisher or Nuke."

## Run it as a round, not as reading

Set a timer. Sketch. Talk the whole time. Open a section only when its slot is over.

| Clock | Phase | What you do |
|---|---|---|
| 0:00–0:02 | The prompt | Repeat it back in one sentence |
| 0:02–0:07 | Clarify | Ask yours, then read section 1 |
| 0:07–0:12 | Scope | Out of scope first, then features, then what must feel good |
| 0:12–0:24 | High level | The idea · the parts · the sketch · each part · two flows |
| 0:24–0:40 | Deep dives | The interviewer picks one of sections 9–11 |
| 0:40–0:45 | Recap | Follow-ups, then the 60-second summary |

## What this question is really testing

- **The cost of a decoded image:** width × height × 4 bytes, whatever the file size.
- **One download for two rows** that want the same picture.
- **Cancelling on cell reuse**, without killing a download another row still needs.
- **Shrinking off the main thread**, so decoding doesn't stutter scrolling.
- **Knowing when to stop.** `AsyncImage`, `URLCache` and `NSCache` are fine for a small app. Say when.

**Traps:** designing the CDN; a cache with no limit; forgetting cancellation; decoding on the main thread; calling prefetching a guarantee; saying "the app's memory stays flat"; listing Kingfisher's features instead of designing.

::: Words used in this chapter
- **Library** — reusable code the whole app calls. Here, the code that loads every picture.
- **Pixel** — one dot on the screen. A picture's pixel size is how many dots wide and tall it is.
- **Decode** — unpack a compressed file (JPEG, HEIC) into pixels the screen can draw. Unpacked, it's much bigger.
- **Downsample** — decode straight to a smaller size, so the big version never exists.
- **Memory vs disk** — memory is fast, small and emptied when the app quits. Disk is slower, bigger and survives.
- **Cache** — a kept copy, so the next time is fast. *Eviction* throws old entries out when it's full.
- **CDN** — servers that keep copies of files close to users. Ours can also resize a picture before sending it.
- **Main thread** — the one lane that draws the screen. Slow work there freezes scrolling.
- **Actor** — a Swift object that runs one piece of its code at a time, so its data is never changed twice at once.
- **Protocol** — a promise of what a part can do, without saying how. A fake can keep the same promise in tests.
- **Prefetch** — fetch pictures just before they come into view.
- **Deduplicate** — when two callers want the same thing, do the work once and give both the result.
:::

::: 1 · The interviewer answers your clarifying questions
**"One app, or an SDK other teams adopt?"** → *One app, but shaped so it could become a package.*

**"Where do images come from?"** → *The network. A few bundled assets, but skip those.*

**"Who uses it?"** → *UIKit image views and SwiftUI. Sometimes code that wants an image to share.*

**"Heaviest screen?"** → *A thumbnail grid you can fling through, plus a full-screen detail view.*

**"Can the server resize?"** → *Yes. The CDN takes `?w=` and sends `ETag` and `Cache-Control`.*

**"Offline?"** → *Pictures the user has seen should still show.*

**"Any public images, or private ones too?"** → *Public for now. Profile photos may go private later.*

**"How big?"** → *Ten million users a day, each sees about 200 pictures. A grid shows about 30 at once.*

**"What hurts today?"** → *Stutter on older phones, and the app gets killed for using too much memory.*
:::

::: 2 · Requirements and scope — what you should have said
**Out of scope, said first:** GIFs and video, filters and editing, placeholder animations (the caller owns those), bundled and file sources, and the server beyond "a CDN with a width parameter".

**Required for the prompt**

1. Load an image by URL, at the size it will be shown, into a view or back to a caller.
2. Cache in memory, and on disk so seen pictures show offline.
3. One download per picture, even when two rows ask.
4. Cancel when a row no longer needs the picture.

**What must feel good:** smooth (no decoding or disk work on the main thread) · bounded *cache* memory (a byte limit) · no repeat download while a picture is loading or cached · a reused row only shows the picture for its current request.

**Production considerations** (say them, don't draw them): prefetching as an optimization, visible-first priority, freshness from the CDN's cache headers, metrics, HTTPS and private URLs. They're in sections 10 and 12.

**Optional follow-ups** (add only when asked):

```text
No offline need                → URLCache instead of our disk cache
Private images                 → auth in the loader, a protected folder
Another source (files, Photos) → a new data loader
GIFs, filters                  → a decoder per format, a processing step
Other teams adopt it           → a Swift package with a small public API
```

*"I'll start simple and add each of these when the requirement appears."*
:::

::: 3 · The idea, in 30 seconds — before you draw anything
> *"A view asks for a picture by URL and by the size it will show it at. One pipeline checks a memory cache with a byte limit, and if the same picture at the same size is already loading for another row, it waits for that load instead of starting a second. On a miss, it reads the bytes from a disk cache or downloads them from the CDN at a width bucket, shrinks them to the display size off the main thread, and keeps the result in memory. It's a library, so three frames of its own: the API callers touch, the core that coordinates, and the I/O that does the work."*
:::

::: 4 · What we need — the components, before the sketch
| # | Part | Type | Layer | Its one job |
|---|---|---|---|---|
| 1 | **Image view** | `setImage` · `LazyImage` | API | Shows one request in one view. |
| 2 | **Image pipeline** | `ImagePipeline` | Core | Coordinates loads, one per picture. |
| 3 | **Memory cache** | `ImageMemoryCache` | Core | Keeps pictures ready to draw. |
| 4 | **Disk cache** | `ImageDiskCache` | I/O | Keeps downloaded files on the phone. |
| 5 | **Data loader** | `DataLoader` «protocol» | Core | Promises bytes for a URL. |
| 6 | **Network loader** | `NetworkDataLoader` | I/O | Downloads the bytes. |
| 7 | **Decoder** | `ImageDecoder` | I/O | Turns bytes into a small picture. |

Not on the list yet: a file loader, a disk index, an auth header, image processing, metrics. *"I'll add those if we go there."*

No use case and no composite here: it's a library with no app rules and no model built from several sources.
:::

::: 5 · The sketch
```mermaid
flowchart TB
  subgraph A["API"]
    View["`**1 · Image view**
setImage · LazyImage`"]
  end
  subgraph C["CORE"]
    Pipe["`**2 · Image pipeline**
ImagePipeline`"]
    Mem["`**3 · Memory cache**
ImageMemoryCache`"]
    Loader["`**5 · Data loader**
«protocol»`"]
  end
  subgraph IO["I/O"]
    Disk["`**4 · Disk cache**
ImageDiskCache`"]
    Net["`**6 · Network loader**
NetworkDataLoader`"]
    Dec["`**7 · Decoder**
ImageDecoder`"]
  end
  View -- "request → image" --> Pipe
  Pipe -- "key → image" --> Mem
  Pipe -- "URL → bytes" --> Loader
  Loader ~~~ Net
  Net -. "implements" .-> Loader
  Mem ~~~ Disk
  Pipe -- "URL → bytes" --> Disk
  Pipe -- "bytes → image" --> Dec
  class View pres
  class Pipe,Mem,Loader dom
  class Disk,Dec data
  class Net net
```

**How to read it.** A solid arrow points from the part that asks to the part that answers: *request → reply*. The dashed arrow means *implements*. On a miss the pipeline tries memory, then disk, then the network, then decodes.

**Dependency inversion, in one line.** The core writes the promise (card 5); the network loader in I/O keeps it (card 6). The arrow points **up**, so the core never imports networking.

**One owner per source.** Memory, disk and network each have their own card. The pipeline owns none of them: it only decides which to ask, in order, like a composite.

**On Miro:** three frames (blue, purple, green), seven cards, six arrows. Point at card 2 and say: *"this is where two rows share one download."*
:::

::: 6 · Each component: its job, its interface, the choice inside it
Every part passes around one value:

```swift
struct ImageRequest: Hashable, Sendable {
    let url: URL
    /// Display size in pixels (points × screen scale), nil = full size
    let pixelSize: CGSize?
    /// Visible rows high, prefetch low
    let priority: Priority
}
```

### 1 · Image view (`setImage`, `LazyImage`)

**Job:** the one line a screen calls to show a picture. It cancels the old request when the row is reused.

**Interface:**

```swift
extension UIImageView {
    /// nil cancels and clears
    @MainActor func setImage(_ request: ImageRequest?)
}

struct LazyImage: View {
    init(request: ImageRequest)
}
```

**Choices:**

- **It checks the memory cache first, synchronously**, so a cached picture shows in the same frame with no flicker.
- **It keeps its current request as a token** and, before setting a result, checks the result's request still equals it. Cancelling is cooperative, so a late result for the previous row can still arrive; the check drops it.
- `LazyImage` uses `.task(id: request)`: SwiftUI cancels the load when the request changes or the view disappears, and starts it when the view appears.

### 2 · Image pipeline (`ImagePipeline`)

**Job:** every request goes through it. It checks memory, joins a load already running for the same picture, or starts one.

**Interface:**

```swift
protocol ImagePipelineType: Sendable {
    /// Synchronous memory lookup, safe on the main thread
    func cachedImage(for request: ImageRequest) -> UIImage?
    func image(for request: ImageRequest) async throws -> UIImage
    /// Optional speed-up at low priority; correctness never depends on it
    func prefetch(_ requests: [ImageRequest])
    func cancelPrefetch(_ requests: [ImageRequest])
}
```

**Choices:**

- **An actor that only keeps the books.** It holds a table of running loads, one per URL + size. It never decodes, or every decode in the app would queue behind it.
- **A running load is shared.** It stops only when the last caller waiting for it leaves (deep dive 9).
- **`async throws`**, so the share sheet and tests use the same path as the views. *Rejected:* `AsyncImage` alone. It has no shared memory cache we control and no downsampling. Fine for one screen.

### 3 · Memory cache (`ImageMemoryCache`)

**Job:** keeps decoded pictures ready to draw. When it's full, the one unused the longest goes.

```swift
protocol ImageMemoryCacheType: Sendable {
    func image(for key: ImageKey) -> UIImage?
    /// Cost = the picture's bytes
    func store(_ image: UIImage, for key: ImageKey)
    /// Called on memory warning
    func removeAll()
}

/// URL + pixel size: a picture is only reusable at the size it was decoded for
struct ImageKey: Hashable { let url: URL; let pixelSize: CGSize? }
```

**Choices:**

- **A byte budget, not an item count.** One full-screen picture costs as much as a hundred thumbnails. Cost = bytes per row × height of the decoded bitmap.
- **Emptied on `didReceiveMemoryWarningNotification`**, trimmed on `didEnterBackgroundNotification`. This bounds the *cache*; the app's total memory still moves with everything else it does.
- **Start with `NSCache`**: set `totalCostLimit` and pass each picture's bytes as `cost` in `setObject(_:forKey:cost:)`. It also evicts on its own under memory pressure. *Switch to* a small LRU (a dictionary plus a linked list) when you need a predictable eviction order or "remove this URL at every size".

### 4 · Disk cache (`ImageDiskCache`)

**Job:** keeps the downloaded files, still compressed, so seen pictures show offline.

```swift
protocol ImageDiskCacheType: Sendable {
    func data(for url: URL) async -> Data?
    func store(_ data: Data, for url: URL) async
    /// Removes the oldest files, off the launch path
    func trim(toBytes limit: Int) async
}
```

**Choices:**

- **Compressed bytes, keyed by URL alone.** Bytes don't depend on display size, so every size shares one file.
- **In `Library/Caches`**, with a size cap. The system may clear it, and that's fine for a cache.
- **The CDN's headers decide freshness; we decide retention.** Past `max-age`, a copy is revalidated with its `ETag` when online, and still shown when offline.
- *Simpler:* `URLCache` gives a disk HTTP cache for free. Own this card only because offline must outlive `max-age` and we want a cap and eviction we control (deep dive 11).

### 5 · Data loader (`DataLoader`)

**Job:** the promise "give me the bytes at this URL". The pipeline depends on it, not on the network.

```swift
protocol DataLoader: Sendable {
    /// Throws on cancel, a bad status or a short body
    func data(for url: URL) async throws -> Data
}
```

**Choice:** the one protocol drawn on the board, because it earns two things: a fake that holds its reply, to test sharing and cancelling, and a place to grow. A file loader is a new conformance, never a `switch` in the pipeline.

### 6 · Network loader (`NetworkDataLoader`)

**Job:** downloads the bytes from the CDN.

**Interface:** conforms to `DataLoader`. Built with `init(session: URLSession)`.

**Choices:**

- **It asks the CDN for the right width**, rounded up to a few buckets (160, 320, 640, 1280), so nearby sizes share one cached copy.
- **Visible requests go first.** It sets `URLSessionTask.priority` high for visible rows and low for prefetches. Prefetches use a session with `allowsConstrainedNetworkAccess = false`, so they skip Low Data Mode.

### 7 · Decoder (`ImageDecoder`)

**Job:** turns compressed bytes into a picture, shrunk to the display size, off the main thread.

```swift
protocol ImageDecoderType: Sendable {
    func image(from data: Data, maxPixelSize: CGFloat?) async throws -> UIImage
}
```

**Choices:**

- **Downsample while decoding** with ImageIO (`CGImageSourceCreateThumbnailAtIndex`, with `kCGImageSourceThumbnailMaxPixelSize`), so the full-size bitmap is never created.
- **Decode now, not at first draw** (`kCGImageSourceShouldCacheImmediately`), or the first draw decodes on the main thread mid-scroll.
- *Simpler:* `UIImage.byPreparingThumbnail(ofSize:)` does much the same in one line. Use it unless you need ImageIO's options.

**Why these parts, and no more.** Each changes for a different reason: the view helpers with UIKit and SwiftUI, the pipeline with coordination, the caches with eviction, the loader with the network, the decoder with formats. Each protocol earns its place: `DataLoader` a fake and new sources, `ImagePipelineType` a fake for screens' tests, the cache and decoder protocols fakes that let pipeline tests count calls. In a smaller codebase I'd keep those last three concrete. What I'd *not* add: a use case or repository (no app rules), a plugin or processor chain, a generic cache, a DI container. Constructor injection is enough.
:::

::: 7 · Key flows through the sketch
**Flow 1 — two rows want the same avatar.** Memory and disk both miss.

```mermaid
sequenceDiagram
  participant A as Row A
  participant B as Row B
  participant P as Pipeline
  participant L as Network loader
  participant X as Decoder
  A->>P: image(url, 160px)
  Note over P: no load running, start one
  B->>P: image(url, 160px)
  Note over P: same key loading, wait
  P->>L: data(url)
  alt downloaded
    L-->>P: bytes
    P->>X: image(bytes, 160)
    X-->>P: image
    P-->>A: image
    P-->>B: same image
  else failed
    L-->>P: error
    P-->>A: throws
    P-->>B: throws
  end
```

One download and one decode serve both rows. The pipeline also saves the bytes to disk and the picture to memory.

**Flow 2 — a row is reused before its picture arrives.**

```mermaid
sequenceDiagram
  participant A as Row A
  participant B as Row B
  participant P as Pipeline
  participant L as Network loader
  A->>P: image(url)
  B->>P: image(url)
  P->>L: data(url)
  Note over A: row A reused for another post
  A->>P: cancel
  alt row B still waiting
    L-->>P: bytes
    P-->>B: image
  else nobody waiting
    P->>L: cancel
  end
```

Cancelling takes the row off the waiting list. The download stops only when the last caller leaves. If row A's result still arrives, its view sees the request token no longer matches and drops it.
:::

::: 8 · The server contract
```
GET https://img.example.com/{id}?w={160|320|640|1280}
    → 200  image/jpeg
           Cache-Control: max-age=86400
           ETag: "a1b2"

GET same URL, If-None-Match: "a1b2"
    → 304  (keep the copy on disk)
```

- **Width buckets**, so the phone downloads a 640-pixel picture, not a 4000-pixel original, and nearby sizes share one CDN copy.
- **`Cache-Control` says how long a copy is fresh; `ETag` checks a stale one cheaply.** A 304 sends no bytes.
- **The client chooses how long to keep files.** Past `max-age` a copy is stale, not gone: offline, the app still shows it.
:::

::: 9 · Deep dive — "Two cells show the same avatar. Walk me through it."
**Decision:** the pipeline actor keeps a table: key (URL + pixel size) → the running load and how many callers wait on it.

1. **Check memory.** A hit returns at once.
2. **If a load for this key is running, join it.** Add one to its count and wait on the same task.
3. **Otherwise, put a new load in the table straight away**, before any `await`.
4. **When a caller cancels, take one off the count.** That caller gets `CancellationError`. Cancel the load only when the count reaches zero. Remove the entry when it finishes, success or failure.

**Why step 3 says "straight away".** An actor lets other callers in every time it waits. If it waited before recording the load, two callers could both find nothing and both download.

**Why the view still checks.** Cancellation is cooperative: it sets a flag, and work stops at its next check. A result can already be on its way, so the view compares it with its current request before setting it.

The same URL at two sizes is two keys, two decodes. After the first download the bytes are on disk, so the second doesn't download again.

*Rejected:* cancel the shared load when any caller cancels. Row A scrolls away and kills the download row B still needs.
:::

::: 10 · Deep dive — "This grid gets the app killed on an iPhone 12. Why?"
**The fact:** a decoded picture costs width × height × 4 bytes. A 4032 × 3024 photo is a 2 MB JPEG but about 49 MB decoded. Twenty of those is the kill.

**Decision:** decode straight to the display size, off the main thread.

1. The view computes the size in **pixels**: points × screen scale. The loader asks the CDN for the next width bucket up.
2. The decoder makes a thumbnail at that size from the compressed bytes. The full-size bitmap is never created.
3. The memory cache counts each picture's bytes against a budget (a slice of what the app may use).
4. A memory warning empties the cache. Visible rows simply ask again.

*Rejected:* decode full size, then redraw smaller. Peak memory is still the full picture.

**Prefetching is an optimization, not correctness.** In UIKit, `UICollectionViewDataSourcePrefetching` tells us about rows before they appear (we call `prefetch`) and when the user flings past (`collectionView(_:cancelPrefetchingForItemsAt:)`, we cancel). Those callbacks aren't guaranteed, so a row still loads its own picture when it appears. Visible rows run at high priority, prefetches at low. SwiftUI has no prefetch callback: start the load when a row appears and cancel when it disappears (lazy stacks build rows a little before they're on screen).:::

::: 11 · Deep dive — "Why not just use URLCache?"
**Decision:** own a disk cache of compressed bytes, with a size cap.

1. **Compressed, not decoded.** Bytes are 10–50 times smaller, and decoding is cheap next to downloading.
2. **Safe writes.** Write to a temporary file, then rename, so a crash can't leave a half-written file under the real name.
3. **Oldest out first**, using a small index of size and last use, trimmed off the launch path.
4. **Freshness from the headers.** Within `max-age`, use the copy. Past it, show the copy at once and check in the background with `If-None-Match`. Offline, keep showing it.

*Rejected:* `URLCache` alone. With the default policy, a copy past `max-age` needs the network to revalidate, and you don't choose what it evicts or when. *Switch to it* if offline doesn't matter: it's free and already honours the CDN's headers.
:::

::: 12 · Failure modes, production and scale
**Failures**

| Failure | Client behaviour |
|---|---|
| Offline | Disk hits show, even if stale; misses fail fast to a placeholder |
| Download fails | One retry for timeouts and 5xx, none for 4xx; remember a 404 briefly |
| 429 from the CDN | Honour `Retry-After`; drop prefetches first |
| Corrupt file | Delete it from disk, download once more, then placeholder |
| Memory warning | Empty the memory cache; visible rows ask again |
| Late result into a reused row | Dropped by the request-token check |
| Signed URL expired | Ask the app for a fresh URL, retry once |
| App killed mid-write | The temporary file is never renamed; the old copy stays |

**Production notes** (short, not on the board)

- **Networking:** a timeout per request; retry only what's safe, with backoff; visible first, prefetch low; cancel what no row needs.
- **Metrics:** memory and disk hit rate, load time, decode time, memory warnings, failure rate by status. No URLs in logs if images are private.
- **Security:** HTTPS only. Private images use signed, expiring URLs or an auth header in the loader. Key the cache on the image ID, not the signature, or every new signature is a miss. Keep private files in their own folder with file protection, and clear it on sign-out.

**Scale, back of the envelope.** Use the interviewer's numbers; the shape is what matters.

```text
pictures on screen × pixels each × 4 bytes   = memory for one screen
users a day × pictures each × bytes each     = CDN bandwidth
```

30 thumbnails × 400 × 400 px × 4 bytes is about 19 MB a screen, so a cache budget of a few screens is 50–100 MB. The same 30 at a 12-megapixel full size would be about 1.5 GB. 10M users × 200 pictures × 40 KB is about 80 TB a day: width buckets and hit rate move cost, not the client architecture.

**Grow only when asked**

```text
One screen, few pictures  → AsyncImage, or URLCache + NSCache
A fling grid              → this pipeline: share, cancel, downsample
Offline past max-age      → our own disk cache
Bigger disk cache         → move its index to SQLite
Private images            → auth in the loader, a protected folder
Older phones              → decode one screen ahead, fetch bytes further
```
:::

::: 13 · Question bank — everything they can push on
Answer out loud first, then open.

### Scope and architecture

<details>
<summary>"Walk me through the layers."</summary>

API: the view helpers callers touch. Core: the pipeline, the memory cache and the data loader promise. I/O: disk cache, network loader, decoder.
</details>

<details>
<summary>"Where's the use case? The composite repository?"</summary>

There are none. A library has no app rules and no model combined from several sources, so neither earns its place.
</details>

<details>
<summary>"Show me dependency inversion."</summary>

The pipeline holds a `DataLoader` protocol. The network loader implements it. The arrow points up, so the core never imports networking.
</details>

<details>
<summary>"Where do bytes become a picture?"</summary>

Only in the decoder. The disk cache and loader deal in bytes; the memory cache and views deal in pictures.
</details>

<details>
<summary>"Why seven parts and not one ImageManager?"</summary>

Each changes for a different reason: the loader with the network, the decoder with formats, the caches with eviction, the pipeline with coordination. One class would change for all of them.
</details>

<details>
<summary>"When is AsyncImage enough?"</summary>

One screen, few pictures, no offline need. It has no memory cache we control and no downsampling.
</details>

<details>
<summary>"Isn't this a lot of protocols for one library?"</summary>

`DataLoader` earns a fake and new sources; the pipeline protocol earns a fake for screens. The cache and decoder protocols are only for pipeline tests, so I'd keep them concrete in a small codebase.
</details>

### Caching

<details>
<summary>"Why two caches?"</summary>

Memory gives a same-frame hit when scrolling back. Disk gives offline and saves data. They hold different things: pictures and bytes.
</details>

<details>
<summary>"Why does the memory cache key on URL plus size?"</summary>

A picture decoded for 80 points can't be reused at 300. Bytes are the same at every size, so disk keys on URL alone.
</details>

<details>
<summary>"Why a byte budget?"</summary>

One full-screen picture can cost as much as a hundred thumbnails. Counting items doesn't bound memory.
</details>

<details>
<summary>"Why not store decoded pictures on disk?"</summary>

They're 10–50 times bigger. Decoding is cheap next to the disk space.
</details>

<details>
<summary>"NSCache or your own LRU?"</summary>

`NSCache` first, with `totalCostLimit` and each picture's bytes as its cost. Own an LRU when you need a known eviction order or "remove this URL at every size".
</details>

<details>
<summary>"When is a cached file stale?"</summary>

When it's past the CDN's `max-age`. Stale isn't gone: show it, revalidate with `ETag` when online, keep showing it offline.
</details>

<details>
<summary>"Does the app's memory stay flat while scrolling?"</summary>

No. The image cache is bounded by bytes and empties on memory warnings, so image memory doesn't grow with scroll depth. Total app memory still moves.
</details>

<details>
<summary>Follow-up chain: "Revalidation."</summary>

1. *"The picture on the server changed."* → The disk copy has an `ETag`.
2. *"When do you check?"* → Once it's past the CDN's `max-age`, in the background.
3. *"What does the user see meanwhile?"* → The old copy, at once.
4. *"And if it's unchanged?"* → A 304, no bytes. Just mark it fresh.
</details>

### Concurrency and cancellation

<details>
<summary>"Two rows want the same picture."</summary>

The pipeline finds the running load for that key and the second row waits on it. One download, one decode.
</details>

<details>
<summary>"Why is the pipeline an actor?"</summary>

Its table of running loads is changed by many callers. An actor makes sure only one changes it at a time.
</details>

<details>
<summary>"Why not decode inside the actor?"</summary>

Every decode in the app would queue behind one actor. The actor keeps the books, the decoder runs elsewhere.
</details>

<details>
<summary>"An async function runs off the main thread, right?"</summary>

Not always. With SE-0461's behaviour on (Swift 6.2), a plain `nonisolated async` function runs on the caller's actor. Mark the decoder `@concurrent` to move it off.
</details>

<details>
<summary>"A cell is reused. What happens?"</summary>

The view cancels its request and starts the new one. The pipeline cancels the download only if nobody else waits.
</details>

<details>
<summary>Follow-up chain: "The wrong picture flashes."</summary>

1. *"A reused row shows the old picture for a moment."* → The old result arrived after cancel.
2. *"Why, if you cancelled?"* → Cancelling only sets a flag. Work stops at its next check.
3. *"Fix?"* → The view keeps a request token and sets a result only if it matches.
4. *"Why not just cancel harder?"* → A result can already be on its way; only the check makes it harmless.
</details>

### Performance and memory

<details>
<summary>"How much memory does a picture take?"</summary>

Width × height × 4 bytes, decoded. A 12-megapixel photo is about 49 MB.
</details>

<details>
<summary>"It stutters. Where do you start?"</summary>

Instruments first. Usual causes: decoding on the main thread, decoding at full size, decoding at first draw.
</details>

<details>
<summary>"How does prefetch work?"</summary>

The collection view's prefetch callback calls `prefetch` at low priority, and its cancel callback cancels it. It's an optimization: the callbacks aren't guaranteed, so each row still loads its own picture.
</details>

<details>
<summary>"And in SwiftUI?"</summary>

No prefetch callback. Start the load when the row appears and cancel when it disappears; `.task(id:)` does both.
</details>

<details>
<summary>"Visible rows and prefetches compete. Who wins?"</summary>

Visible rows. They get high task priority, and the loader caps connections per host (`httpMaximumConnectionsPerHost`).
</details>

<details>
<summary>"Low Data Mode?"</summary>

Prefetches use a session with `allowsConstrainedNetworkAccess = false`, so they don't run. Visible rows still load, at a smaller bucket.
</details>

### Testing, security and change

<details>
<summary>"How do you test deduplication?"</summary>

A fake loader that holds its reply. Ask twice for the same URL, then check it was called once.
</details>

<details>
<summary>"How do you test cancellation?"</summary>

Two callers, cancel one, check the fake loader wasn't cancelled. Cancel both, check it was.
</details>

<details>
<summary>"Some images are private now."</summary>

Signed, expiring URLs or an auth header in the network loader, over HTTPS. Key the cache on the image ID, not the signature. A separate disk folder with file protection, cleared on sign-out.
</details>

<details>
<summary>"What would you measure in production?"</summary>

Memory and disk hit rate, load time, decode time, memory warnings, failures by status.
</details>

<details>
<summary>"What changes at 10x?"</summary>

Mostly the CDN. On the client: smaller buckets for thumbnails, a fixed memory budget, backing off on 429s, a disk index in SQLite.
</details>

<details>
<summary>"Add a file or bundle source."</summary>

A new `FileDataLoader` conforming to `DataLoader`. The pipeline doesn't change.
</details>

<details>
<summary>Follow-up chain: "A second screen."</summary>

1. *"Tap a thumbnail to open it full screen."* → A new request, same URL, bigger size.
2. *"Does it download again?"* → Bytes are on disk under the URL. Only the decode is new.
3. *"Show something at once?"* → Show the cached thumbnail, then swap in the sharp one.
4. *"Memory?"* → The full-screen picture is one entry in the same budget.
</details>
:::

::: 14 · Scorecard — mark yourself, 0 / 1 / 2
| | Did you… | 0–2 |
|---|---|---|
| 1 | Talk the whole time, and listen when interrupted | |
| 2 | Clarify before designing | |
| 3 | Give a rejected alternative for each choice | |
| 4 | Say out of scope first; separate required from later | |
| 5 | Say the idea, list the parts, then sketch | |
| 6 | Keep the sketch to about seven cards | |
| 7 | Name the server contract: width buckets, `max-age`, `ETag` | |
| 8 | Give the decoded cost: width × height × 4 | |
| 9 | Bound the image cache by bytes; purge on memory warning | |
| 10 | Share one download per URL + size between rows | |
| 11 | Cancel only when the last caller leaves; check late results | |
| 12 | Decode to display size, off the main thread | |
| 13 | Call prefetching an optimization; visible rows first | |
| 14 | Land the recap inside 60 seconds | |

14+ is a pass.<!--private--> Anything scored 0 goes in the progress log and comes back as a recall prompt.<!--/private--><!--public--> A zero names the thing to read about next.<!--/public-->
:::

::: 15 · The 60-second recap
A view asks for a picture by URL and by the pixel size it will show it at. One pipeline actor checks a memory cache keyed by URL plus size, and if the same picture is already loading, it joins that load, so two rows share one download. On a miss, bytes come from a disk cache keyed by URL alone, or from the CDN at a rounded width. The decoder shrinks them to display size off the main thread, because a decoded picture costs width × height × 4 bytes whatever the file size. The memory cache has a byte budget and empties on memory warnings, so image memory is bounded, not the whole app's. The disk cache keeps compressed bytes: the CDN's headers decide when a copy is stale, we decide how long to keep it, so seen pictures show offline. A reused row cancels its request, the download stops only when the last caller leaves, and the view's request token drops a late result. Prefetching only makes it faster, visible rows first. The pipeline depends on a loader protocol, so a new source or a test fake plugs in without changing it; anything more waits until it's asked for.
:::
