---
title: 10 · Sort Colors
summary: Rearrange an array of 0s, 1s and 2s so equal values sit together, in place and in one pass.
minutes: 25
sources:
- LeetCode 75 · Sort Colors | https://leetcode.com/problems/sort-colors/
- Swift standard library · MutableCollection.swapAt(_:_:) | https://developer.apple.com/documentation/swift/mutablecollection/swapat(_:_:)
---

*Medium · G*

You get an array whose entries are only ever 0, 1 or 2 — think red, white and blue markers. Rearrange it so that all the 0s come first, then all the 1s, then all the 2s. Change the array you were given rather than returning a new one, don't call the library sort, and aim to look at each entry only once.

| Before | After |
|---|---|
| `[2, 0, 1, 1, 0, 2]` | `[0, 0, 1, 1, 2, 2]` |
| `[1, 0]` | `[0, 1]` |
| `[2, 2, 1]` | `[1, 2, 2]` — no 0s at all |

Constraints that matter: between 1 and 300 entries, each 0, 1 or 2. "In place" means O(1) extra memory: a few index variables, no second array. Counting the three values and writing them back is a valid two-pass answer; the target is a single pass.

::: Pattern and cue
**Three pointers partitioning in place — the Dutch national flag.** The cue is *"only three distinct values"* plus *"in place"* and *"one pass"*. Two pointers mark where the finished 0s end and where the finished 2s begin; a third walks the unsorted middle and throws each value to the side it belongs on.
:::

::: Approach
Keep three positions. Everything before `low` is a finished 0. Everything after `high` is a finished 2. Everything from `low` up to `mid` is a finished 1, and `mid` to `high` is still unseen.

Look at the value under `mid`. A 0 gets swapped to `low`, and both `low` and `mid` move forward. A 1 is already in the right zone, so only `mid` moves. A 2 gets swapped to `high`, and `high` moves back — but `mid` stays where it is, because the value that just arrived from the far end hasn't been looked at yet. Stop when `mid` passes `high`: nothing unseen is left.

Time O(n): every step either moves `mid` forward or `high` back, so there are at most n steps. Space O(1): three indices.
:::

::: Swift solution
```swift
func sortColors(_ colors: inout [Int]) {
    var low = 0                     // next slot for a 0
    var mid = 0                     // the value being looked at
    var high = colors.count - 1     // next slot for a 2

    while mid <= high {
        switch colors[mid] {
        case 0:
            colors.swapAt(low, mid)
            low += 1
            mid += 1
        case 1:
            mid += 1
        default:
            colors.swapAt(mid, high)
            high -= 1               // don't move mid: the value that just arrived is unseen
        }
    }
}
```

When a 0 is swapped from `low`, `mid` may move forward without looking, because whatever sat at `low` was already seen and was a 1 (or `low` and `mid` were the same position).

Verified with `swift test` on Swift 6.2.3 in Swift 6 mode: the three examples above, six more (empty, a single 0, a single 2, reversed `[2, 1, 0]`, all 1s, `[2, 0, 2, 0]` with no 1s), and 3,000 random arrays checked against the library sort.
:::

::: Walk it through
**`[2, 0, 1, 1, 0, 2]`** — low 0, mid 0, high 5

| Array | low | mid | high | Value at mid | Action |
|---|---|---|---|---|---|
| `[2, 0, 1, 1, 0, 2]` | 0 | 0 | 5 | 2 | swap with high (a 2 for a 2); high → 4 |
| `[2, 0, 1, 1, 0, 2]` | 0 | 0 | 4 | 2 | swap with high; high → 3 |
| `[0, 0, 1, 1, 2, 2]` | 0 | 0 | 3 | 0 | swap with low (itself); low, mid → 1 |
| `[0, 0, 1, 1, 2, 2]` | 1 | 1 | 3 | 0 | swap with low (itself); low, mid → 2 |
| `[0, 0, 1, 1, 2, 2]` | 2 | 2 | 3 | 1 | mid → 3 |
| `[0, 0, 1, 1, 2, 2]` | 2 | 3 | 3 | 1 | mid → 4, passes high → stop |

The first two rows are the reason `mid` holds still after a 2: the value swapped in was another 2, and it would have been left in the middle had `mid` moved on.

**`[1, 0]`** — the 1 at position 0 stays and `mid` moves to 1. The 0 there is swapped with `low` (position 0): `[0, 1]`. `mid` becomes 2, passes `high` at 1, stop.
:::

::: The Swift trap
**`swap(&colors[i], &colors[j])` breaks exclusive access.** It is the obvious spelling and it doesn't compile: two `inout` accesses to the same array overlap, and Swift rejects it ("overlapping accesses to 'colors'"). Use `colors.swapAt(i, j)`, which is the array's own method and is fine when `i == j` — which happens here every time `low` and `mid` sit together. The second trap is the `inout` itself: `func sortColors(_ colors: [Int])` receives a constant copy, so an answer that "sorts in place" into a local `var` changes nothing the caller can see. Say "in place" and write `inout` and `&` at the call site.
:::

::: What they ask next
- **"Why not just count them?"** → Counting 0s, 1s and 2s and writing them back is O(n) and O(1), but takes two passes and only works because the values carry no payload. If each entry were a record sorted by a colour key, overwriting would lose the records; swapping keeps them.
- **"Is it stable?"** → No. Swaps with the far end reorder equal keys. A stable version needs O(n) extra memory — three buckets appended in order.
- **"Now there are k colours."** → Counting sort in O(n + k), or partition repeatedly: split around the middle colour and recurse, O(n log k). The three-pointer trick doesn't generalise past three.
:::
