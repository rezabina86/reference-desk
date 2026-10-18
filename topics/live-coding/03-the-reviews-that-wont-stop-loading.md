---
title: 03 · The reviews that won't stop loading
summary: A paged SwiftUI reviews list for one tour, with its service in a local package. It doesn't build, it opens on a CancellationError, the rating is always a whole number, and scrolling to the end wipes the list. Fix it, then switch to the cursor endpoint, add a minimum-stars filter, and test the paging.
minutes: 60
group: Rounds
sources:
- Apple · task(id:priority:_:) — the task is cancelled when the view disappears, and restarted when the id changes | https://developer.apple.com/documentation/swiftui/view/task(id:name:priority:file:line:_:)
- Apple · CancellationError — what a cancelled Task.sleep or URLSession call throws | https://developer.apple.com/documentation/swift/cancellationerror
- Apple · refreshable(action:) — pull to refresh with an async action | https://developer.apple.com/documentation/swiftui/view/refreshable(action:)
- Swift · Sending risks causing data races — the diagnostic the first build error links to | https://docs.swift.org/compiler/documentation/diagnostics/sending-risks-data-race
- Apple · ContentUnavailableView — the standard empty, error and no-results state | https://developer.apple.com/documentation/swiftui/contentunavailableview
- GetYourGuide · iOS senior reports — tour reviews with pagination; pair coding on an existing codebase | https://www.glassdoor.com/Interview/GetYourGuide-IOS-Senior-Developer-Interview-Questions-EI_IE695237.0,12_KO13,33.htm
---

*Shape: C · review it, then extend it — 60 minutes, your Xcode, screen shared, no AI assistant · Reported:
GetYourGuide's senior iOS reports (a tour-reviews list with pagination, and pair coding on an existing codebase)
and Rightmove's live round (switch a plain endpoint to the paginated one, then prove it with unit tests) ·
Verified: Xcode 27.1, iOS 26 target, Swift 6 language mode with main-actor default isolation. The starter fails
with the two build errors below, one after the other. On the iPhone 17e simulator, the launch error, the
"4.0" rating, the end-of-list error and the double requests were reproduced, and the console lines are quoted
as the service printed them. The duplicate-and-skip in finding 7 was reproduced with a test against the starter
view model. The Part 1 fix and the final app build with no warnings, and the six tests pass on the simulator.*

**How the hour runs**

| Time | The interviewer says | You're scored on |
|---|---|---|
| 0:00–0:05 | "Clone it, open it, get it running." | Reading the isolation error, choosing the right fix |
| 0:05–0:25 | "Walk me through what you'd change. Fix what matters." | Reading the console, who owns a request, error states |
| 0:25–0:50 | "Switch to the cursor endpoint and add a star filter." | The questions you ask first, stale responses |
| 0:50–1:00 | "Write a few tests. Then: what if a review is deleted between pages?" | A fake that can be slow or fail, follow-ups |

> "This is the reviews screen for one tour. It pages through the reviews as you scroll. The service is
> a local package, and it prints every request it gets, so keep the console open. Get it running, then
> tell me what you'd change before this ships. Fix what matters. Talk as you go."

The project is in `LiveCodingLab/Round03-TourReviews`. It's written the way a 2026 project is: `@Observable`
with `@State`, `.task`, `.refreshable`, `ContentUnavailableView`, format styles. There are 30 reviews in pages
of 8, so there are 4 pages.

