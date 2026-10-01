---
title: 02 · Infinite photo feed
summary: "We have a feed of photos that scrolls forever. Design the client."
minutes: 50
sources:
- weeeBox · Mobile system design, the Twitter feed walkthrough (cursor pagination, local storage, real-time options) | https://github.com/weeeBox/mobile-system-design
- System Design Handbook · iOS system design interview | https://www.systemdesignhandbook.com/guides/ios-system-design-interview/
- WWDC21 · Make blazing fast lists and collection views | https://developer.apple.com/videos/play/wwdc2021/10252/
- WWDC19 · Advances in UI data sources | https://developer.apple.com/videos/play/wwdc2019/220/
- WWDC23 · Discover Observation in SwiftUI | https://developer.apple.com/videos/play/wwdc2023/10149/
- Apple · UICollectionViewDataSourcePrefetching | https://developer.apple.com/documentation/uikit/uicollectionviewdatasourceprefetching
- Apple · NSDiffableDataSourceSnapshot.reconfigureItems(_:) | https://developer.apple.com/documentation/uikit/nsdiffabledatasourcesnapshot/reconfigureitems(_:)
- Apple · onScrollTargetVisibilityChange(idType:threshold:_:) | https://developer.apple.com/documentation/swiftui/view/onscrolltargetvisibilitychange(idtype:threshold:_:)
- Apple · allowsConstrainedNetworkAccess | https://developer.apple.com/documentation/foundation/urlsessionconfiguration/allowsconstrainednetworkaccess
---

*An image-heavy feed is one of the recurring senior mobile prompts in the first-hand reports collected for this programme. The public corpus interviewers draw on uses a Twitter-style feed as its main worked example, and the pagination advice below matches it: cursors, not offsets.*

> **Interviewer:** "We have a feed of photos — think Instagram's home feed. It scrolls forever. Design the client for me."

## Run it as a round, not as reading

Set a timer. Stand up. Sketch. Talk the whole time. **Do not open a section until its slot is over.**

| Clock | Phase | What you do |
|---|---|---|
| 0:00–0:02 | The prompt | Repeat it back in one sentence and say how you'll use the time |
| 0:02–0:07 | Clarify | Ask yours; then open section 1 and take its answers as the interviewer's |
| 0:07–0:12 | Scope | Out of scope first, then 3–5 functional, then the non-functional ones that matter |
| 0:12–0:24 | High level | The boxes, the flow, the contract, the state |
| 0:24–0:40 | Deep dives | The interviewer picks; sections 6–8 are the three they pick from |
| 0:40–0:45 | Follow-ups and recap | Rapid fire, then the 60-second summary |

## What this question is really testing

It looks like a question about lists. It is a question about **three clocks running at once**: the frame clock (16 ms, or 8 ms on a 120 Hz screen), the network clock (hundreds of milliseconds per page) and the user's thumb, which is faster than both.

- **Do you pick cursor pagination, and can you say why?** Offsets break the moment someone posts while you scroll. This is the single most-checked line in the answer.
- **Do you know the cell's height before the image arrives?** Layout jumps are the visible bug in most feeds, and the fix is in the API, not in the view.
- **Can you keep "load the next page" from firing five times?** That's the concurrency content: a guard that is atomic on the main actor, and a refresh that doesn't race with a page load.
- **Do you treat the image work as solved?** You built it in question 1. Say "the image pipeline from before" and spend the time on the feed.
- **Do you keep it client-side?** Ranking, fan-out and timelines are the server's job. Name them as out of scope in the first minute.

**Traps:** offset pagination; inserting new posts at the top while the user is reading; holding `UIImage`s in the model; a like button that flickers back when the feed refreshes; designing the ranking algorithm.

::: 1 · The interviewer answers your clarifying questions
Ask yours first. These are the answers you'd get, and the assumptions the rest of this chapter runs on.

**"What's in a post?"**
→ *One photo, an author, a caption, a like count and whether I liked it. Carousels and video exist in the real app; leave them out.*

**"Who orders the feed — chronological or ranked?"**
→ *Ranked, by the server. The client gets pages in order and doesn't reorder.*

**"How much should work offline?"**
→ *Opening the app on the U-Bahn should show what you saw last time. Posting and liking offline are nice-to-haves.*

**"Do new posts appear live?"**
→ *We'd like the user to know there's something new. We don't need a live socket for it.*

**"Which interactions matter?"**
→ *Like and unlike from the feed. Comments open a separate screen — out of scope.*

