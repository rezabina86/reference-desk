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

*A recurring senior mobile prompt in first-hand interview reports. The public exercise interviewers draw their wording from is weeeBox's image-library brief, which also publishes the grading criteria used below.*

> **Interviewer:** "We show a lot of images — feeds, avatars, a photo grid. I'd like you to design the image loading library we'd build for that. Something in the spirit of Kingfisher or Nuke. Where would you start?"

## Run it as a round, not as reading

Set a timer. Stand up. Sketch on paper or an iPad. Talk the whole time — silence is the thing that fails these rounds. **Do not open a section until its slot is over.**

| Clock | Phase | What you do |
|---|---|---|
| 0:00–0:02 | The prompt | Repeat it back in one sentence and say what you're going to do with the time |
| 0:02–0:07 | Clarify | Ask; then open section 1 only after you've asked yours, and take its answers as the interviewer's |
| 0:07–0:12 | Scope | Out of scope first, then 3–5 functional, then the non-functional ones that matter |
| 0:12–0:24 | High level | The boxes, the flow, the API and the keys |
| 0:24–0:40 | Deep dives | The interviewer picks; sections 6–8 are the three they pick from |
| 0:40–0:45 | Follow-ups and recap | Rapid fire, then the 60-second summary |

## What this question is really testing

It looks like a question about caching. It isn't, quite.

- **Can you find the axis?** Every decision here trades **memory ↔ disk ↔ CPU ↔ bandwidth**. A candidate who names that axis in the first five minutes has already passed the framing part.
- **Do you know what a decoded image costs?** Width × height × 4 bytes, regardless of file size. Everything about memory follows from that one fact, and it's the most common gap.
- **Can you design components with reasons?** They will ask why these types and not fewer. This is where SOLID earns its keep — not as vocabulary, but as four or five sentences about what would change and what wouldn't.
- **Do you think about the same image twice?** Two cells, one URL. Dedupe of in-flight work is the concurrency content of this question and the thing most answers miss.
- **Do you know when to stop?** `AsyncImage` and `NSCache` are legitimate answers for a small app. Saying so, with the condition attached, reads as senior. Building a pipeline for a settings screen does not.

**Traps:** drifting into CDN and backend design; describing a cache with no eviction; forgetting cancellation entirely; naming Kingfisher's features instead of designing; decoding on the main actor without noticing.

::: 1 · The interviewer answers your clarifying questions
Ask yours first. These are the answers you'd get, and the assumptions the rest of this chapter runs on.

**"Is this a library for one app, or an SDK other teams adopt?"**
→ *One app to start, but shaped so it could be extracted as a package later.*

**"Where do images come from — network only?"**
→ *Network mostly, but also files on disk and a few bundled assets. The public version of this exercise wants all three.*

**"Who consumes them? Views only, or code too?"**
→ *`UIImageView` and SwiftUI, and occasionally non-UI code that wants the image to share or export.*

**"What's the heaviest screen?"**
→ *A grid of thumbnails you can fling through, plus full-screen detail views.*

**"Can the server resize? Is there a CDN with a width parameter?"**
→ *Yes, assume `?w=` works and the CDN sends `ETag` and `Cache-Control`.*

**"Do images need to show offline?"**
→ *Yes. Anything the user has seen should still appear with no network.*

**"Anything sensitive in these images?"**
→ *Not today. Ask me again at the end.* (They will.)

**"What are we optimising — smoothness, data, battery?"**
→ *Scrolling must stay smooth on a three-year-old phone, and we've had memory-pressure kills in the field.*
:::

::: 2 · Requirements and scope — what you should have said
**Out of scope, stated first, before any design:** animated GIF/APNG playback, video thumbnails, editing and filters beyond resize, placeholder and transition animations (the caller owns those), plug-in loaders for arbitrary formats, and everything server-side beyond "there is a CDN with a width parameter". Progressive JPEG is a stretch goal if time allows.

**Functional — five, no more**

1. Load an image by URL from network, file or bundle, into a view or back to a caller.
2. Downsample to the size it will actually be displayed at.
3. Cache in memory and on disk; previously seen images appear offline.
4. Cancel automatically when a view stops needing the image — cell reuse, disappearance.
5. Prefetch ahead of the scroll position.

**Non-functional that matter here**

- **Memory** — decoded bitmaps are what gets the app killed. Budget them explicitly.
- **Main-thread time** — no decode and no disk I/O on the main actor; the scroll holds its frame rate.
- **Bandwidth and battery** — never fetch the same bytes twice; honour Low Data Mode.
- **Correctness** — a reused cell never shows another row's image.
- **Testability** — every I/O boundary behind a protocol.

