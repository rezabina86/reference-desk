---
title: 20 · The pull-to-refresh merge
summary: Merge freshly fetched stories on top of the ones on screen — no duplicates, order kept — review a candidate's version, then make it fast.
minutes: 25
group: Review, then extend
sources:
- LeetCode Discuss · Meta iOS — stories [A,B,C,D] + fetched [D,E,F] must show [D,E,F,A,B,C]; "Follow up: How would you improve the efficiency?" | https://leetcode.com/discuss/interview-question/511373/
- Apple · UITableViewDiffableDataSource — apply a snapshot of identifiers instead of reloading everything | https://developer.apple.com/documentation/uikit/uitableviewdiffabledatasource
---

*Shape: review, then extend · Reported: Meta — current stories `[A,B,C,D]`, refresh fetches
`[D,E,F]`, the screen must show `[D,E,F,A,B,C]`, then "how would you improve the efficiency?" ·
Verified: snippet's bugs reproduced and the fix tested, Swift 6.4*

> "The feed shows stories A, B, C, D. The user pulls to refresh and the server returns D, E, F. We
> want D, E, F, A, B, C — new on top, no duplicates, order kept. Here's what a candidate wrote.
> Review it. Then: how would you make it more efficient?"

```swift
import Foundation

struct Story: Hashable {
    let id: String
    var title: String
    var likes: Int
}

final class FeedViewModel {
    private(set) var stories: [Story] = []
    private var isLoadingMore = false
    private let api: FeedAPI

    init(api: FeedAPI) { self.api = api }

    // First attempt, left in by the candidate:
    // stories = Array(Set(fetched + stories))

    func didRefresh(with fetched: [Story]) {
        var merged = fetched
        for story in stories {
            if !merged.contains(story) {
                merged.append(story)
            }
        }
        stories = merged
    }

    func loadMore() {
        guard !isLoadingMore else { return }
        isLoadingMore = true
        let offset = stories.count
        api.fetchPage(after: offset) { page in
            self.stories.insert(contentsOf: page, at: offset)
            self.isLoadingMore = false
        }
    }
}

protocol FeedAPI {
    func fetchPage(after offset: Int, completion: @escaping ([Story]) -> Void)
}
```

::: A hint, if you're stuck
- Run the sample in your head, then run it again with one change: the fresh D now has 99 likes.
- What does "the same story" mean here — same everything, or same something?
- What did the commented-out `Set` line do to the order?
- `loadMore` remembers `offset`. What happens to that number if a refresh lands while the page is
  still loading?
:::

::: The key — what I expect a senior to find
1. **`insert(contentsOf:at: offset)` can crash.** `offset` is read when the request starts. If the
   list is shorter when the page arrives, the index is past the end and the app traps. A refresh
   that collapses duplicates is enough: `[A,B,A,B]`, load-more at offset 4, refresh shrinks it to
   `[A,B]`, page arrives — *Array replace: subrange extends past the end*. Append, never insert at
   a remembered index.
2. **Data race on `stories`.** `fetchPage`'s completion runs on whatever queue the API picks —
   usually a background one — and mutates `stories` while the main thread reads it for the table.
   Swift 6 mode compiles this without a word: nothing says the class or the closure belongs to an
   actor, so the compiler can't see two threads. Mark the view model `@MainActor` and hop back to
   it in the callback.
3. **Load-more in flight during a refresh puts the page in the middle.** `offset` is 4 when the
   request starts; the refresh grows the list to 6; the page then lands at index 4:
   `["D", "E", "F", "A", "X", "Y", "B", "C"]`. A refresh has to make an in-flight page stale.
4. **An edited story appears twice.** `contains(story)` compares the *whole* struct. The fresh D has
   99 likes, the old D has 0, so both are kept: `["D99", "E0", "F0", "A0", "B0", "C0", "D0"]`.
   Deduplicate by `id`.
5. **Load-more never deduplicates.** Paging by offset after new stories landed on top means the
   next page starts with stories already on screen, and they're added again.
6. **The `Set` attempt loses order.** A `Set` has no order, and Swift seeds its hashing randomly per
   process, so the order even changes between launches. Delete the comment too — dead code in a PR
   invites someone to "simplify" back to it.
7. **`isLoadingMore` can get stuck, and errors can't be reported.** The callback has no error case,
   so a failed page either never calls back or can't say it failed — and load-more is dead until
   the screen is rebuilt. A refresh doesn't reset it either.
8. **Duplicates inside `fetched` survive.** `merged = fetched` keeps them as they are. Servers do
   send overlapping pages.
9. **Nothing tells the view.** `stories` changes with no callback, no observation, no
   notification. The table only finds out if something else makes it reload.
10. **Nothing is testable.** `didRefresh` mixes the merge rule with the stored state. Pull the merge
    into a pure function and test it with the examples in the prompt.
11. **O(n²) merge.** `contains` scans `merged`, which grows to n + m, once for every old story —
    about n²/2 comparisons. With 20,000 stories on screen took about 0.7 s on my Mac (`-O`): a
    visible hang on the main thread.
