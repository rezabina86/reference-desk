---
title: 4 · Longest Consecutive Sequence
summary: Given an unsorted list of whole numbers, find how long the longest unbroken run of consecutive values is.
minutes: 25
sources:
- LeetCode 128 · Longest Consecutive Sequence | https://leetcode.com/problems/longest-consecutive-sequence/
- Swift standard library · Set | https://developer.apple.com/documentation/swift/set
- The Swift Programming Language · Overflow Operators | https://docs.swift.org/swift-book/documentation/the-swift-programming-language/advancedoperators/#Overflow-Operators
---

*Medium · G*

You get an unsorted array of integers. A run is a set of values that follow each other with no gap — 7, 8, 9, 10 — wherever they sit in the array. Return the length of the longest run. Repeated values count once. The interviewer wants it in O(n) time, which rules out sorting first.

| Numbers | Answer | Why |
|---|---|---|
| `[31, 5, 2, 30, 4, 3, 32]` | `4` | 2, 3, 4, 5 — longer than 30, 31, 32 |
| `[]` | `0` | no numbers, no run |
| `[1, 2, 2, 3]` | `3` | the second 2 adds nothing |

Constraints that matter: up to 100,000 numbers; values from −10⁹ to 10⁹. The array is not sorted and you must not rely on position — the run is about values, not neighbours in the array.

::: Pattern and cue
**Hash set.** The cue is *"unsorted"* combined with *"O(n)"*. Sorting would make the runs obvious but costs O(n log n), so you need another way to ask "is the next value present?" in constant time — that question is a set lookup.

The trick that keeps it linear: only start counting a run from its **bottom**. A value is the bottom of a run if the value one below it is *not* in the set. Every other value is skipped, so each run is walked exactly once.
:::

::: Approach
Put every number into a set, which also removes repeats. Then look at each value in the set. If the value one less is also in the set, this value is in the middle of a run — skip it. Otherwise it starts a run: step upward one value at a time while the next value is in the set, and count the steps. Keep the longest count you have seen.

Time O(n): building the set is O(n); the outer loop visits each value once; the inner walk only runs from run starts, and every value is walked over by at most one of those — so the inner steps add up to n in total, not n per value. Space O(n) for the set.

Sorting and scanning is O(n log n) and O(1) extra — say it as the fallback, and why the problem forbids it.
:::

::: Swift solution
```swift
func longestConsecutive(_ numbers: [Int]) -> Int {
    let seen = Set(numbers)
    var longest = 0

    for start in seen {
        // Only start counting at the bottom of a run.
        if start > .min, seen.contains(start - 1) { continue }

        var end = start
        while end < .max, seen.contains(end + 1) {
            end += 1
        }
        longest = max(longest, end - start + 1)
    }
    return longest
}
```

The `start > .min` and `end < .max` guards look fussy; the trap below explains why they are there. Within the stated constraints you can leave them out and say so.

Verified with `swift test` on Swift 6.2.3 in Swift 6 mode: the three examples above plus six more — a single value, the same value three times, a run crossing zero (`-2 … 1`), values sitting at `Int.max` and `Int.min` (which crash the unguarded version), no two values adjacent, and a run of five given in descending order.
:::

::: Walk it through
**`[31, 5, 2, 30, 4, 3, 32]`**

The set holds 2, 3, 4, 5, 30, 31, 32 (in whatever order Swift picks — it doesn't matter).

| Value | One below in set? | Action | Longest |
|---|---|---|---|
| 2 | 1 — no | walk 3, 4, 5, stop at 6 → length 4 | 4 |
| 3, 4, 5 | yes | skip | 4 |
| 30 | 29 — no | walk 31, 32, stop at 33 → length 3 | 4 |
| 31, 32 | yes | skip | 4 |

Seven values, seven checks in the outer loop, five steps in total in the inner walks. Answer 4.

**`[1, 2, 2, 3]`** — the set is {1, 2, 3}. 1 starts a run, walks to 3, length 3. The duplicate never reaches the loop, which is why iterating the set rather than the array matters: with the array, a value repeated a thousand times at the bottom of a long run would walk that run a thousand times.
:::

::: The Swift trap
**`start - 1` and `end + 1` crash at the edges of `Int`.** In C, `INT_MIN - 1` quietly wraps around to the maximum; in Swift, arithmetic that overflows traps — the process stops. So an input containing `Int.min` crashes on the very first check, and one containing `Int.max` crashes when the walk tries to look past it. The problem's constraints keep values within ±10⁹, so this won't fire on LeetCode, but it will fire on a test an interviewer writes to probe you. Guard the comparison (`start > .min`), or use the reporting forms (`start.subtractingReportingOverflow(1)`) — not `&-`, which wraps `Int.min` around to `Int.max` and, if `Int.max` is also in the set, silently gives a wrong answer instead of a crash.

The related one: iterate `seen`, not `numbers`. It gives the same answer either way, and only the complexity breaks — which is the kind of bug a test won't catch and an interviewer will.
:::

::: What they ask next
- **"Return the run itself, not its length."** → Keep `bestStart` alongside `longest`; the run is `bestStart ... bestStart + longest - 1`.
- **"Numbers keep arriving; keep the answer up to date."** → Union-find, or a dictionary from each run's endpoints to its length: on insert, merge with the run ending at `x − 1` and the one starting at `x + 1`, update both new endpoints. O(1) amortised per insert.
- **"Memory is tight."** → Sort in place and scan, skipping equal neighbours: O(n log n) time, O(1) extra. Trade the time back for the space, and say that's the trade.
:::
