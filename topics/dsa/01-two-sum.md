---
title: 1 · Two Sum
summary: Given a list of whole numbers and a target, return the positions of the two numbers that add up to it.
minutes: 25
sources:
- LeetCode 1 · Two Sum | https://leetcode.com/problems/two-sum/
- Swift standard library · Dictionary | https://developer.apple.com/documentation/swift/dictionary
---

*Easy · G — the warm-up almost every loop has seen*

You get an array of integers and a target number. Exactly two entries in the array add up to the target. Return their two positions, smaller position first. You can't use the same entry twice, but two different entries may hold the same value.

| Numbers | Target | Answer | Why |
|---|---|---|---|
| `[3, 8, 11, 4]` | `15` | `[2, 3]` | 11 + 4 |
| `[5, 5]` | `10` | `[0, 1]` | two different fives |
| `[-4, 6, 1, 10]` | `6` | `[0, 3]` | −4 + 10; the 6 on its own doesn't count |

Constraints that matter: between 2 and 10,000 numbers; values and target fit comfortably in `Int` (roughly ±10⁹); exactly one valid pair always exists. The brute-force check of every pair is O(n²) — the interviewer is waiting for you to beat it.

::: Pattern and cue
**Hash map.** The cue is *"find a pair"* combined with *"return the positions"*. For each number you already know exactly what its partner must be — `target − number` — so the question becomes "have I seen that value before, and where?" That is a lookup, and "seen before, and where" is a dictionary from value to position.

Why not two pointers? Two pointers needs a sorted array, and sorting throws away the original positions you're asked to return. You could sort pairs of (value, position), but that's O(n log n) to reach what a dictionary gives you in O(n).
:::

::: Approach
Walk the array once, left to right. For each number, work out the partner it needs (target minus the number). Ask a dictionary whether that partner has already appeared; if it has, the dictionary tells you where, and you're done. If not, record the current number and its position in the dictionary and move on.

The order of those two steps matters: **look first, then record.** Recording first would let a number pair with itself when it's exactly half the target.

Time O(n): one pass, and each dictionary lookup and insert is O(1) on average. Space O(n): in the worst case the pair is the last two numbers and the dictionary holds everything before them.
:::

::: Swift solution
```swift
func twoSum(_ numbers: [Int], target: Int) -> [Int] {
    var indexByValue: [Int: Int] = [:]

    for (index, number) in zip(numbers.indices, numbers) {
        if let partnerIndex = indexByValue[target - number] {
            return [partnerIndex, index]
        }
        indexByValue[number] = index
    }

    return []
}
```

The partner is always found at the *second* number of the pair, so `partnerIndex` is always the smaller position — no sorting of the answer needed. The final `return []` is unreachable under the stated constraints; in a round, say so rather than reaching for `fatalError`.

Verified with `swift test` on Swift 6.2.3: the three examples above plus five more — `[3, 5, 1]` → 6 (the self-pair trap), `[0, 3, 0]` → 0 (duplicate zeros), `[7, -7, 2]` → 0 (negatives), a two-element input, and a pair whose sum is `Int.max`.
:::

::: Walk it through
**`[3, 8, 11, 4]`, target 15**

| Step | Number | Needs | Dictionary before | Result |
|---|---|---|---|---|
| 0 | 3 | 12 | `{}` | not there → record `3: 0` |
| 1 | 8 | 7 | `{3: 0}` | not there → record `8: 1` |
| 2 | 11 | 4 | `{3: 0, 8: 1}` | not there → record `11: 2` |
| 3 | 4 | 11 | `{3: 0, 8: 1, 11: 2}` | found at 2 → return `[2, 3]` |

**`[3, 5, 1]`, target 6 — the edge case**

| Step | Number | Needs | Dictionary before | Result |
|---|---|---|---|---|
| 0 | 3 | 3 | `{}` | not there (3 isn't recorded yet) → record `3: 0` |
| 1 | 5 | 1 | `{3: 0}` | not there → record `5: 1` |
| 2 | 1 | 5 | `{3: 0, 5: 1}` | found at 1 → return `[1, 2]` |

Had step 0 recorded 3 before looking, it would have found itself and returned `[0, 0]`.
:::

::: The Swift trap
**`enumerated()` hands you offsets, not indices.** On an `Array` they coincide, so `for (i, n) in numbers.enumerated()` works here. Change the parameter to `ArraySlice<Int>` or any `Collection` — which an interviewer may do as a follow-up ("now take a slice of a bigger buffer") — and offset 0 is no longer `startIndex`; subscripting with it reads the wrong element or traps. `zip(numbers.indices, numbers)` gives real indices on every collection, which is why the solution uses it. Say it out loud: it is a one-sentence senior signal.

The second trap is quieter: `numbers.firstIndex(of: target - number)` inside the loop reads like a lookup but is a linear scan, quietly putting you back at O(n²).
:::

::: What they ask next
- **"What if the array is sorted?"** → Two pointers from both ends: sum too small, move left in; too big, move right in. O(n) time, O(1) space — the dictionary disappears.
- **"Return all pairs, not just one, without duplicates."** → Sort, then two pointers, skipping equal neighbours after each hit. O(n log n). This is the doorway to 3Sum (problem 8).
- **"What if the numbers don't fit in memory?"** → Stream them in chunks and keep only the dictionary of values seen; if that doesn't fit either, partition by value range (bucket to disk) so partners land in the same bucket.
:::