12. **`Hashable` on the whole struct mixes up identity and equality.** Identity is "which story";
    equality is "same content". The feed needs `Identifiable`; `Equatable` is for "did it change?".
13. **Strong `self` in the completion.** Not a leak — the closure isn't stored by the view model —
    but it keeps the view model alive until the request ends. `[weak self]` is the tidier default.
:::

::: The idea behind it
Two words do the work here: *identity* and *equality*. Identity answers "is this the same story?"
— the server gives each one an `id` that never changes. Equality answers "does it look the same?"
— same title, same like count. A story can keep its identity while its content changes. The merge
must match on identity, then keep the newest content.

The second idea is cost. Checking "have I seen this already?" by scanning an array means looking at
every item, every time — *quadratic* work: double the stories, four times the time. A `Set` answers
the same question in roughly one step, because it files each value by its hash, a number computed
from it. So build a set of ids you've already placed, and the whole merge becomes one pass.

A `Set` alone can't be the answer, though. It forgets order. Keep the array for order and the set
for the "seen it?" question — two tools, each doing the one thing it's good at.

Think of a guest list at a door. You don't re-read the whole list for every arrival. You tick names
on a clipboard, and you seat people in the order they walk in.
:::

::: The fix
Same class, same methods, same completion handler. The callback gains a `Result`, and a counter
marks which list a page belongs to.

```swift
import Foundation

struct Story: Identifiable, Equatable {                 // key 12: identity is the id
    let id: String
    var title: String
    var likes: Int
}

@MainActor                                               // key 2
final class FeedViewModel {
    private(set) var stories: [Story] = []
    private var isLoadingMore = false
    private var generation = 0                           // key 3: which list a page belongs to
    private let api: FeedAPI

    init(api: FeedAPI) { self.api = api }

    func didRefresh(with fetched: [Story]) {
        generation += 1                                  // key 3: a page in flight is now stale
        isLoadingMore = false
        stories = Self.merging(top: fetched, bottom: stories)
    }

    func loadMore() {
        guard !isLoadingMore else { return }
        isLoadingMore = true
        let offset = stories.count
        let generation = generation
        api.fetchPage(after: offset) { [weak self] result in   // key 13
            Task { @MainActor in                         // key 2: back on main
                guard let self, generation == self.generation else { return }
                self.isLoadingMore = false               // key 7: reset on failure too
                if case .success(let page) = result {    // key 1, 5: append and dedupe, no insert
                    self.stories = Self.merging(top: self.stories, bottom: page)
                }
            }
        }
    }

    /// `top` first, then the stories of `bottom` not already there. On a clash `top` wins.
    static func merging(top: [Story], bottom: [Story]) -> [Story] {   // key 10
        var seen = Set<Story.ID>()                       // key 4, 8, 11: one hash lookup per story
        return (top + bottom).filter { seen.insert($0.id).inserted }
    }
}

protocol FeedAPI {
    func fetchPage(after offset: Int,
                   completion: @escaping @Sendable (Result<[Story], Error>) -> Void)   // key 7
}
```

Why each piece:

- **`seen.insert(_:).inserted`** — inserts and answers "was it new?" in one call, so one pass over
  both lists drops every duplicate, the old ones and the ones inside the page.
- **`top` wins on a clash** — the fresh D replaces the old D at the top, with 99 likes. For
  load-more the current list is `top`, so a story already on screen never moves down.
- **`generation`** — a refresh bumps it; a page that comes back with an older number is dropped.
  That's the smallest change that keeps the completion-handler API. A cursor is better (below).
- **Merged, not inserted** — load-more goes through the same merge, so there is no index to go
  stale and nothing to crash.

The merge with the prompt's sample, an edited story and 20,000 stories gave the right lists; the
set of ids took the 20,000-story merge from about 0.7 s to 3 ms.