**"Minimum OS, UIKit or SwiftUI?"**
→ *iOS 17 minimum. SwiftUI app, but the feed screen is the most performance-sensitive thing we have — tell me what you'd use.*

**"What hurts today?"**
→ *Stutter when flinging on older phones, the list jumping when images load, and data use.*
:::

::: 2 · Requirements and scope — what you should have said
**Out of scope, stated first:** ranking and the server timeline, posting and the camera, comments, stories, video and carousels, ads, search. The image loading pipeline is in scope only as a dependency — it's question 1, and you say so.

**Functional — four**

1. Show a ranked feed of photo posts that loads more as you scroll, without a visible wait in normal conditions.
2. Pull to refresh; tell the user when newer posts exist, without moving what they're reading.
3. Like and unlike, instantly, surviving a refresh and a flaky network.
4. Show the last-seen feed immediately on launch, including offline.

**Non-functional that matter here**

- **Smoothness** — no dropped frames while flinging on a three-year-old phone. No decode, no JSON parsing, no layout measurement of unknown images on the main actor.
- **Stability** — the content under the user's thumb never moves unless they asked it to.
- **Memory** — bounded however far you scroll; decoded images are the budget, not models.
- **Data and battery** — prefetch a little ahead, not a lot; honour Low Data Mode.
- **Correctness** — no duplicates, no gaps, no stale like state.

Then say the axis: *"Everything here trades how far ahead I load against memory, data and battery. Too little and the user waits; too much and we pay for posts nobody sees."*
:::

::: 3 · The design, on the whiteboard
```diagram
<figure class="dg">
  <figcaption>One screen, one source of truth, two pipelines underneath</figcaption>

  <div class="dg-row"><span class="dg-lane">View</span>
    <div class="dg-nodes">
      <div class="dg-node"><b>FeedView</b><span>collection view · cells sized from the model</span></div>
    </div>
  </div>

  <div class="dg-flow both">state out · intents in (appear, near end, refresh, like)</div>

  <div class="dg-row"><span class="dg-lane">State</span>
    <div class="dg-nodes">
      <div class="dg-node accent"><b>FeedViewModel</b><span>@MainActor @Observable · items, phase, cursor</span></div>
    </div>
  </div>

  <div class="dg-flow both">pages · mutations</div>

  <div class="dg-row"><span class="dg-lane">Domain</span>
    <div class="dg-nodes">
      <div class="dg-node"><b>FeedRepositoryType</b><span>page(after:) · head(since:)</span></div>
      <div class="dg-node"><b>LikeServiceType</b><span>setLiked(_:post:) · last intent wins</span></div>
    </div>
  </div>

  <div class="dg-row"><span class="dg-lane">Data</span>
    <div class="dg-nodes">
      <div class="dg-node warm"><b>FeedAPI</b><span>GET /feed?cursor= · PUT/DELETE like</span></div>
      <div class="dg-node"><b>FeedStore</b><span>last ~200 posts on disk · cursor</span></div>
    </div>
  </div>

  <div class="dg-flow">cells ask for pixels, not the view model</div>

  <div class="dg-row"><span class="dg-lane">Images</span>
    <div class="dg-nodes">
      <div class="dg-node ghost"><b>ImagePipeline</b><span>question 1 · prefetch, dedupe, downsample</span></div>
    </div>
  </div>

  <p class="dg-note">Models carry URLs and sizes; only cells ever hold pixels.</p>
  <div class="dg-legend"><span>accent · owns concurrency</span><span>warm · crosses the network</span><span>dashed · reused from question 1</span></div>
</figure>
```

Narrate it once: on launch the view model reads the last feed from `FeedStore` and shows it immediately, then asks the repository for the first page. Pages arrive as plain value models — id, author, caption, like state, image URL **plus its width and height** — and the view model merges them by id into one ordered array. The view renders that array; each cell knows its height from the model before any image exists, and asks the image pipeline for exactly the pixel size it will show. When the user nears the end, the view sends "near end"; the view model fetches the next page with the cursor it holds. Likes change the model at once and go to the server behind it. The disk store is rewritten from the head of the feed after each successful first-page load.
:::

::: 4 · The state, and why it lives where it does
They will ask *"walk me through the layers"* and then *"why MVVM?"*. Answer with what each layer owns and what would make it change.

**The view model owns the feed's state, and only the feed's state.**