Then say the axis out loud: *"Everything from here is memory against disk against CPU against bandwidth. I'll keep naming which one each choice spends."*
:::

::: 3 · The design, on the whiteboard
```diagram
<figure class="dg">
  <figcaption>One request, four layers, two cache keys</figcaption>

  <div class="dg-row"><span class="dg-lane">Call site</span>
    <div class="dg-nodes">
      <div class="dg-node"><b>UIImageView.setImage</b><span>@MainActor · cancels on reuse</span></div>
      <div class="dg-node"><b>LazyImage</b><span>SwiftUI · .task(id: request)</span></div>
      <div class="dg-node ghost"><b>Any async caller</b><span>share sheet, export</span></div>
    </div>
  </div>

  <div class="dg-flow">ImageRequest(url, pixel size, priority)</div>

  <div class="dg-row"><span class="dg-lane">Pipeline</span>
    <div class="dg-nodes">
      <div class="dg-node accent"><b>ImagePipeline · actor</b><span>look up, join in-flight work, or start one</span></div>
    </div>
  </div>

  <div class="dg-row"><span class="dg-lane">owns</span>
    <div class="dg-nodes">
      <div class="dg-node"><b>MemoryCache</b><span>key: url + pixel size · LRU with a byte budget</span></div>
      <div class="dg-node"><b>inFlight[ImageKey]</b><span>Task + how many callers are waiting</span></div>
    </div>
  </div>

  <div class="dg-flow">memory miss → ask for bytes, keyed by url alone</div>

  <div class="dg-row"><span class="dg-lane">Data</span>
    <div class="dg-nodes">
      <div class="dg-node"><b>DataLoader</b><span>dedupes downloads by url</span></div>
      <div class="dg-node"><b>DiskCache</b><span>encoded bytes · SHA-256 filename · LRU index + ETag</span></div>
    </div>
  </div>

  <div class="dg-flow">disk miss</div>

  <div class="dg-row"><span class="dg-lane">Sources</span>
    <div class="dg-nodes">
      <div class="dg-node warm"><b>URLSession → CDN</b><span>?w= bucket · ETag · Low Data Mode</span></div>
      <div class="dg-node"><b>File / bundle</b><span>same protocol, no network</span></div>
    </div>
  </div>

  <div class="dg-flow up">bytes</div>

  <div class="dg-row"><span class="dg-lane">Decode</span>
    <div class="dg-nodes">
      <div class="dg-node accent"><b>ImageDecoder · @concurrent</b><span>downsample straight to pixel size, decode eagerly</span></div>
    </div>
  </div>

  <div class="dg-flow up">UIImage → memory cache → every caller waiting on this key</div>

  <p class="dg-note">The two keys are the point: bytes are the same at any display size, a decoded bitmap is not.</p>
  <div class="dg-legend"><span>accent · owns concurrency</span><span>warm · crosses the network</span><span>dashed · optional caller</span></div>
</figure>
```

Narrate it in one pass: a request carries a URL and the pixel size it will be shown at. The pipeline checks the memory cache under URL + size; a hit returns in the same frame. On a miss it looks for an in-flight task for that key and joins it instead of starting a second one. Otherwise it asks for bytes — disk first, then network, deduplicated by URL alone — hands them to the decoder, which downsamples off the main actor, stores the result and gives it to everyone waiting. Only the final assignment to the view is main-actor work.
:::

::: 4 · The types, and the reasons behind them — SOLID out loud
They will ask *"why these types and not one `ImageManager`?"*. The answer is five sentences about change, not five principle names. Name the principle **after** the reason, if at all.

