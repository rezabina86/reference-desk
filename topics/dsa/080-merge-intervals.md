---
title: 67 · Merge Intervals
summary: Given ranges in any order, join every group that overlaps into one range and return the result sorted.
group: Intervals
minutes: 25
sources:
- LeetCode 56 · Merge Intervals | https://leetcode.com/problems/merge-intervals/
- Swift standard library · Array.last | https://developer.apple.com/documentation/swift/array/last
---

*Medium · G*

You get a list of ranges `[start, end]` in no particular order. Wherever ranges overlap — including when one ends exactly where another starts — replace them with one range that covers them all. Return the ranges that remain, sorted by start.

| Ranges | Answer |
|---|---|
| `[[8, 10], [1, 4], [3, 5], [12, 13]]` | `[[1, 5], [8, 10], [12, 13]]` |
| `[[1, 2], [2, 3]]` | `[[1, 3]]` — touching counts as overlapping |
| `[[5, 5]]` | `[[5, 5]]` — one range, a single point |

Constraints that matter: up to 10,000 ranges, each with start ≤ end, values up to 10,000. Comparing every pair is O(n²) and gets complicated as merged ranges grow; the target is O(n log n), the cost of one sort.

::: Starter code and tests
In an Xcode test target:

```swift
import Testing

struct MergeIntervalsTests {

    @Test(arguments: [
        ([[8, 10], [1, 4], [3, 5], [12, 13]], [[1, 5], [8, 10], [12, 13]]),
        ([[1, 2], [2, 3]], [[1, 3]]),
        ([[5, 5]], [[5, 5]]),
    ])
    func joinsEveryOverlappingGroup(intervals: [[Int]], expected: [[Int]]) {
        #expect(merge(intervals) == expected)
    }

    // MARK: - Privates
    private func merge(_ intervals: [[Int]]) -> [[Int]] {
        []
    }
}
```

In a playground:

```swift
func merge(_ intervals: [[Int]]) -> [[Int]] {
    [] // your solution
}

let cases: [([[Int]], [[Int]])] = [
    ([[8, 10], [1, 4], [3, 5], [12, 13]], [[1, 5], [8, 10], [12, 13]]),
    ([[1, 2], [2, 3]], [[1, 3]]),
    ([[5, 5]], [[5, 5]]),
]
for (intervals, expected) in cases {
    let got = merge(intervals)
    print(got == expected ? "PASS" : "FAIL", intervals, "→", got, "expected", expected)
}
```
:::

::: Pattern and cue
**Sort by start, then sweep.** The cue is a list of *ranges* in *no order* plus *"merge the overlapping ones"*. Once ranges are sorted by start, a range can only overlap the block you're currently building, never one you finished earlier.
:::

::: Approach
Sort the ranges by where they start. Take the first one as the block you're building. For each next range, compare its start with the end of the current block: if it starts before or exactly at that end, it overlaps, so stretch the block's end to whichever end is later. If it starts after the block's end, there's a gap, so the block is finished; the new range becomes the block you're building. At the end, the finished blocks are the answer, already in order.

Time O(n log n) for the sort; the sweep is O(n). Space O(n) for the sorted copy and the result.
:::

::: Swift solution
```swift
func merge(_ intervals: [[Int]]) -> [[Int]] {
    let sorted = intervals.sorted { $0[0] < $1[0] }
    var merged: [[Int]] = []
    for interval in sorted {
        if let last = merged.last, interval[0] <= last[1] {
            merged[merged.count - 1][1] = max(last[1], interval[1])   // extend the open one
        } else {
            merged.append(interval)
        }
    }
    return merged
}
```

`max(last[1], interval[1])`, not just `interval[1]`: a range can sit completely inside the block, like `[2, 3]` inside `[1, 10]`, and taking its end would shrink the block.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, three more (one range inside another, two identical ranges, two separate ranges given in reverse), and 3,000 random lists checked against a brute force that merges any overlapping pair until none are left.
:::

::: Walk it through
**`[[8, 10], [1, 4], [3, 5], [12, 13]]`** — sorted: `[1, 4]`, `[3, 5]`, `[8, 10]`, `[12, 13]`.

| Range | Current block | Test | Result so far |
|---|---|---|---|
| `[1, 4]` | none | — | `[1, 4]` |
| `[3, 5]` | `[1, 4]` | 3 ≤ 4: overlap | `[1, 5]` |
| `[8, 10]` | `[1, 5]` | 8 > 5: gap | `[1, 5]`, `[8, 10]` |
| `[12, 13]` | `[8, 10]` | 12 > 10: gap | `[1, 5]`, `[8, 10]`, `[12, 13]` |

**`[[1, 2], [2, 3]]`** — 2 ≤ 2, so the second range extends the first: `[[1, 3]]`. With `<` instead of `<=` the answer would wrongly stay as two ranges.
:::

::: The Swift trap
**`merged.last![1] = …` doesn't compile.** It's the line everyone writes first, because it reads exactly like the idea. But `last` is a get-only property that hands back a copy of the final element, so the compiler stops with "cannot assign through subscript: 'last' is a get-only property". Read through `last` (the `if let last` above is fine), and write through an index: `merged[merged.count - 1][1] = …`.
:::

::: What they ask next
- **"Can you do it in place, without the extra array?"** → Sort `var intervals = intervals` in place and keep a write index: overlap extends `intervals[write]`, a gap copies the range to `intervals[write + 1]`. The result is `intervals[...write]`. O(1) extra space apart from the sort.
- **"Ranges keep arriving one at a time."** → Keep the merged list sorted and insert each new range as in Insert Interval, or use a tree keyed by start.
- **"Return the gaps instead — the free time."** → Merge, then the gaps are `[block[i][1], block[i + 1][0]]` between consecutive blocks.
:::