```swift
@MainActor @Observable
final class FeedViewModel {
    private(set) var items: [FeedItem] = []
    private(set) var phase: Phase = .idle
    private(set) var newerAvailable = false

    enum Phase: Equatable {
        case idle, loadingFirst, loadingMore, refreshing
        case failed(FeedError), exhausted
    }

    func onAppear() async
    func onNearEnd() async          // the only pagination trigger
    func refresh() async
    func toggleLike(_ id: PostID)
}
```

- **One `phase`, not five booleans.** `isLoading`, `isRefreshing`, `hasError`, `isAtEnd` as separate flags allow states that can't exist — loading *and* failed — and every view has to defend against them. An enum makes the impossible states unrepresentable, and it's the guard the pagination deep dive leans on.
- **`@MainActor`, because the view reads it every frame.** All mutations happen on one actor, so check-then-set needs no lock. The network and the JSON decoding are not on it — the repository is `Sendable` and does that work elsewhere, returning finished values.
- **`@Observable`, not `ObservableObject`.** With Observation a view re-renders only when a property it actually read changes. A cell reading one post's like count isn't invalidated because `phase` flipped. *Switch condition:* below iOS 17, `ObservableObject` with care over what's `@Published`.

**The model holds no pixels.** `FeedItem` is a `Sendable` struct of strings, ints and URLs — around a kilobyte. Ten thousand of them is about 10 MB, which is fine. A `UIImage` in the model would be 1–4 MB *each* once decoded; that's how feeds get killed. Pixels belong to cells, borrowed from the image pipeline's cache.

**Why MVVM here, said honestly.** The view model is the seam that makes the feed testable without a view: give it a fake repository, call `onNearEnd()` twice, assert one request. *Alternative rejected:* a single reducer store (TCA-style). It buys a strict event log and time-travel testing at the cost of a dependency and a learning curve for the team. *Switch condition:* if several screens share feed state — a profile grid and the home feed both showing the same post's like — move the post cache below the view models into a shared `@MainActor` store, so a like in one place is a like everywhere.

**UIKit or SwiftUI for the scroll itself?** `UICollectionView` with a diffable data source and cell registrations, wrapped in `UIViewControllerRepresentable`. It recycles cells, gives you `prefetchDataSource`, and has had a decade of tuning for exactly this. SwiftUI `List` is also backed by a collection view and recycles; `LazyVStack` creates views lazily but is widely reported to keep views it has created, so memory grows with distance scrolled — Apple doesn't document either behaviour, which is itself a reason to pick the one whose reuse you control. *Switch condition:* a moderate feed with simple cells, on iOS 18, where `List` or `LazyVStack` with `onScrollTargetVisibilityChange` profiles clean — then all-SwiftUI is less code and the right call. Say "I'd measure on the oldest supported device before committing."
:::

::: 5 · API and data model
**The server contract — cursor pages.**

```
GET /v1/feed?cursor={opaque}&limit=20
200 {
  "items": [ { "id": "p_81f", "author": {...}, "caption": "...",
               "image": { "url": "https://img.../p_81f", "width": 3024,
                          "height": 4032, "placeholder": "#7A6A58" },
               "likeCount": 412, "likedByMe": false, "createdAt": "..." } ],
  "nextCursor": "eyJyIjo...",        // null at the end
  "headToken": "h_93a"               // what "newest" meant for this session
}

GET  /v1/feed/head?since={headToken}   → { "newCount": 7 }
PUT    /v1/posts/{id}/like              → 204   (idempotent)
DELETE /v1/posts/{id}/like              → 204   (idempotent)
```

- **Cursor, not offset — the reason in one sentence:** with `?page=3`, five new posts at the top shift everything down, so page 3 repeats five posts you've seen; with a cursor, the server answers "the next 20 after *this one*", and insertions above it change nothing. Deletions don't open gaps either. The cursor is **opaque** — the client never parses it, so the server can change ranking without a client release.
- **Width and height in the payload.** The cell sizes itself from the aspect ratio before the image exists, so nothing jumps when it arrives. The placeholder colour (or a BlurHash string) fills that box meanwhile. If the server can't provide dimensions, that's the first thing to ask for — it's cheaper than any client workaround.
- **Like as PUT and DELETE, never "toggle".** "Set liked = true" sent twice is still liked. "Toggle" sent twice by a retry is unliked. Idempotent writes make retries and offline replays safe.

**Local model.**

```swift
struct FeedItem: Identifiable, Hashable, Sendable {
    let id: PostID
    let author: Author
    let caption: String
    let image: ImageRef          // url, pixel width, height, placeholder
    var likeCount: Int
    var likedByMe: Bool
}

protocol FeedRepositoryType: Sendable {
    func page(after cursor: Cursor?) async throws -> FeedPage
    func head(since token: HeadToken) async throws -> Int
}
```

