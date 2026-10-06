---
title: 66 · Insert Interval
summary: Add one new range to a sorted list of separate ranges, joining it with any it overlaps, and keep the list sorted and separate.
group: Intervals
minutes: 25
sources:
- LeetCode 57 · Insert Interval | https://leetcode.com/problems/insert-interval/
- Swift standard library · ArraySlice | https://developer.apple.com/documentation/swift/arrayslice
---

*Medium · G*

You get a list of ranges `[start, end]`, sorted by start, where no two ranges overlap. You also get one new range. Put the new range into the list, joining it with every range it overlaps — ranges that merely touch, like `[1, 2]` and `[2, 3]`, count as overlapping — and return the result, still sorted and with no overlaps.

| Ranges | New | Answer |
|---|---|---|
| `[[1, 3], [6, 8], [10, 12]]` | `[7, 11]` | `[[1, 3], [6, 12]]` — swallows `[6, 8]` and `[10, 12]` |
| `[]` | `[4, 6]` | `[[4, 6]]` |
| `[[2, 4], [8, 9]]` | `[5, 6]` | `[[2, 4], [5, 6], [8, 9]]` — fits in a gap, nothing joins |

Constraints that matter: up to 10,000 ranges, each with start ≤ end, values from 0 to 100,000. The list is already sorted, so there is no need to sort again: the target is one pass, O(n).

::: Starter code and tests
In an Xcode test target:

```swift
import Testing

struct InsertIntervalTests {

    @Test(arguments: [
        ([[1, 3], [6, 8], [10, 12]], [7, 11], [[1, 3], [6, 12]]),
        ([], [4, 6], [[4, 6]]),
        ([[2, 4], [8, 9]], [5, 6], [[2, 4], [5, 6], [8, 9]]),
    ])
    func insertsAndJoinsWhatOverlaps(intervals: [[Int]], newInterval: [Int], expected: [[Int]]) {
        #expect(insert(intervals, newInterval) == expected)
    }

    // MARK: - Privates
    private func insert(_ intervals: [[Int]], _ newInterval: [Int]) -> [[Int]] {
        []
    }
}
```

In a playground:

```swift
func insert(_ intervals: [[Int]], _ newInterval: [Int]) -> [[Int]] {
    [] // your solution
}

let cases: [([[Int]], [Int], [[Int]])] = [
    ([[1, 3], [6, 8], [10, 12]], [7, 11], [[1, 3], [6, 12]]),
    ([], [4, 6], [[4, 6]]),
    ([[2, 4], [8, 9]], [5, 6], [[2, 4], [5, 6], [8, 9]]),
]
for (intervals, newInterval, expected) in cases {
    let got = insert(intervals, newInterval)
    print(got == expected ? "PASS" : "FAIL", intervals, "+", newInterval, "→", got, "expected", expected)
}
```
:::

::: Pattern and cue
**Interval sweep over an already sorted list.** The cue is a *sorted list of non-overlapping ranges* plus *"insert"* and *"merge if needed"*. Because the list is sorted, it splits into three runs in order: ranges entirely before the new one, ranges that overlap it, and ranges entirely after it.
:::

::: Approach
Walk the list once, in three stages. First, copy over every range that **ends before the new range starts** — those can't touch it. Second, while the next range **starts no later than the new range ends**, it overlaps: stretch the new range to cover it (the smaller of the two starts, the larger of the two ends) and move on. Add the stretched new range to the result. Third, copy over everything that's left; all of it starts after the new range ends.

Time O(n): each range is looked at once. Space O(n) for the result (O(1) besides it).
:::

::: Swift solution
```swift
func insert(_ intervals: [[Int]], _ newInterval: [Int]) -> [[Int]] {
    var result: [[Int]] = []
    var start = newInterval[0], end = newInterval[1]
    var i = 0

    while i < intervals.count && intervals[i][1] < start {      // wholly before
        result.append(intervals[i]); i += 1
    }
    while i < intervals.count && intervals[i][0] <= end {       // overlaps or touches: absorb
        start = min(start, intervals[i][0])
        end = max(end, intervals[i][1])
        i += 1
    }
    result.append([start, end])
    result.append(contentsOf: intervals[i...])                  // wholly after
    return result
}
```

The two comparisons carry the touching rule: `< start` in the first loop and `<= end` in the second both treat a shared endpoint as an overlap. `intervals[i...]` is an empty slice when `i` has reached the end, so the last line needs no check.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, five more (touching on the right, new range before everything, after everything, swallowing every range, falling inside one range), and 3,000 random sorted lists checked against a brute force that adds the new range and merges overlapping pairs until none are left.
:::

::: Walk it through
**`[[1, 3], [6, 8], [10, 12]]` + `[7, 11]`**

| Stage | Range | Test | Action | New range |
|---|---|---|---|---|
| before | `[1, 3]` | ends 3 < 7 | copy | `[7, 11]` |
| before | `[6, 8]` | ends 8, not < 7 | stop stage 1 | `[7, 11]` |
| overlap | `[6, 8]` | starts 6 ≤ 11 | absorb | `[6, 11]` |
| overlap | `[10, 12]` | starts 10 ≤ 11 | absorb | `[6, 12]` |
| — | — | list ended | append `[6, 12]` | — |

Answer `[[1, 3], [6, 12]]`.

**`[[2, 4], [8, 9]]` + `[5, 6]`** — `[2, 4]` ends at 4 < 5, copied. `[8, 9]` ends after 5, so stage 1 stops; it starts at 8 > 6, so stage 2 absorbs nothing. Append `[5, 6]`, then copy `[8, 9]`.
:::

::: The Swift trap
**The bounds check has to come first, and it has to be in every loop.** `intervals[i][1] < start && i < intervals.count` reads like the same condition, but when `i` reaches the end Swift evaluates the subscript first and crashes with "Index out of range" — there's no reading past the end and getting lucky, as in C. `&&` only skips its right side when the left side is false, so `i < intervals.count` must be on the left. The empty-list example is where a missing check shows up first.
:::

::: What they ask next
- **"The list isn't sorted."** → Append the new range and run Merge Intervals: O(n log n) for the sort.
- **"Insert many ranges, one after another."** → Each array insert is O(n), because elements shift. A balanced search tree keyed by start makes each insert O(log n + k), k being how many ranges it swallows.
- **"Find the insert position with binary search."** → You can find where stage 2 starts in O(log n), but copying the result is still O(n), so the total doesn't improve unless you modify in place.
:::