```diagram
<figure class="dg">
  <figcaption>What depends on what — protocols in the middle, concretes at the edges</figcaption>

  <div class="dg-group">
    <p class="dg-group-label">Composition root — the only place concrete types are named</p>
    <div class="dg-split">
      <div class="dg-node ghost"><b>URLSessionDataLoader</b><span>network bytes</span></div>
      <div class="dg-node ghost"><b>FileDataLoader</b><span>disk / bundle bytes</span></div>
      <div class="dg-node ghost"><b>ImageIODecoder</b><span>downsample + decode</span></div>
      <div class="dg-node ghost"><b>LRUMemoryCache</b><span>byte budget</span></div>
    </div>
  </div>

  <div class="dg-flow up">injected once, at start-up</div>

  <div class="dg-row"><span class="dg-lane">Seams</span>
    <div class="dg-nodes">
      <div class="dg-node accent"><b>ImageDataLoaderType</b><span>data(for:) async throws</span></div>
      <div class="dg-node accent"><b>ImageDecoderType</b><span>image(from:to:) async throws</span></div>
      <div class="dg-node accent"><b>ImageCacheType</b><span>get / set / removeAll</span></div>
    </div>
  </div>

  <div class="dg-flow up">depends only on these</div>

  <div class="dg-row"><span class="dg-lane">Policy</span>
    <div class="dg-nodes">
      <div class="dg-node"><b>ImagePipeline</b><span>coordination: keys, dedupe, cancellation, cache writes</span></div>
    </div>
  </div>
</figure>
```

**Single responsibility — say it as "what would make each of these change".** The loader changes when the transport changes. The decoder changes when the format or the downsampling strategy changes. The cache changes when the eviction policy changes. The pipeline changes when the *coordination* rules change — dedupe, cancellation, which cache to consult first. Four reasons, four types. One `ImageManager` would be touched by all four, which is why it becomes the file nobody wants to review.

**Open–closed, concretely.** Adding a source — bundle assets today, the Photos framework tomorrow, base64 data URLs for tests — is a new conformance to `ImageDataLoaderType` and a line in the composition root. No `switch` inside the pipeline grows. That's the practical form of the principle: new behaviour by composition, not by editing the coordinator.

**Liskov, in the form it actually bites on iOS.** Every loader must honour the same contract: it throws `CancellationError` when cancelled, it never returns half the bytes, and it is safe to call concurrently. A file loader that quietly ignores cancellation satisfies the *compiler* and breaks every caller written against the protocol. Contracts in a protocol are behaviour, not just signatures — which is why the protocol's documentation comment says those three things, and why the same test suite runs against every conformance.

**Interface segregation.** `ImagePipelineType` has three methods. Prefetching lives in its own `ImagePrefetchingType`, so a detail screen that shows one image doesn't depend on — or have to fake — prefetch. The test is the doubles: if a mock needs twelve methods to test one, the protocol is too fat.

**Dependency inversion.** The pipeline depends on protocols; `URLSession`, ImageIO and the file system are injected at the composition root. In Swift this mostly looks like taking protocols in `init`, and its payoff is concrete: the dedupe test in section 6 needs a loader whose response is held open by the test, which is impossible if the pipeline constructs a `URLSession` itself.

**And the honest caveat, which is worth saying in the room:** SOLID came from a world of class hierarchies. On iOS, half of it shows up as value types and protocol witnesses rather than inheritance, and taken too far SRP gives you thirty one-method types nobody can navigate. *"I split where a reason to change differs, not per noun."*
:::

::: 5 · API and the two keys
**The server contract.** Nothing of our own. `GET https://img.example.com/{id}?w={pixels}`, with `ETag` and `Cache-Control`. The client rounds width up into buckets — 160, 320, 640, 1280 — so neighbouring sizes share a CDN entry and a disk entry.

**Public API — three entry points over one pipeline**

```swift
struct ImageRequest: Hashable, Sendable {
    let url: URL
    let targetPixelSize: CGSize?      // nil = full size
    let priority: Priority            // .veryLow ... .high
    let allowsConstrainedNetwork: Bool
}

protocol ImagePipelineType: Sendable {
    func image(for request: ImageRequest) async throws -> UIImage
}

protocol ImagePrefetchingType: Sendable {
    func prefetch(_ requests: [ImageRequest])
    func cancelPrefetch(_ requests: [ImageRequest])
}

extension UIImageView {                         // thin, @MainActor
    @MainActor func setImage(_ request: ImageRequest?)
}

struct LazyImage: View { init(request: ImageRequest) }   // .task(id: request)
```

`async throws` is the core and the view helpers are thin, for three reasons: cancellation comes free from task cancellation, non-UI callers use the same path, and tests call it directly with no view in sight.

**The two keys — the detail most answers miss**

```swift
struct DataKey: Hashable  { let url: URL }                    // disk + network
struct ImageKey: Hashable { let url: URL; let pixelSize: CGSize? }   // memory + decode
```

Bytes don't depend on display size, so downloads and disk entries dedupe on the URL. A decoded bitmap is only reusable at the size it was decoded for, so the memory cache and in-flight decodes key on URL + size. Two cells showing one avatar at 80 pt and 300 pt share a download and get two decodes.