**On disk:** the first ~200 posts and the cursor that follows them, written after each successful first-page load. A Codable file written atomically is enough for one screen; SwiftData or SQLite earns its place only if other screens query posts. Say which you'd pick and why — both are defensible.
:::

::: 6 · Deep dive — "The user flings to the bottom. Walk me through loading more."
**Decision: one trigger, one guard, one in-flight task — and a refresh that cancels it.**

**The trigger.** Ask for the next page when the user is within about one screen — five to ten posts — of the end. In UIKit that's `willDisplay` for an index past `items.count - threshold`, or the prefetch data source; in SwiftUI, the visibility of a post near the end via `onScrollTargetVisibilityChange` (iOS 18) or `.onAppear` on a sentinel row. *Alternative rejected:* fetching when the last cell appears. On a fling the user hits the bottom before the response, and sees a spinner every page. *Switch condition:* on a constrained network, widen the threshold and shrink the page — the round trip is the cost, not the bytes.

**The guard — the concurrency content of this question.**

```swift
func onNearEnd() async {
    guard phase == .idle, let cursor else { return }   // check…
    phase = .loadingMore                                // …and set, no await between
    let generation = self.generation

    do {
        let page = try await repository.page(after: cursor)
        guard generation == self.generation else { return }   // a refresh happened meanwhile
        append(page)
        phase = page.nextCursor == nil ? .exhausted : .idle
    } catch {
        guard generation == self.generation else { return }   // the refresh owns phase now
        phase = error is CancellationError ? .idle : .failed(FeedError(error))
    }
}
```

`willDisplay` fires for every cell past the threshold — five calls in one fling is normal. Because the view model is `@MainActor`, the check and the set run without an `await` between them, so they're atomic: the first call flips `phase` and the other four return. Put an `await` before the `phase = .loadingMore` line and you've reintroduced the double fetch — actor re-entrancy, the same bug as question 1's double miss, in a different coat.

**Refresh races with load-more.** The user pulls to refresh while page 4 is in flight. Page 4 returns after the refresh has replaced the list with fresh page 1 — and gets appended to it, with a cursor from the old session. Two fixes, used together: the refresh **cancels** the load-more task, and a **generation counter** bumped on every refresh makes any response — or error — from an older generation drop itself without touching `phase`. Cancellation alone isn't enough, because it's cooperative — a response already decoded can still arrive.

**Merging.** Append by id, skipping ids already present. Ranked feeds occasionally return an item again across pages; a duplicate id in a diffable snapshot is a crash, not a glitch. Keep a `Set<PostID>` beside the array.

**Prefetch the next images, not the next pages.** When page N+1 arrives, hand its first few image requests to the pipeline's prefetcher at low priority, with `allowsConstrainedNetworkAccess = false` so Low Data Mode skips them. Cancel prefetches for rows the user has flung past (`cancelPrefetchingForItemsAt`). That's what makes images appear already loaded, and it's question 1's API doing the work.
:::

::: 7 · Deep dive — "It stutters on an iPhone 12, and the list jumps. Why?"
**Each frame has 8–16 ms of main-thread time. Find what's spending it.** Start in Instruments — the Hangs and Animation Hitches instruments, plus `os_signpost` around cell configuration — not with guesses. The usual culprits, in the order they turn up:

1. **Decoding full-size images on the main thread.** A 12-megapixel photo decodes to about 48 MB and takes tens of milliseconds. Fixed by question 1: downsample to the cell's pixel size, off the main actor, before the image reaches the view.
2. **Measuring cells whose height depends on the image.** Self-sizing that waits for the image means the cell is laid out twice, and the content above the viewport changes height — that's the jump. **Fix: size from the model.** `height = width × image.height / image.width`, known when the post arrives. Text height is the only measured part, and caching it per post id and width makes it a dictionary lookup.
3. **Reloading instead of reconfiguring.** A like changes one number. `reloadItems` throws away the cell and builds a new one; `reconfigureItems` (iOS 15) updates the existing cell in place. In SwiftUI, Observation gives you the same thing for free if the cell reads only its own post.
4. **Too much view per cell.** Nested stacks, shadows with no `shadowPath`, rounded-corner masks on images. Flatten the hierarchy; give layers explicit shadow paths.
5. **Work in `cellForItemAt`.** Date formatting, string building, attributed text. Precompute in the model mapping on the repository side, so the cell assigns finished values.