**Said out loud, not coded:** page by a cursor (the last story's id) instead of an offset; make the
view model `@Observable` (or give it a change callback) so the view hears about changes; a generic
merge over `Identifiable` if comments or messages need it too; an `async` API with a stored `Task`
that refresh cancels.
:::

::: Now write the tests
> "Good. Now show me the tests — for the merge, and for the race you found."

**What I'd test, and why**

1. **The prompt's example.** `[A,B,C,D]` plus `[D,E,F]` gives `[D,E,F,A,B,C]`. The merge is a pure
   function — same input, same output, no state — so the interviewer's example becomes a test as
   written.
2. **An edited story appears once, with its new content.** The fresh D has 99 likes; the result has
   one D, on top, with 99. That's the duplicate bug from the review.
3. **A refresh drops an in-flight load-more.** The old page arrives after the refresh and must not
   land. That's the page-in-the-middle bug.
4. **Load-more after a refresh still works, without duplicates.** Regression for the stuck
   `isLoadingMore`: the next request goes out, and an overlapping offset page only adds what's new.

I wouldn't time the merge in a unit test. Timing on a shared CI machine is noisy, so it's a
benchmark to run by hand, not a pass/fail check.

**The seam.** The merge needs none: it's a pure function. The view model already takes its
`FeedAPI` through `init`, so the tests pass a *fake* — a small stand-in that records each offset
and holds the completion until the test answers. That lets the test refresh *while* a page is in
flight, every time, with no sleeps.

```swift
import Testing

func story(_ id: String, likes: Int = 0) -> Story {
    Story(id: id, title: "Story \(id)", likes: likes)
}

/// A fake server: records each page request and holds its completion until the test answers.
final class FakeFeedAPI: FeedAPI {
    private(set) var offsets: [Int] = []
    private var completions: [@Sendable (Result<[Story], Error>) -> Void] = []

    func fetchPage(after offset: Int,
                   completion: @escaping @Sendable (Result<[Story], Error>) -> Void) {
        offsets.append(offset)
        completions.append(completion)
    }

    func answer(_ request: Int, with page: [Story]) { completions[request](.success(page)) }
}

/// Gives the view model's main-actor task a turn, up to a fixed number of times. No clocks.
@MainActor
func waitUntil(maxYields: Int = 100, _ done: () -> Bool) async {
    for _ in 0..<maxYields where !done() { await Task.yield() }
}

@MainActor
struct FeedViewModelTests {

    @Test
    func freshStoriesGoOnTopWithoutDuplicates() {
        let merged = FeedViewModel.merging(top: ["D", "E", "F"].map { story($0) },
                                           bottom: ["A", "B", "C", "D"].map { story($0) })

        #expect(merged.map(\.id) == ["D", "E", "F", "A", "B", "C"])
    }

    @Test
    func anEditedStoryAppearsOnceWithItsNewContent() {
        let merged = FeedViewModel.merging(top: [story("D", likes: 99)],
                                           bottom: [story("A"), story("D", likes: 0)])

        #expect(merged == [story("D", likes: 99), story("A")])
    }

    @Test
    func aRefreshDropsAnInFlightLoadMore() async {
        // Given A, B, C, D on screen and a page still loading
        let api = FakeFeedAPI()
        let viewModel = FeedViewModel(api: api)
        viewModel.didRefresh(with: ["A", "B", "C", "D"].map { story($0) })
        viewModel.loadMore()

        // When a refresh lands first, then the old page arrives
        viewModel.didRefresh(with: ["D", "E", "F"].map { story($0) })
        api.answer(0, with: [story("X"), story("Y")])
        await waitUntil(maxYields: 20) { false }

        // Then the stale page never lands in the middle
        #expect(viewModel.stories.map(\.id) == ["D", "E", "F", "A", "B", "C"])
    }

    @Test
    func loadMoreAfterARefreshAppendsWithoutDuplicates() async {
        // Given a refresh that dropped an in-flight load-more
        let api = FakeFeedAPI()
        let viewModel = FeedViewModel(api: api)
        viewModel.didRefresh(with: ["A", "B"].map { story($0) })
        viewModel.loadMore()
        viewModel.didRefresh(with: [story("C")])

        // When the user scrolls down again and the offset page overlaps what's shown
        viewModel.loadMore()
        api.answer(1, with: [story("B"), story("X")])
        await waitUntil { viewModel.stories.count == 4 }

        // Then the second request went out, and only the new story was appended
        #expect(api.offsets == [2, 3])
        #expect(viewModel.stories.map(\.id) == ["C", "A", "B", "X"])
    }
}
```

`waitUntil` gives the view model's main-actor task a few turns after the fake answers. It's
bounded by a count of yields, not a time, so a slow machine can't make it flaky. In the third test
nothing should change, so it just spends its turns.

Ran with Swift 6.4: 4 tests, all passed.
:::

::: What I'd ask next
- *"How would you improve the efficiency?"* (Meta's follow-up) — Three levels. **The algorithm:**
  the set of ids takes it from O(n²) to O(n + m). **Memory and work:** the fresh page is small, so
  a set of just the fresh ids (O(m) memory) is enough for a refresh: `fresh +
  stories.filter { !freshIDs.contains($0.id) }`. **The UI:** don't call `reloadData()` — apply a
  diffable data source snapshot of ids, so only the three new rows animate in and an edited story
  is reconfigured in place. And ask the server for `?since=<newest id>`, so it only sends what's new.
- *"The list is 100,000 items. Is O(n) per refresh still fine?"* — Keep an `[ID: Int]` index of
  positions alongside the array, or store a page window rather than the whole history. Above a few
  thousand, also ask whether the screen should hold everything at all.
- *"Should an old story that the server deleted disappear on refresh?"* — Not from this merge: a
  refresh page only says what's new. Deletions need a separate signal (a tombstone list or a full
  resync), or the merge will quietly keep stale items.
- *"Why `Equatable` at all, if you match on `id`?"* — For change detection: the diffable snapshot or
  SwiftUI's `ForEach` uses identity to know which row it is and equality to know whether to redraw it.
- *"In SwiftUI, what goes wrong if two rows share an id?"* — `List` and `ForEach` track rows by
  `id`. Two rows with the same id confuse the diff: rows animate wrongly, state sticks to the wrong
  row, and SwiftUI logs a warning. That's one more reason the merge must never keep a duplicate id.
:::