```swift
// ReviewsService/Sources/ReviewsService/ReviewsService.swift — the package has no default isolation
import Foundation

// MARK: - Model
public struct Review: Decodable, Hashable, Sendable {
    public let id: String
    public let author: String
    public let rating: Int          // 1...5
    public let text: String
    public let date: Date

    public init(id: String, author: String, rating: Int, text: String, date: Date) {
        self.id = id
        self.author = author
        self.rating = rating
        self.text = text
        self.date = date
    }
}

/// v1: page numbers, 1-based.
public struct ReviewPage: Decodable, Sendable {
    public let reviews: [Review]
    public let page: Int
    public let totalPages: Int
    public let totalCount: Int
}

// ReviewCursorPage, ReviewSummary and the v2 endpoint are used in Part 2.

public enum ReviewsError: LocalizedError, Equatable {
    case pageNotFound(Int)
    case invalidCursor

    public var errorDescription: String? {
        switch self {
        case .pageNotFound(let page): "Page \(page) doesn't exist."
        case .invalidCursor: "The cursor doesn't belong to this request."
        }
    }
}

// MARK: - Service
public final class ReviewsService {
    public init() {}

    private let pageSize = 8
    private var requestCount = 0

    /// v1. Deprecated by the backend team, still used by the app.
    public func fetchReviews(tourID: String, page: Int) async throws -> ReviewPage {
        requestCount += 1
        print("[ReviewsService] #\(requestCount) GET /tours/\(tourID)/reviews?page=\(page)")
        try await Task.sleep(for: .milliseconds(700))   // simulate the network

        let totalPages = (Self.all.count + pageSize - 1) / pageSize
        guard (1...totalPages).contains(page) else { throw ReviewsError.pageNotFound(page) }
        let start = (page - 1) * pageSize
        let slice = Self.all[start..<min(start + pageSize, Self.all.count)]
        return ReviewPage(reviews: Array(slice), page: page, totalPages: totalPages, totalCount: Self.all.count)
    }

    // v2: fetchReviews(tourID:minimumRating:cursor:) ... used in Part 2 ...
    // the 30 reviews ... unchanged ...
}
```

```swift
// TourReviews/TourReviews/TourReviewsViewModel.swift — the target's default isolation is MainActor
import Foundation
import Observation
import ReviewsService

@Observable
final class TourReviewsViewModel {
    let tourID: String
    var reviews: [Review] = []
    var totalCount = 0
    var hasMore = true
    var errorMessage: String?

    private let service = ReviewsService()
    private var nextPage = 1

    init(tourID: String) {
        self.tourID = tourID
    }

    var averageRating: Double {
        guard !reviews.isEmpty else { return 0 }
        return Double(reviews.map(\.rating).reduce(0, +) / reviews.count)
    }

    func loadNextPage() async {
        guard hasMore else { return }
        do {
            let page = try await service.fetchReviews(tourID: tourID, page: nextPage)
            reviews += page.reviews
            totalCount = page.totalCount
            hasMore = page.page <= page.totalPages
            nextPage += 1
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func refresh() async {
        reviews = []
        nextPage = 1
        hasMore = true
        await loadNextPage()
    }
}
```

```swift
// TourReviews/TourReviews/TourReviewsView.swift
import SwiftUI
import ReviewsService

struct TourReviewsView: View {
    @State private var viewModel = TourReviewsViewModel(tourID: "berlin-wall-walk")

    var body: some View {
        NavigationStack {
            Group {
                if let message = viewModel.errorMessage {
                    ContentUnavailableView("Couldn't load reviews",
                                           systemImage: "exclamationmark.bubble",
                                           description: Text(message))
                } else {
                    List {
                        Section {
                            ForEach(viewModel.reviews) { review in
                                ReviewRow(review: review)
                            }
                        } header: {
                            RatingSummary(average: viewModel.averageRating, count: viewModel.totalCount)
                        }

                        if viewModel.hasMore {
                            ProgressView()
                                .frame(maxWidth: .infinity)
                                .task { await viewModel.loadNextPage() }
                        }
                    }
                    .refreshable { await viewModel.refresh() }
                }
            }
            .navigationTitle("Berlin Wall walk")
            .task { await viewModel.loadNextPage() }
        }
    }
}

// RatingSummary: a star, the average with one decimal, and "· 30 reviews".
// ReviewRow: author, date, the rating as ★★★★☆, and the text.
```

## Part 1 — make it run, then review it

::: A hint, if you're stuck
The first error is about a class crossing from the main actor to somewhere else. Ask what that class holds
that makes it unsafe to share. Once it runs, don't read the code yet. Read the console: count the requests
and look at which page each one asks for. Then scroll to the very end of the list.
:::

::: The key — what I expect a senior to find
In the order you'd hit them: build, run, use, read.

**It doesn't build**

1. **`sending 'self.service' risks causing data races`**, with the note *"sending main actor-isolated
   'self.service' to @concurrent instance method 'fetchReviews(tourID:page:)' risks causing data races between
   @concurrent and main actor-isolated uses"*. The view model is on the main actor, but the package isn't
   compiled with main-actor default isolation, so its `async` method runs off the main actor. The service is a
   class with a mutable `requestCount`, so it isn't `Sendable` and can't go along. Make it an `actor`: it has
   mutable state and it's called concurrently, which is exactly what an actor is for. Say why the other
   options are worse: `@unchecked Sendable` hides a real race on `requestCount`, and `@MainActor` on the
   service puts the network fake on the UI thread.