**Keeping the user's place stable.** Three rules: never insert above the visible rows unless the user asked (that's the "new posts" pill in section 8); know every row's height before it's inserted; and on refresh, if the user has scrolled, keep the old list on screen until they tap to jump to the top.

**Memory, however far they scroll.** Models are cheap; decoded images are not. Cells hold images only while visible, and the pipeline's memory cache has a byte budget, so memory is bounded by the cache, not by the scroll distance. *Alternative rejected:* trimming the model array as the user scrolls (windowing). It bounds memory that wasn't the problem and makes scroll-up need a second, backwards cursor. *Switch condition:* sessions of tens of thousands of posts with heavy models — then keep a window of pages and page backwards too.
:::

::: 8 · Deep dive — "New posts, and the like button."
**New posts: tell, don't insert.**

*Decision:* check `GET /feed/head?since=` when the app returns to the foreground and every couple of minutes while the feed is visible; if `newCount > 0`, show a "7 new posts" pill. Tapping it scrolls to the top and loads page 1. The content under the user's thumb never moves on its own.

*Alternative rejected:* a WebSocket or server-sent events for live insertion. It costs a held connection, battery, reconnect logic and a server component, and it buys immediacy a ranked photo feed doesn't need — ranking already means "newest" isn't the point. *Alternative rejected:* silent push to trigger a refresh. Delivery is throttled by the system and not guaranteed, so it can't be the mechanism; it can be a hint. *Switch condition:* a chronological, conversational feed — chat-like, sports scores — where seconds matter. Then a socket earns its cost, and that's question 3's design.

**The like: optimistic, idempotent, last intent wins.**

```swift
func toggleLike(_ id: PostID) {
    guard let index = index(of: id) else { return }
    items[index].likedByMe.toggle()                    // UI changes now
    items[index].likeCount += items[index].likedByMe ? 1 : -1
    let wanted = items[index].likedByMe

    pendingLikes[id]?.cancel()                         // a newer tap supersedes
    pendingLikes[id] = Task {
        do { try await likes.setLiked(wanted, post: id) }
        catch is CancellationError { return }          // superseded: the newer task owns the slot
        catch { rollback(id, to: !wanted) }            // and a quiet toast
        pendingLikes[id] = nil
    }
}
```

- **Rapid taps.** Like–unlike–like in a second sends one intent at a time per post, the newest cancelling the older. Because the request says "liked = true", not "toggle", even an older request that already left the device can't leave the post in the wrong state once the newest arrives — and if ordering matters on the server, a client timestamp or a sequence number per post settles it.
- **Refresh overwrites the optimistic state.** Page 1 comes back from the server with `likedByMe: false` because the PUT hasn't landed yet, and the heart flickers off. Fix: while a like is pending for a post, the merge keeps the local value. Pending mutations are an **overlay** on server data, not a write into it.
- **Offline.** Either fail fast and roll back, or queue the intent in a small persisted outbox and replay it when `NWPathMonitor` reports a path. Idempotent PUT and DELETE make the replay safe. For likes, queueing is usually worth it; say the trade-off: the user sees "liked" for something the server hasn't recorded.

*Alternative rejected:* waiting for the server before changing the heart. Correct, and it feels broken — 300 ms to react to a tap. *Switch condition:* actions with real cost — a purchase, a follow that notifies someone — wait for the server and show progress.
:::

::: 9 · Failure modes and 10×
- **Offline at launch.** Show the stored feed with "Last updated 2 h ago". Load-more at the end of stored content shows an inline retry row, not an error screen.
- **First page fails.** With a stored feed: keep it and show a banner. Without one: a full-screen error with retry. Never replace good content with an error.
- **Page N fails.** Inline retry row at the bottom; `phase = .failed`, and the next "near end" or a tap retries. One automatic retry with jittered backoff for timeouts and 5xx, none for 4xx.
- **Cursor expired** (server says 410 or "invalid cursor" after a long background). Reload from page 1 and keep the user's place if the post they were on comes back in it; otherwise jump to top with a pill-style hint.
- **Duplicates and gaps.** Duplicates: merge by id. Gaps: impossible with cursors unless the server breaks its contract — log them, don't paper over.
- **Races.** Double load-more: the main-actor guard. Refresh versus load-more: cancel plus generation. Late like response: per-post task, newest wins.
- **Memory pressure.** The image cache purges; models stay. Visible cells re-request their images at the same size and hit the disk cache.
- **Killed mid-scroll.** Nothing to recover: the store holds the last successful first page, the outbox holds pending likes, both written atomically.
- **Low Data Mode.** No image prefetch, smaller image width bucket, same feed.