**Local model.** Memory: `ImageKey → (UIImage, cost)`. Disk: files in `Library/Caches/Images/` named by the SHA-256 hex of the URL, plus a small index — `hash → (byteCount, lastAccess, etag)` — for eviction and revalidation.
:::

::: 6 · Deep dive — "Two cells show the same avatar. Walk me through it."
**Decision: an actor holds a dictionary of in-flight `Task`s keyed by `ImageKey`; callers join; the work is cancelled only when the last subscriber leaves.**

```swift
actor ImagePipeline: ImagePipelineType {
    private var inFlight: [ImageKey: Entry] = [:]
    private struct Entry { let task: Task<UIImage, Error>; var subscribers: Int }

    func image(for request: ImageRequest) async throws -> UIImage {
        let key = ImageKey(request)
        if let hit = memory.value(for: key) { return hit }

        let task: Task<UIImage, Error>
        if var entry = inFlight[key] {                  // join, don't restart
            entry.subscribers += 1; inFlight[key] = entry; task = entry.task
        } else {
            task = Task { try await load(key, request) }
            inFlight[key] = Entry(task: task, subscribers: 1)
        }

        return try await withTaskCancellationHandler {
            try await task.value
        } onCancel: {
            Task { await self.unsubscribe(key) }        // last one out cancels
        }
    }
}
```

The lookup and the insert happen with no `await` between them, so they're atomic on the actor. That's the entire trick. The naive version — check the cache, `await` the download, insert — lets two callers both miss and both download, because an actor is re-entrant at every `await`. Storing the **task** rather than the result closes the window. The task must also remove its entry when it finishes, success or failure, or one failed load poisons that key forever.

*Alternative rejected: cancel the shared work when any caller cancels.* Simpler and wrong — cell A scrolls away and kills the download cell B is still waiting for. *Alternative rejected: never cancel shared work.* Wastes bandwidth exactly during a fast fling, when requests pile up.

*Switch condition:* if profiling showed duplicate URLs are rare on screen, the subscriber count is complexity for nothing; plain per-caller cancellation is fine. A nice middle: on last unsubscribe let the **download** finish into the disk cache and cancel only the **decode**.

**Where each piece runs.** `setImage` is `@MainActor` and reads the memory cache synchronously, so a hit paints in the same frame with no flicker. The pipeline actor does bookkeeping only — it must never decode, or every decode in the app serialises behind one executor. Decoding is `@concurrent`, because since SE-0461 a plain `nonisolated async` function runs on the caller's actor: "it's async" no longer means "it's off the main thread", so the hop has to be asked for.

**Cell reuse is a cancellation problem, not a caching one.** `setImage` keeps the current `Task` on the view; a new call or `prepareForReuse` cancels it. On completion the view checks the request it finished for is still its current one, because cancellation is cooperative and a late result can still arrive. That check is what stops the wrong-image-in-a-reused-cell bug. SwiftUI's `.task(id: request)` gives you both behaviours for free.
:::

::: 7 · Deep dive — "This grid gets the app killed on an iPhone 12. Why?"
**The fact the rest rests on:** memory cost comes from pixel dimensions, not file size. A decoded 8-bit RGBA bitmap costs width × height × 4 bytes. A 4032 × 3024 photo that's 2 MB as a JPEG is about 49 MB decoded. Twenty of those at full size is the kill.

**Decision: decode straight to display size with ImageIO; never decode full-size and then scale.**

```swift
@concurrent
func downsample(_ data: Data, to maxPixelSize: CGFloat) -> CGImage? {
    let source = CGImageSourceCreateWithData(
        data as CFData, [kCGImageSourceShouldCache: false] as CFDictionary)!
    let options: [CFString: Any] = [
        kCGImageSourceCreateThumbnailFromImageAlways: true,
        kCGImageSourceShouldCacheImmediately: true,        // decode here, off main
        kCGImageSourceCreateThumbnailWithTransform: true,  // honour EXIF orientation
        kCGImageSourceThumbnailMaxPixelSize: maxPixelSize,
    ]
    return CGImageSourceCreateThumbnailAtIndex(source, 0, options as CFDictionary)
}
```

`ShouldCache: false` stops ImageIO holding a full-size decode; `ShouldCacheImmediately` forces the decode to happen here rather than lazily at first render on the main thread. That pair is the difference between a smooth scroll and a hitch.