2. **`referencing initializer 'init(_:content:)' on 'ForEach' requires that 'Review' conform to 'Identifiable'`.**
   You only see it after fixing 1. `Review` has a stable `id` but doesn't say so. Add `Identifiable` in the
   package, not `id: \.id` at each call site.

**It runs, and shows an error**

3. **The first screen says "The operation couldn't be completed. (Swift.CancellationError error 1.)"** It does
   this on every launch. The console has the first clue:

   ```
   [ReviewsService] #1 GET /tours/berlin-wall-walk/reviews?page=1
   [ReviewsService] #2 GET /tours/berlin-wall-walk/reviews?page=1
   ```

   There are two triggers. The `.task` on the screen loads a page, and so does the footer's `.task`, which is
   on screen because the list is still empty. The first response fills the list and pushes the footer off the
   screen. SwiftUI cancels the footer's task, `Task.sleep` throws `CancellationError`, and the `catch` treats it
   as a failure. That is three problems: two triggers for one page, cancellation shown as an error, and a
   request whose lifetime belongs to a row that scrolls.
4. **The header says "4.0".** The first page's ratings average 4.875. `reduce(0, +) / reviews.count` is
   integer division, and the `Double(...)` comes too late. It's also the average of the pages loaded so far,
   so it changes as you scroll, and the tour's real average is 3.9. The number belongs to the server. Fix the
   division now and say that out loud.

**Ignore the cancellation, and use it**

If you first make the `catch` skip `CancellationError`, the list loads. Then:

5. **Scroll to the end, and the whole screen turns into "Page 5 doesn't exist."** The console shows
   `#6 GET /tours/berlin-wall-walk/reviews?page=5`. There are 4 pages. `hasMore = page.page <= page.totalPages`
   is still true after page 4. It should be `<`.
6. **That error replaces 30 loaded reviews, and there's no way back.** The view shows the error *instead of*
   the list, there is no Try again button, the `List` that had the pull-to-refresh is gone, and nothing sets
   `errorMessage` back to `nil`. A failure on page 1 and a failure on page 4 are different states. Page 1
   failing means there's nothing to show: a full-screen error with Try again. A later page failing keeps the
   list and shows a retry row at the bottom.
7. **No in-flight guard, and the page counter moves after the `await`.** If two calls overlap, both read
   `nextPage == 1`, both append page 1, and both add one. I ran two overlapping `loadNextPage()` calls against
   the starter view model: 16 rows with 8 unique IDs, and the next request asked for `page=3`. Page 2 is never
   shown. In the app, the footer's cancellation hides this at launch, by luck. `removeDuplicates()` by ID would
   hide the skipped page too.
8. **Pull to refresh asks for page 1 twice.** The console shows two `page=1` requests again. `refresh()` empties
   `reviews` first, which brings the footer back on screen, so its task fires. A refresh that starts while
   page 3 is in flight has a second problem: nothing stops page 3 from landing after the refresh, and it would be
   appended to the new page 1.

**Read the code**

9. **The service is built inside the view model.** Nothing here can be tested without the real 700 ms service
   and its fixed data. Put a `ReviewsFetching: Sendable` protocol in the package, inject it in `init`, and mark
   the stored dependency `@ObservationIgnored`. You need it before Part 3.
10. **Said, not coded:**
    - The footer's `.task` runs when the footer *appears*. If a page doesn't fill the screen, the footer never
      disappears and reappears, so nothing loads the next page. Key the task on the review count.
    - Load earlier than the last row on a fast scroll, for example when the third-from-last row appears.
    - The rating is a string of ★ and ☆ glyphs. Give it an accessibility label: "4 out of 5 stars".
    - `@State private var viewModel = TourReviewsViewModel(tourID: "berlin-wall-walk")` hard-codes the tour.
      Take the ID and the service through `init`.

What sinks this part: showing `CancellationError` to the user and calling it fixed when it's silenced, without
asking why a second request existed; deduplicating by ID instead of finding the counter bug; or fixing
`hasMore` and leaving the error screen that throws away loaded pages.
:::

::: The idea behind it
Paging has one rule: **the view model owns the requests, not the rows.** A row's `.task` is a good *trigger*,
but it's a bad *owner*, because SwiftUI cancels it the moment the row scrolls away. So the view model keeps the
page request in its own `Task`, a second trigger joins the request that's already in flight, and every request
carries a generation number. A refresh, or in Part 2 a new filter, starts a new generation, and an answer from
an older generation is dropped.

