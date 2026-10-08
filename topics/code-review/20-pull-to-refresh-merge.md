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
Compiled and run with Swift 6.4: the buggy snippet compiles cleanly in both Swift 5 and Swift 6
mode (and misbehaves — real output below); the fix compiles in Swift 6 mode with zero warnings and
was run on the sample, edge cases and a 20,000-story timing*

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
1. **Data race on `stories`.** `fetchPage`'s completion runs on whatever queue the API picks —
   usually a background one — and mutates `stories` while the main thread reads it for the table.
   Swift 6 mode compiles this without a word (verified): nothing says the class or the closure
   belongs to an actor, so the compiler can't see two threads. Mark the view model `@MainActor`.
2. **Load-more in flight during a refresh puts the page in the middle.** `offset` is 4 when the
   request starts; the refresh grows the list to 6; the page is then inserted at index 4. Real
   output: `["D", "E", "F", "A", "X", "Y", "B", "C"]`. Cancel the load-more on refresh, and page by
   a cursor (the last story's id), not by an index.
3. **An edited story appears twice.** `contains(story)` compares the *whole* struct. The fresh D has
   99 likes, the old D has 0, so they're "different" and both are kept. Real output:
   `["D99", "E0", "F0", "A0", "B0", "C0", "D0"]`. Deduplicate by `id`.
4. **The `Set` attempt loses order.** A `Set` has no order, and Swift seeds its hashing randomly per
   process, so the order even changes between launches. Three runs of the same input printed
   `["A", "E", "F", "B", "C", "D"]`, `["F", "C", "E", "B", "A", "D"]`, `["A", "B", "D", "E", "C", "F"]`.
   Delete the comment too — dead code in a PR invites someone to "simplify" back to it.
5. **`isLoadingMore` can get stuck.** The callback has no error case, so a failed page either never
   calls back or can't say it failed — and load-more is then dead until the screen is rebuilt.
6. **Duplicates inside `fetched` survive.** `merged = fetched` keeps them as-is. Servers do send
   overlapping pages.
7. **O(n × m) merge.** `contains` scans the merged array for every old story. With 20,000 stories on
   screen and 50 fresh ones that took 0.93 s on my Mac — a visible hang on main.
8. **`Hashable` on the whole struct mixes up identity and equality.** Identity is "which story";
   equality is "same content". The feed needs `Identifiable`; `Equatable` is for "did it change?".
9. **Strong `self` in the completion** — the view model lives until the request ends.
10. **Nothing is testable.** `didRefresh` mixes the merge rule with the stored state. Pull the merge
    into a pure function and test it with the examples in the prompt.
:::

::: The idea behind it
Two words do the work here: *identity* and *equality*. Identity answers "is this the same story?"
— the server gives each one an `id` that never changes. Equality answers "does it look the same?"
— same title, same like count. A story can keep its identity while its content changes. The merge
must match on identity, then keep the newest content.

The second idea is cost. Checking "have I seen this already?" by scanning an array means looking at
every item, every time — *quadratic* work: double the stories, four times the time. A `Set` answers
the same question in roughly one step, because it files each value by its hash, a number computed
from it. So build a set of ids you've already placed, and the whole merge becomes one pass over each
list.

A `Set` alone can't be the answer, though. It forgets order. Keep the array for order and the set
for the "seen it?" question — two tools, each doing the one thing it's good at.

Think of a guest list at a door. You don't re-read the whole list for every arrival. You tick names
on a clipboard, and you seat people in the order they walk in.
:::

::: The version I'd ship
```swift
import Foundation

struct Story: Identifiable, Equatable, Sendable {
    let id: String
    var title: String
    var likes: Int
}

enum FeedMerge {
    /// `top` first, then the items of `bottom` whose id isn't already shown.
    /// Order inside each list is kept; on a clash the `top` copy wins. O(n + m).
    static func merging<Item: Identifiable>(top: [Item], bottom: [Item]) -> [Item] {
        var seen = Set<Item.ID>(minimumCapacity: top.count + bottom.count)
        var result: [Item] = []
        result.reserveCapacity(top.count + bottom.count)
        for item in top where seen.insert(item.id).inserted { result.append(item) }
        for item in bottom where seen.insert(item.id).inserted { result.append(item) }
        return result
    }
}

protocol FeedAPI: Sendable {
    func latest() async throws -> [Story]
    func page(after cursor: Story.ID) async throws -> [Story]
}

@MainActor
final class FeedViewModel {
    private(set) var stories: [Story] = []
    private let api: FeedAPI
    private var loadMoreTask: Task<Void, Never>?

    init(api: FeedAPI) { self.api = api }

    func refresh() async {
        loadMoreTask?.cancel()          // its cursor belongs to the list we're replacing
        loadMoreTask = nil
        guard let fresh = try? await api.latest() else { return }
        stories = FeedMerge.merging(top: fresh, bottom: stories)
    }

    func loadMore() {
        guard loadMoreTask == nil, let cursor = stories.last?.id else { return }
        loadMoreTask = Task {
            let page = try? await api.page(after: cursor)
            guard !Task.isCancelled else { return }   // a refresh owns the list now
            loadMoreTask = nil
            if let page { stories = FeedMerge.merging(top: stories, bottom: page) }
        }
    }
}
```

What the harness printed (a number in brackets is the like count of an edited story):

```text
sample:       D,E,F,A,B,C
edited D:     D(99),E,F,A,B,C
dup in fresh: E,D,A,B,C
nothing new:  A,B,C,D
first load:   A,B,C,D
race:         D(99),E,F
load more:    D(99),E,F,X,Y
quadratic:    20050 items, 0.933690041 seconds
set of ids:   20050 items, 0.004308208 seconds
```

`race` started a slow load-more, then refreshed: the stale page was dropped instead of landing in
the middle. The next load-more appended normally. The timing is 20,000 stories on screen plus 51
fetched, built with `-O` on my Mac — about 200 times faster, and the gap grows with the list.

Why each piece:

- **`Set<Item.ID>` of seen ids** — "already placed?" is one hash lookup, so the merge is one pass
  over each list: O(n + m) time.
- **`seen.insert(_:).inserted`** — inserts and answers "was it new?" in one call. Used on both lists,
  so duplicates inside the fresh page and inside the old list are dropped too.
- **`top` wins on a clash** — the fresh D replaces the old D in place at the top, with its new like
  count. For load-more I pass the current list as `top`, so a story already on screen is never
  moved down.
- **Generic over `Identifiable`** — the rule isn't about stories. The same function merges comments
  or messages, and it's a pure function, so the examples in the prompt become unit tests.
- **`@MainActor` and a stored `Task`** — every write to `stories` is on main, refresh cancels the
  load-more, and paging by cursor means a refresh can't shift the page's position.
:::

::: What I'd ask next
- *"How would you improve the efficiency?"* (Meta's follow-up) — Three levels. **The algorithm:**
  the set of ids above takes it from O(n × m) to O(n + m). **Memory and work:** the fresh page is
  small, so a set of just the fresh ids (O(m) memory) is enough for a refresh: `fresh +
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
- *"How would you test the race?"* — A fake API whose page call is slower than the refresh call, as
  the harness does. Assert the page didn't land and that a later load-more still works.
:::