*Alternative rejected:* redrawing through `UIGraphicsImageRenderer` — it decodes the full image first, so peak memory is the full bitmap. *Also available:* `UIImage.byPreparingThumbnail(ofSize:)` and `byPreparingForDisplay()` (iOS 15) do this with far less code. *Switch condition:* if you don't need EXIF-transform control or exotic formats, use them and own less code. Sizes must be in **pixels** — points × `displayScale` — which is why the request carries a pixel size the view computes.

**Decision: a custom LRU memory cache with a byte budget**, costed by `bytesPerRow × height` of the decoded image. Budget a fraction of what the process may use (sample `os_proc_available_memory()` at launch, take 15–20%, cap it). Purge on `didReceiveMemoryWarningNotification`; trim on background.

*Alternative rejected: `NSCache`.* Thread-safe, reacts to memory pressure by itself, and an entirely respectable answer. Its costs: eviction order is undocumented, you can't enumerate it to purge one URL at every size, and it's widely observed to empty itself on backgrounding — behaviour that isn't documented, so you can't design around it. *Switch condition:* one image screen, no need to purge by URL → `NSCache` with a `totalCostLimit`, and say so out loud.

**"Why cache decoded images at all, when the disk has the bytes?"** Because a disk read plus a decode is milliseconds of CPU per image, and scrolling back up the feed must paint in the same frame. Memory buys CPU and smoothness — the axis again.
:::

::: 8 · Deep dive — "Why not just use URLCache?"
**Decision: own a disk cache of encoded bytes, keyed by SHA-256 of the URL, in `Library/Caches`, with a size cap and LRU eviction driven by a small index.**

- **Encoded, not decoded.** Bytes are 10–50× smaller than the bitmap, and decoding is cheap next to the network. Storing bitmaps trades a lot of disk for a little CPU — the wrong direction on a phone.
- **Atomic writes.** Write to a temp file and rename (`Data.write(to:options: .atomic)`), so a kill mid-write leaves the old file or nothing, never a truncated JPEG that fails forever.
- **LRU needs its own index.** File access dates aren't a dependable "recently used" signal, so keep `hash → (bytes, lastAccess, etag)` in a small file or SQLite, updated in memory and flushed in batches.
- **Sweep off the launch path.** Enforce the cap (150–300 MB) on background entry or a low-priority task, never during start-up.
- **`Library/Caches` is not backed up and the system may purge it** — correct for a cache, and the code must treat any file as possibly gone.

*Alternative rejected: `URLCache`.* Free, handles HTTP semantics, and Nuke's default loader leans on it. It loses here because it obeys the server: a CDN sending `max-age=300` means "offline after five minutes", which breaks functional requirement 3. It also gives no control over eviction, can't purge one URL, and covers network sources only. *Switch condition:* if you control the cache headers and offline display isn't required, `URLCache` with a large `diskCapacity` is the better answer — less code, correct revalidation for free. Say that it's a judgement call, not a rule.

**Revalidation.** Store the `ETag`; past a freshness window, show the disk copy immediately and revalidate in the background with `If-None-Match`. A 304 just touches the index. Stale-while-revalidate, client-side.
:::

::: 9 · Failure modes and 10×
- **Offline.** Disk hits work; misses fail fast with a typed error the view maps to a placeholder. Don't retry into a dead network — watch `NWPathMonitor` and let the view re-request when the path returns.
- **Errors and retries.** One retry with jittered backoff for transient failures (timeout, connection lost, 5xx); none for 4xx. Remember 404s briefly in memory so a broken URL isn't refetched on every scroll.
- **Races.** Duplicate work: the in-flight dictionary. Late result into a reused cell: the current-request check.
- **Corrupt bytes.** Decode returns nil → delete the disk entry, refetch once, then give up. Never loop on a file that will never decode.
- **Memory pressure.** Memory warning purges the cache; in-flight decodes for visible cells finish. MetricKit's exit reasons tell you if you're being killed in the field; the first knob is the budget, the second the width buckets.
- **Killed mid-operation.** Atomic writes keep the disk consistent; the index may lag, so the next sweep reconciles — orphan files deleted, entries without files dropped.
- **Low Data Mode.** Prefetches set `allowsConstrainedNetworkAccess = false` and simply don't run on a constrained path; visible requests still load at a smaller bucket. A failure with `networkUnavailableReason == .constrained` becomes tap-to-load.
- **Too many requests at once.** A fling issues dozens. Cap per-host connections and give visible requests priority over prefetches; decodes run on the cooperative pool, already sized to the cores.