The other half is error states. A list that's paged has two kinds of failure. If the first page fails, show a
full-screen error. If a later page fails, keep what's loaded and add a retry row.

| Use | Instead of |
|---|---|
| A `Task` stored in the view model, joined by a second caller | an `isLoading` flag checked by the view, or none |
| A generation number checked after every `await` | trusting that responses arrive in the order they were sent |
| `catch is CancellationError` with nothing in it | an error screen for a request nobody needs any more |
| `.task(id: reviews.count)` on the footer | `.task`, which never fires again while the footer stays on screen |
| An `actor` for a service with mutable state | `@unchecked Sendable` or `@MainActor` on a network type |
:::

::: The fix
In the package: add `Identifiable`, and add a protocol. The service becomes an actor:

```swift
public struct Review: Decodable, Identifiable, Hashable, Sendable {
    ...

// MARK: - Service
public protocol ReviewsFetching: Sendable {
    func fetchReviews(tourID: String, page: Int) async throws -> ReviewPage
}

public actor ReviewsService: ReviewsFetching {
    // ... unchanged ...
```

The view model owns the page request and drops stale answers:

```swift
import Foundation
import Observation
import ReviewsService

@Observable
final class TourReviewsViewModel {   // main actor: the target's default isolation
    enum Phase: Equatable {
        case loading            // the first page is on its way
        case loaded
        case failed(String)     // the first page failed: there is nothing to show
    }

    let tourID: String
    private(set) var phase: Phase = .loading
    private(set) var reviews: [Review] = []
    private(set) var totalCount = 0
    private(set) var hasMore = true
    private(set) var pageError: String?     // a later page failed: keep what's on screen

    init(tourID: String, service: any ReviewsFetching) {
        self.tourID = tourID
        self.service = service
    }

    /// The average of what's loaded so far, so it moves as pages arrive. The server should send it.
    var averageRating: Double? {
        guard !reviews.isEmpty else { return nil }
        return Double(reviews.map(\.rating).reduce(0, +)) / Double(reviews.count)
    }

    /// The first load, pull to refresh and Try again. Supersedes any page still in flight.
    func reload() async {
        generation += 1
        pageTask?.cancel()
        pageError = nil
        if case .failed = phase { phase = .loading }   // a refresh keeps the old list on screen
        let task = Task { [generation] in await load(page: 1, generation: generation) }
        pageTask = task
        await task.value
    }

    /// Called when the footer appears. A second call while a page is in flight joins it.
    func loadNextPage() async {
        if pageTask == nil {
            guard phase == .loaded, hasMore else { return }
            pageError = nil
            pageTask = Task { [nextPage, generation] in await load(page: nextPage, generation: generation) }
        }
        await pageTask?.value
    }

    @ObservationIgnored private let service: any ReviewsFetching
    @ObservationIgnored private var nextPage = 1
    @ObservationIgnored private var pageTask: Task<Void, Never>?   // owned here, not by a row
    @ObservationIgnored private var generation = 0

    private func load(page number: Int, generation: Int) async {
        defer { if generation == self.generation { pageTask = nil } }
        do {
            let page = try await service.fetchReviews(tourID: tourID, page: number)
            guard generation == self.generation else { return }   // a reload started meanwhile
            reviews = number == 1 ? page.reviews : reviews + page.reviews
            totalCount = page.totalCount
            nextPage = page.page + 1
            hasMore = page.page < page.totalPages
            phase = .loaded
        } catch is CancellationError {
            // superseded by a reload: not an error
        } catch {
            guard generation == self.generation else { return }
            if phase == .loaded {
                pageError = error.localizedDescription
            } else {
                phase = .failed(error.localizedDescription)
            }
        }
    }
}
```

The view switches over `phase`, keeps the list when a later page fails, and re-arms the footer after each page:

```swift
import SwiftUI
import ReviewsService

struct TourReviewsView: View {
    @State private var viewModel: TourReviewsViewModel

    init(tourID: String = "berlin-wall-walk", service: any ReviewsFetching = ReviewsService()) {
        _viewModel = State(initialValue: TourReviewsViewModel(tourID: tourID, service: service))
    }

    var body: some View {
        NavigationStack {
            content
                .navigationTitle("Berlin Wall walk")
                .task { await viewModel.reload() }
        }
    }

    @ViewBuilder
    private var content: some View {
        switch viewModel.phase {
        case .loading:
            ProgressView()
        case .failed(let message):
            ContentUnavailableView {
                Label("Couldn't load reviews", systemImage: "exclamationmark.bubble")
            } description: {
                Text(message)
            } actions: {
                Button("Try again") { Task { await viewModel.reload() } }
            }
        case .loaded where viewModel.reviews.isEmpty:
            ContentUnavailableView("No reviews yet", systemImage: "star.bubble")
        case .loaded:
            List {
                Section {
                    ForEach(viewModel.reviews) { review in
                        ReviewRow(review: review)
                    }
                } header: {
                    RatingSummary(average: viewModel.averageRating, count: viewModel.totalCount)
                }
                footer
            }
            .refreshable { await viewModel.reload() }
        }
    }

    @ViewBuilder
    private var footer: some View {
        if let message = viewModel.pageError {
            Button {
                Task { await viewModel.loadNextPage() }
            } label: {
                Label("\(message) Try again", systemImage: "arrow.clockwise")
            }
        } else if viewModel.hasMore {
            ProgressView()
                .frame(maxWidth: .infinity)
                .task(id: viewModel.reviews.count) { await viewModel.loadNextPage() }   // re-arms after each page
        }
    }
}
```

`RatingSummary` takes `average: Double?` and shows nothing while there is no average. `ReviewRow` adds
`.accessibilityLabel("\(review.rating) out of 5 stars")` to the stars. With this fix, the console shows pages 1,
2, 3 and 4, once each, the header says 4.9 for the first page, and the list ends at the 30th review with no
spinner.
:::

## Part 2 — add the feature

> "The backend team wants us off the page-number endpoint. The service already has a cursor version. Switch
> to it, and while you're there, product wants a filter: 'show reviews with at least N stars'."

::: A hint, if you're stuck
Read the doc comment on the v2 endpoint before you write anything. Then ask where the filter runs, and what the
number at the top of the screen should mean once a filter is on.
:::

::: The key — what I expect a senior to find
**The questions to ask first** — each one changes the code:

- **Does the server filter, or do we filter the pages we've loaded?** The server does: v2 takes `minimumRating`.
  Filtering the loaded pages on the phone is the trap. With 8 reviews loaded you'd show "3 reviews with 5
  stars" when the tour has 12. And if a filtered page has no matches, the footer can stay on screen and stop
  loading, so the list looks finished.
- **So what happens to paging when the filter changes?** It starts again: an empty list, a spinner, and the
  first page of a *new* cursor chain. A cursor belongs to the query that created it. The service rejects an old
  cursor with a new filter (`ReviewsError.invalidCursor`). Real backends do the same, or worse, they return the
  wrong page.
- **What if a page of the old filter is still in flight?** It must not land in the new list. Cancel it, and check
  the generation after the `await`, because cancellation doesn't stop a response that has already arrived.
- **Does the average follow the filter?** No. The header is the tour's rating, 3.9 from 30 reviews, whatever
  the filter is. The average of the 4-and-5-star reviews is always above 4, and showing it would make every tour
  look great. Show the filter's count under it instead: "Showing 22 with 4 stars or more". Both numbers come
  from the server (`summary` and `matchingCount`), so they're right before the last page has loaded.
- **What does an empty result look like?** "No reviews with 5 stars or more" with a "Show all reviews" button,
  not the "No reviews yet" screen.

**What I'm looking at while you build:**

- The end of the list is `nextCursor == nil`. There's no page arithmetic left to get wrong.
- The filter is a property on the view model. Its `didSet` resets the chain, and `.task(id: viewModel.minimumRating)`
  reloads. SwiftUI cancels the previous reload when the value changes.
- The protocol now has only the v2 method. The view model can't call the old endpoint by mistake.
:::

::: The fix
The protocol switches to v2, and the cursor page gets a public `init` so tests can build one:

```swift
/// v2: an opaque cursor. Filtering happens on the server.
public struct ReviewCursorPage: Decodable, Sendable {
    public let reviews: [Review]
    public let nextCursor: String?      // nil: there is nothing after this page
    public let matchingCount: Int       // reviews that pass the filter
    public let summary: ReviewSummary   // the whole tour, unfiltered

    public init(reviews: [Review], nextCursor: String?, matchingCount: Int, summary: ReviewSummary) {
        self.reviews = reviews
        self.nextCursor = nextCursor
        self.matchingCount = matchingCount
        self.summary = summary
    }
}

// MARK: - Service
public protocol ReviewsFetching: Sendable {
    func fetchReviews(tourID: String, minimumRating: Int?, cursor: String?) async throws -> ReviewCursorPage
}
```

The view model: a cursor instead of a page number, and a filter that starts a new chain:

```swift
import Foundation
import Observation
import ReviewsService

@Observable
final class TourReviewsViewModel {   // main actor: the target's default isolation
    enum Phase: Equatable {
        case loading            // the first page is on its way
        case loaded
        case failed(String)     // the first page failed: there is nothing to show
    }

    let tourID: String
    private(set) var phase: Phase = .loading
    private(set) var reviews: [Review] = []
    private(set) var summary: ReviewSummary?     // the whole tour: it does not follow the filter
    private(set) var matchingCount = 0           // reviews that pass the filter, counted by the server
    private(set) var pageError: String?          // a later page failed: keep what's on screen

    /// nil shows every rating. The server filters, so a new value starts a new cursor chain.
    var minimumRating: Int? {
        didSet {
            guard minimumRating != oldValue else { return }
            generation += 1                  // drop any page of the old chain still in flight
            pageTask?.cancel()
            pageTask = nil
            reviews = []
            cursor = nil
            isAtEnd = false
            pageError = nil
            phase = .loading
        }
    }

    var hasMore: Bool { !isAtEnd }

    init(tourID: String, service: any ReviewsFetching) {
        self.tourID = tourID
        self.service = service
    }

    /// The first load, a filter change, pull to refresh and Try again. Supersedes any page in flight.
    func reload() async {
        generation += 1
        pageTask?.cancel()
        pageError = nil
        if case .failed = phase { phase = .loading }   // a refresh keeps the old list on screen
        let task = Task { [generation] in await load(after: nil, generation: generation) }
        pageTask = task
        await task.value
    }

    /// Called when the footer appears. A second call while a page is in flight joins it.
    func loadNextPage() async {
        if pageTask == nil {
            guard phase == .loaded, let cursor else { return }   // no cursor: the chain has ended
            pageError = nil
            pageTask = Task { [generation] in await load(after: cursor, generation: generation) }
        }
        await pageTask?.value
    }

    @ObservationIgnored private let service: any ReviewsFetching
    @ObservationIgnored private var cursor: String?
    @ObservationIgnored private var pageTask: Task<Void, Never>?   // owned here, not by a row
    @ObservationIgnored private var generation = 0
    private var isAtEnd = false

    private func load(after cursor: String?, generation: Int) async {
        defer { if generation == self.generation { pageTask = nil } }
        do {
            let page = try await service.fetchReviews(tourID: tourID, minimumRating: minimumRating, cursor: cursor)
            guard generation == self.generation else { return }   // a reload or a new filter took over
            reviews = cursor == nil ? page.reviews : reviews + page.reviews
            self.cursor = page.nextCursor
            isAtEnd = page.nextCursor == nil
            matchingCount = page.matchingCount
            summary = page.summary
            phase = .loaded
        } catch is CancellationError {
            // superseded: not an error
        } catch {
            guard generation == self.generation else { return }
            if phase == .loaded {
                pageError = error.localizedDescription
            } else {
                phase = .failed(error.localizedDescription)
            }
        }
    }
}
```

In the view, the filter goes in the toolbar, and the task reloads when the filter changes:

```swift
    var body: some View {
        NavigationStack {
            content
                .navigationTitle("Berlin Wall walk")
                .toolbar { RatingFilter(minimumRating: $viewModel.minimumRating) }
                .task(id: viewModel.minimumRating) { await viewModel.reload() }   // runs on appear, then on every change
        }
```

Two new cases go before `case .loaded:`, and the header uses the server's numbers:

```swift
        case .loaded where viewModel.reviews.isEmpty && viewModel.minimumRating != nil:
            ContentUnavailableView {
                Label("No reviews with \(viewModel.minimumRating ?? 0) stars or more", systemImage: "star.slash")
            } actions: {
                Button("Show all reviews") { viewModel.minimumRating = nil }
            }
        case .loaded where viewModel.reviews.isEmpty:
            ContentUnavailableView("No reviews yet", systemImage: "star.bubble")
```

