---
title: 68 · Non-overlapping Intervals
summary: Remove as few ranges as possible from a list so that the ones left never overlap, and return how many you removed.
group: Intervals
minutes: 25
sources:
- LeetCode 435 · Non-overlapping Intervals | https://leetcode.com/problems/non-overlapping-intervals/
- Wikipedia · Interval scheduling | https://en.wikipedia.org/wiki/Interval_scheduling
---

*Medium · G*

You get a list of ranges `[start, end]`, each with start < end. Remove the fewest ranges you can so that no two of the remaining ones overlap, and return how many you removed. Here ranges that only **touch** — one ends at 3, the next starts at 3 — do **not** overlap.

| Ranges | Answer |
|---|---|
| `[[1, 3], [2, 4], [3, 5], [1, 5]]` | `2` — keep `[1, 3]` and `[3, 5]` |
| `[[1, 2], [2, 3]]` | `0` — they only touch |
| `[[1, 2], [1, 2], [1, 2]]` | `2` — keep one of the three copies |

Constraints that matter: up to 100,000 ranges, values from −50,000 to 50,000. Trying every subset is exponential; the target is O(n log n).

::: Starter code and tests
In an Xcode test target:

```swift
import Testing

struct NonOverlappingIntervalsTests {

    @Test(arguments: [
        ([[1, 3], [2, 4], [3, 5], [1, 5]], 2),
        ([[1, 2], [2, 3]], 0),
        ([[1, 2], [1, 2], [1, 2]], 2),
    ])
    func countsTheFewestRemovalsThatLeaveNoOverlap(intervals: [[Int]], expected: Int) {
        #expect(eraseOverlapIntervals(intervals) == expected)
    }

    // MARK: - Privates
    private func eraseOverlapIntervals(_ intervals: [[Int]]) -> Int {
        0
    }
}
```

In a playground:

```swift
func eraseOverlapIntervals(_ intervals: [[Int]]) -> Int {
    0 // your solution
}

let cases: [([[Int]], Int)] = [
    ([[1, 3], [2, 4], [3, 5], [1, 5]], 2),
    ([[1, 2], [2, 3]], 0),
    ([[1, 2], [1, 2], [1, 2]], 2),
]
for (intervals, expected) in cases {
    let got = eraseOverlapIntervals(intervals)
    print(got == expected ? "PASS" : "FAIL", intervals, "→", got, "expected", expected)
}
```
:::

::: Pattern and cue
**Sort by end, then keep greedily.** The cue is *ranges* plus *"fewest to remove so none overlap"* — the same as *"most you can keep"*. That's the classic interval-scheduling problem: among the ranges that still fit, always keep the one that **finishes first**.
:::

::: Approach
Removing the fewest is the same as keeping the most, so think about keeping. Sort the ranges by where they end. Walk through them, remembering the end of the last range you kept. If the next range starts at or after that end, it fits: keep it, and its end becomes the new boundary. If it starts before, it clashes with something you kept, so remove it and count one. Why is keeping the earliest-finishing range always safe? Any plan that keeps a different range in that slot could swap it for the one that finishes earlier, and that swap never causes a new clash — it only leaves more room after it.

Time O(n log n) for the sort; the walk is O(n). Space O(n) for the sorted copy.
:::

::: Swift solution
```swift
func eraseOverlapIntervals(_ intervals: [[Int]]) -> Int {
    let byEnd = intervals.sorted { $0[1] < $1[1] }
    var removed = 0
    var lastEnd = Int.min
    for interval in byEnd {
        if interval[0] >= lastEnd {
            lastEnd = interval[1]                // keep it: it ends earliest among what fits
        } else {
            removed += 1                         // clashes with a kept one that ends sooner
        }
    }
    return removed
}
```

`interval[0] >= lastEnd` is where the touching rule lives: `>=` lets a range start exactly where the last kept one ended. `Int.min` as the starting boundary means the first range always fits, whatever its values; it's only compared, never added to, so it can't overflow.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, three more (a single range, one long range covering three short ones, negative values), and 2,000 random lists of up to eight ranges checked against a brute force that tries every subset and keeps the largest one with no overlaps.
:::

::: Walk it through
**`[[1, 3], [2, 4], [3, 5], [1, 5]]`** — sorted by end: `[1, 3]`, `[2, 4]`, then `[3, 5]` and `[1, 5]` (both end at 5, in either order).

| Range | Last kept end | Fits? | Removed |
|---|---|---|---|
| `[1, 3]` | none | yes, keep | 0 |
| `[2, 4]` | 3 | 2 < 3: no | 1 |
| `[3, 5]` | 3 | 3 ≥ 3: yes, keep | 1 |
| `[1, 5]` | 5 | 1 < 5: no | 2 |

Answer 2. Had `[1, 5]` come before `[3, 5]`, it would be removed against the boundary 3 instead, and `[3, 5]` kept: still 2.

**`[[1, 2], [1, 2], [1, 2]]`** — the first copy is kept with boundary 2; the other two start at 1 < 2, so both are removed. Answer 2.
:::

::: The Swift trap
**`intervals.sort { … }` doesn't compile — and the fix you reach for decides the memory.** Function parameters in Swift are constants, so the in-place `sort` that you'd write in Java or Python fails with "cannot use mutating member on immutable value". There are two fixes, and they're not the same. `let byEnd = intervals.sorted { … }` returns a new sorted array: clear, and O(n) extra memory. `var intervals = intervals` followed by `intervals.sort { … }` looks like it sorts in place, but the first write triggers copy-on-write, because the caller's array still shares the storage — so it's also an O(n) copy. With 100,000 ranges neither matters; just know that in Swift you can't sort a caller's array without being handed it `inout`.
:::

::: What they ask next
- **"Why sort by end and not by start?"** → Sorting by start can keep a long early range that blocks several short ones: `[1, 100]`, `[2, 3]`, `[4, 5]`. By end, `[2, 3]` and `[4, 5]` are kept and only the long one goes. Sorting by start works too, but then on a clash you must keep whichever of the two ends sooner.
- **"Return the ranges to remove, not the count."** → Collect the else-branch ranges instead of counting them.
- **"Ranges carry a value; keep the most valuable set."** → Weighted interval scheduling: greedy fails, it needs dynamic programming over ranges sorted by end, with a binary search for the last compatible one. O(n log n).
:::