**At 10×** — ten times more posts per session, or heavier posts:
- **Scroll distance:** memory still bounded by the image cache; model array grows linearly, fine into the tens of thousands, then window it.
- **Heavier posts (carousels, video):** a cell that holds a player is the new memory hog. One player, reused, attached to the most-visible cell only.
- **More interactions per post:** the overlay of pending mutations generalises — one per post per field — and that's when a shared post store below the view models pays for itself.
- **Data:** the CDN width bucket and Low Data Mode carry it; the client's job is to ask for the smallest bucket that looks sharp.
:::

::: 10 · Rapid fire — the follow-ups
1. **"Why not offset pagination? It's simpler."** → Insertions above your position shift every later page, so you see repeats; deletions skip posts. Cursors are stable under both, and opaque cursors let the server change ranking freely.
2. **"How do you know the cell height before the image loads?"** → The API sends width and height; the cell sizes from the aspect ratio and shows a placeholder colour. If the API can't, I'd ask for it before writing client code.
3. **"Two `willDisplay` calls trigger two page loads. Fix it."** → `@MainActor` view model, `phase` checked and set with no `await` in between. Atomic by construction.
4. **"The user likes a post, then pulls to refresh, and the heart turns off. Why?"** → The refresh returned server state from before the PUT landed. Keep pending mutations as an overlay that wins over server data until confirmed.
5. **"Would you build this in SwiftUI?"** → On iOS 18 with simple cells, `List` or `LazyVStack`, if it profiles clean on the oldest device. For the app's most performance-critical screen, `UICollectionView` behind a representable, because I control reuse and prefetch.
6. **"How do you test the pagination logic?"** → A repository double that returns scripted pages and can hold a response open. Assert one request for five near-end calls; assert a refresh drops a page that returns late. No view, no network.
7. **"How do you measure scroll performance in the field?"** → MetricKit's scroll hitch rate and hang diagnostics, `os_signpost` around configuration and decode, and an image-cache hit rate. Gate the prefetch distance behind a remote flag to tune it without a release.
8. **"What would you ship in a week?"** → Cursor pages with the main-actor guard, model-sized cells, the image pipeline. Offline cache, the new-posts pill and offline likes come after, in that order.
:::

::: 11 · Scorecard — mark yourself, 0 / 1 / 2
The first five rows are the public exercise's grading criteria; the rest are specific to this question.

| | Did you… | 0–2 |
|---|---|---|
| 1 | Narrate continuously, and listen when interrupted | |
| 2 | Clarify before designing, and state your assumptions | |
| 3 | Attach a rejected alternative and a switch condition to each choice | |
| 4 | Say plainly where your knowledge ends | |
| 5 | Name a smaller version that would be enough | |
| 6 | Say out of scope **first**, including ranking | |
| 7 | Choose cursor pagination and say why in one sentence | |
| 8 | Size cells from width and height in the payload | |
| 9 | Guard load-more on the main actor, and handle refresh racing it | |
| 10 | Keep pixels out of the model; reuse the image pipeline | |
| 11 | Make likes optimistic and idempotent, and survive a refresh | |
| 12 | Land the recap inside 60 seconds | |

12+ is a pass in a real round.<!--private--> Anything scored 0 goes in the progress log and comes back as a recall prompt.<!--/private--><!--public--> A zero is worth more than the total: it names the thing to read about before the next one.<!--/public-->
:::

::: 12 · The 60-second recap
A photo feed is three clocks — the frame, the network and the user's thumb — and the design keeps the frame clock safe while the other two catch up. A main-actor view model owns one ordered array of small value models and a single phase enum. Pages come from the server by opaque cursor, so new posts never shift what's already loaded; the next page is requested a screen before the end, behind a guard that's atomic because nothing awaits between the check and the set, and a refresh cancels any page in flight and drops late answers by generation. Every post carries its image's width and height, so cells are sized before any pixel arrives and nothing jumps. Pixels never live in the model: cells ask the image pipeline from question 1 for the exact size they show, with prefetch a few rows ahead and off in Low Data Mode. New posts are announced with a pill, not inserted under the user's thumb. Likes change the screen at once, go to the server as idempotent PUT and DELETE, and stay on top of refreshed data until confirmed. The last feed is on disk, so the app opens with content even offline.
:::