```swift
                } header: {
                    RatingSummary(summary: viewModel.summary, minimumRating: viewModel.minimumRating,
                                  matchingCount: viewModel.matchingCount)
                }
```

```swift
}

struct RatingFilter: View {
    @Binding var minimumRating: Int?

    var body: some View {
        Menu {
            Picker("Minimum rating", selection: $minimumRating) {
                Text("All ratings").tag(Int?.none)
                ForEach([5, 4, 3, 2], id: \.self) { stars in
                    Text(stars == 5 ? "5 stars" : "\(stars) stars or more").tag(Optional(stars))
                }
            }
        } label: {
            Label("Filter", systemImage: minimumRating == nil
                  ? "line.3.horizontal.decrease.circle" : "line.3.horizontal.decrease.circle.fill")
        }
    }
}

struct RatingSummary: View {
    let summary: ReviewSummary?
    let minimumRating: Int?
    let matchingCount: Int

    var body: some View {
        VStack(alignment: .leading, spacing: 2) {
            if let summary {
                HStack {
                    Image(systemName: "star.fill")
                        .foregroundStyle(.yellow)
                    Text(summary.averageRating, format: .number.precision(.fractionLength(1)))
                        .font(.title2.bold())
                    Text("· \(summary.totalCount) reviews")
                }
                .accessibilityElement(children: .combine)
            }
            if let minimumRating {
                Text("Showing \(matchingCount) with \(minimumRating) stars or more")
                    .font(.footnote)
            }
        }
        .textCase(nil)
```

On the simulator, choosing "4 stars or more" sends `GET /v2/tours/berlin-wall-walk/reviews?min_rating=4&cursor=-`,
the header still says 3.9 · 30 reviews with "Showing 22 with 4 stars or more" under it, and scrolling loads two
more pages with that filter's cursors, then stops.
:::

## Part 3 — test it

> "Good. Write a few tests for the paging."

::: Now write the tests
The fake is an `actor`, so it's `Sendable` and can record requests safely. It pages like the server, with a
small page size, and it can fail once or be slow for one filter. That's all you need for the hard cases: two
triggers, the last page, a failed page, a new filter and a stale response.