**At 10×** — ten times denser grid, or ten times more images per session:
- Memory: the budget is fixed by the device, so hit rate falls. Smaller buckets for thumbnails; cache fewer sizes per URL.
- Disk: the index moves to SQLite so eviction is a query rather than a full load.
- CPU: decode becomes the bottleneck on older devices. Prefetch decodes one screenful ahead, bytes further ahead.
- Bandwidth: the CDN width parameter carries almost all of it. The client's job is to ask for the smallest bucket that still looks sharp.
:::

::: 10 · Rapid fire — the follow-ups
1. **"Why not just use `AsyncImage`?"** → No memory cache you control, no downsampling, no prefetch, no dedupe across views. Fine for a settings screen, not a feed.
2. **"Same URL on screen at two sizes — what happens?"** → One download (data key is the URL), two decodes and two memory entries (image key includes size), one copy on disk.
3. **"A cell scrolls away. What exactly gets cancelled?"** → Its subscription. The shared task only when the count hits zero — optionally let the download finish into disk and cancel only the decode.
4. **"These are medical scans. What changes?"** → Ask whether caching is permitted at all; then no disk cache, or `.completeFileProtection`; purge memory on background; no third-party CDN caching; encrypt at rest with a Keychain key if it stays.
5. **"How do you test the dedupe?"** → A loader double whose response is held open by the test: fire two requests, assert one load call, release, assert both callers got the same image. Count `Task.yield()`s, never sleep.
6. **"How do you know it's working in production?"** → `os_signpost` around load and decode, hit-rate counters for both caches, MetricKit for hangs and memory-pressure exits, and the cache budget behind a remote flag.
7. **"Why is `ImagePipeline` an actor and not a class with a lock?"** → The coordination is async by nature (it awaits loads), and a lock can't be held across an `await`. The actor gives serialised bookkeeping without blocking a pool thread.
8. **"What would you cut if you had two days instead of two weeks?"** → Memory cache + downsampling + cancel-on-reuse. Those three carry the smoothness and the crashes. Disk cache, prefetch and dedupe come next, in that order.
:::

::: 11 · Scorecard — mark yourself, 0 / 1 / 2
The public exercise this prompt comes from lists what the interviewer grades: clear communication, requirement clarification, practical trade-off analysis, honestly acknowledging what you don't know, and balancing engineering quality against timelines. Those are the first five rows; the rest are specific to this question.

| | Did you… | 0–2 |
|---|---|---|
| 1 | Narrate continuously, and listen when interrupted | |
| 2 | Clarify before designing, and state your assumptions | |
| 3 | Attach a rejected alternative and a switch condition to each choice | |
| 4 | Say plainly where your knowledge ends | |
| 5 | Name a smaller version that would be enough (`AsyncImage`, `NSCache`) | |
| 6 | Say out of scope **first** | |
| 7 | Name the memory ↔ disk ↔ CPU ↔ bandwidth axis | |
| 8 | Give the decoded-bitmap cost formula | |
| 9 | Use two keys: URL for bytes, URL + size for images | |
| 10 | Dedupe in-flight work, and handle cancellation with sharing | |
| 11 | Keep decode off the main actor, explicitly | |
| 12 | Land the recap inside 60 seconds | |

12+ is a pass in a real round.<!--private--> Anything scored 0 goes in the progress log and comes back as a recall prompt.<!--/private--><!--public--> A zero is worth more than the total: it names the thing to read about before the next one.<!--/public-->
:::

::: 12 · The 60-second recap
An image library is a set of caches trading memory, disk, CPU and bandwidth. A request carries a URL and the pixel size it will be shown at. An actor-owned pipeline checks a memory cache keyed by URL plus size, then joins any in-flight task for that key so nothing loads twice. On a miss, bytes come from a disk cache keyed by URL alone, or from the network. Decoding happens off the main actor and straight to display size, because a decoded bitmap costs width × height × 4 bytes whatever the file size. The memory cache is an LRU with a byte budget that empties on memory warnings; the disk cache holds encoded bytes with atomic writes and its own index, rather than trusting `URLCache`, because offline display can't depend on the server's cache headers. Cell reuse is cancellation: a view cancels its subscription, shared work stops only when nobody is waiting, and a late result is dropped if the cell has moved on. Four types — loader, decoder, cache, pipeline — because each has its own reason to change, and everything crosses a protocol so the pipeline can be tested with doubles.
:::