```swift
import Foundation
import Testing
import ReviewsService
@testable import TourReviews

/// Serves `reviews` in pages of `pageSize`, filtered like the server. The cursor is the next offset.
private actor FakeReviews: ReviewsFetching {
    struct Request: Equatable { let minimumRating: Int?; let cursor: String? }
    struct Offline: LocalizedError { var errorDescription: String? { "Offline" } }

    private(set) var requests: [Request] = []
    var failingCursors: Set<String> = []
    var delays: [Int?: Duration] = [:]     // per filter: lets an old request finish after a new one

    let reviews: [Review]
    let pageSize: Int

    init(_ reviews: [Review], pageSize: Int = 2) {
        self.reviews = reviews
        self.pageSize = pageSize
    }

    func failOnce(at cursor: String) { failingCursors.insert(cursor) }
    func delay(_ duration: Duration, for minimumRating: Int?) { delays[minimumRating] = duration }

    func fetchReviews(tourID: String, minimumRating: Int?, cursor: String?) async throws -> ReviewCursorPage {
        requests.append(Request(minimumRating: minimumRating, cursor: cursor))
        if let delay = delays[minimumRating] { try await Task.sleep(for: delay) }
        if let cursor, failingCursors.remove(cursor) != nil { throw Offline() }
        let matching = reviews.filter { $0.rating >= (minimumRating ?? 1) }
        let start = cursor.flatMap(Int.init) ?? 0
        let end = min(start + pageSize, matching.count)
        return ReviewCursorPage(reviews: Array(matching[start..<end]),
                                nextCursor: end < matching.count ? String(end) : nil,
                                matchingCount: matching.count,
                                summary: ReviewSummary(averageRating: 3.6, totalCount: reviews.count))
    }
}

private func review(_ id: Int, _ rating: Int) -> Review {
    Review(id: "r\(id)", author: "A", rating: rating, text: "", date: .now)
}

struct TourReviewsViewModelTests {
    let sample = [review(1, 5), review(2, 2), review(3, 4), review(4, 5), review(5, 1)]

    @Test func twoTriggersForOnePageSendOneRequest() async {
        let service = FakeReviews(sample)
        let viewModel = TourReviewsViewModel(tourID: "t", service: service)
        await viewModel.reload()

        async let first: Void = viewModel.loadNextPage()     // the footer appears twice
        async let second: Void = viewModel.loadNextPage()
        _ = await (first, second)

        #expect(viewModel.reviews.map(\.id) == ["r1", "r2", "r3", "r4"])
        #expect(await service.requests == [.init(minimumRating: nil, cursor: nil), .init(minimumRating: nil, cursor: "2")])
    }

    @Test func noRequestAfterTheLastPage() async {
        let service = FakeReviews(sample)
        let viewModel = TourReviewsViewModel(tourID: "t", service: service)
        await viewModel.reload()
        await viewModel.loadNextPage()
        await viewModel.loadNextPage()   // the last page: nextCursor is nil
        await viewModel.loadNextPage()   // must not ask again

        #expect(viewModel.reviews.count == 5)
        #expect(viewModel.hasMore == false)
        #expect(await service.requests.count == 3)
    }

    @Test func aFailedPageKeepsTheListAndRetries() async {
        let service = FakeReviews(sample)
        await service.failOnce(at: "2")
        let viewModel = TourReviewsViewModel(tourID: "t", service: service)
        await viewModel.reload()
        await viewModel.loadNextPage()

        #expect(viewModel.phase == .loaded)
        #expect(viewModel.reviews.map(\.id) == ["r1", "r2"])
        #expect(viewModel.pageError == "Offline")

        await viewModel.loadNextPage()   // Try again
        #expect(viewModel.reviews.map(\.id) == ["r1", "r2", "r3", "r4"])
        #expect(viewModel.pageError == nil)
    }

    @Test func aNewFilterStartsANewCursorChain() async {
        let service = FakeReviews(sample)
        let viewModel = TourReviewsViewModel(tourID: "t", service: service)
        await viewModel.reload()
        await viewModel.loadNextPage()

        viewModel.minimumRating = 4
        await viewModel.reload()

        #expect(viewModel.reviews.map(\.id) == ["r1", "r3"])
        #expect(viewModel.matchingCount == 3)
        #expect(await service.requests.last == .init(minimumRating: 4, cursor: nil))   // not cursor "4"
    }

    @Test func aSlowPageFromTheOldFilterIsDropped() async {
        let service = FakeReviews(sample)
        let viewModel = TourReviewsViewModel(tourID: "t", service: service)
        await viewModel.reload()
        await service.delay(.milliseconds(200), for: nil)
        let oldPage = Task { await viewModel.loadNextPage() }   // in flight for 200 ms
        await Task.yield()

        viewModel.minimumRating = 5
        await viewModel.reload()
        await oldPage.value

        #expect(viewModel.reviews.map(\.id) == ["r1", "r4"])
    }

    @Test func theAverageIsTheToursNotTheFilters() async {
        let viewModel = TourReviewsViewModel(tourID: "t", service: FakeReviews(sample))
        viewModel.minimumRating = 5
        await viewModel.reload()

        #expect(viewModel.summary == ReviewSummary(averageRating: 3.6, totalCount: 5))
    }
}
```

All six pass. Two of them prove the fixes are real. If you remove the join in `loadNextPage()`,
`twoTriggersForOnePageSendOneRequest` fails. If you remove the generation check and the cancel in `didSet`,
`aSlowPageFromTheOldFilterIsDropped` fails: the old filter's page lands in the 5-star list.
:::

::: What I'd ask next
- **"A review is deleted between page 1 and page 2."** With page numbers, everything moves up by one and a review
  is skipped. A cursor that points at the last item you saw (an ID and a date, not an offset) doesn't have this
  problem. The fake's cursor is an offset, so say what you'd ask the backend for.
- **"New reviews arrive while the user is scrolling."** Pull to refresh replaces the list from the top. Don't
  insert new items above the user's scroll position without telling them: show a "New reviews" button instead.
- **"Sort by most helpful, as well as by newest."** It's the same as the filter: the sort is part of the query, so
  a new sort starts a new cursor chain and a new generation.
- **"Cache the first page so the screen isn't empty on launch."** Show the cached page as stale, load the first
  page over it, and replace, don't merge. Keep the cache per filter, or only cache the unfiltered list.
- **"The list is 10,000 reviews long."** `List` is lazy, so rows are fine. The memory is in `reviews`. Say when
  you'd drop pages far above the screen, and why you probably wouldn't at this size.
:::
