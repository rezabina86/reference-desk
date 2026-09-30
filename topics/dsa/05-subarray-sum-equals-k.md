---
title: 5 · Subarray Sum Equals K
summary: Given a list of whole numbers and a target, count how many unbroken stretches of the list add up to exactly that target.
minutes: 25
sources:
- LeetCode 560 · Subarray Sum Equals K | https://leetcode.com/problems/subarray-sum-equals-k/
- Swift standard library · Dictionary.subscript(_:default:) | https://developer.apple.com/documentation/swift/dictionary/subscript(_:default:)-45arb
---

*Medium*

You get an array of integers, which may include negatives and zeros, and a target number k. A stretch is one or more entries that sit next to each other in the array. Count how many stretches add up to exactly k. Two stretches count separately if they start or end at different positions, even when they hold the same values.

| Numbers | k | Answer | The stretches |
|---|---|---|---|
| `[1, 2, 1, -1, 2]` | `3` | `3` | `[1, 2]`, `[2, 1]`, `[1, 2, 1, -1]` |
| `[3, -3, 3]` | `3` | `3` | the first `3`, the last `3`, and all three together |
| `[0, 0, 0]` | `0` | `6` | every stretch — three of length 1, two of length 2, one of length 3 |

Constraints that matter: up to 20,000 numbers, each between −1,000 and 1,000, so running totals stay small. Checking every start and end is O(n²) — that is the answer to beat. The negatives are the point of the problem: they are what breaks the obvious approach.

::: Pattern and cue
**Prefix sums, with a hash map of the sums seen so far.** The cue is *"stretches that add up to exactly k"* — a subarray sum. Any stretch's total is the difference of two running totals: the total up to its end minus the total just before its start. So "a stretch ending here sums to k" becomes "some earlier running total equals the current one minus k" — and "have I seen this value before, how many times?" is a dictionary lookup.

Why not a sliding window? A window grows while the sum is too small and shrinks while it is too big. That only works when adding an element always increases the sum. With negatives and zeros it doesn't, so the window has no rule for when to move.
:::

::: Approach
Walk the array once, keeping a running total. Keep a dictionary that counts how many times each running total has appeared so far, starting with a total of 0 seen once — that stands for "nothing taken yet", and it is what lets a stretch that starts at the very first entry be counted. At each entry, add it to the running total, then ask the dictionary how many earlier totals equal the current total minus k: each one marks the start of a stretch that ends here and sums to k. Add that count to the answer, then record the current total.

Time O(n): one pass, O(1) average per dictionary step. Space O(n): at most one dictionary entry per distinct running total.
:::

::: Swift solution
```swift
func subarraySum(_ numbers: [Int], _ k: Int) -> Int {
    var countBySum: [Int: Int] = [0: 1]   // the empty prefix
    var sum = 0
    var matches = 0

    for number in numbers {
        sum += number
        matches += countBySum[sum - k, default: 0]
        countBySum[sum, default: 0] += 1
    }
    return matches
}
```

The order inside the loop matters: **look up, then record.** Recording first would count the empty stretch that starts and ends at the same place whenever k is 0.

Verified with `swift test` on Swift 6.2.3 in Swift 6 mode: the three examples above, six more (an empty array, a single entry that does and doesn't match, `[-1, -1, 1]` with k 0, `[1, 1, 1]` with k 2, and alternating `[2, -2, 2, -2]` with k 0), and 2,000 random arrays with values from −3 to 3, each checked against the O(n²) brute force.
:::

::: Walk it through
**`[1, 2, 1, -1, 2]`, k = 3**

| Entry | Running total | Look for (total − 3) | Found | Matches | Totals seen after |
|---|---|---|---|---|---|
| — | 0 | — | — | 0 | `0:1` |
| 1 | 1 | −2 | 0 | 0 | `0:1, 1:1` |
| 2 | 3 | 0 | 1 | 1 — `[1, 2]` | `+ 3:1` |
| 1 | 4 | 1 | 1 | 2 — `[2, 1]` | `+ 4:1` |
| −1 | 3 | 0 | 1 | 3 — `[1, 2, 1, −1]` | `3:2` |
| 2 | 5 | 2 | 0 | 3 | `+ 5:1` |

Answer 3.

**`[0, 0, 0]`, k = 0** — the running total stays 0. Before each record the dictionary holds `0:1`, then `0:2`, then `0:3`, so the matches add up 1 + 2 + 3 = 6. That is every stretch, which is right. Record before looking up and you'd get 2 + 3 + 4 = 9.
:::

::: The Swift trap
**Reading a missing key.** `countBySum[sum - k]` is an `Int?`, so `matches += countBySum[sum - k]` doesn't compile. Under time pressure the tempting fix is `countBySum[sum - k]!`, which crashes on the first entry — at that point almost nothing has been seen. Use `countBySum[sum - k, default: 0]`: in a read, the default subscript just returns 0 and does **not** insert the key, so lookups never grow the dictionary. In a write — `countBySum[sum, default: 0] += 1` — it inserts and increments in one hash. Knowing that the same subscript behaves differently when read and when written is exactly the kind of detail an interviewer probes.
:::

::: What they ask next
- **"Return the longest such stretch instead of the count."** → Store the *first* position each running total appeared at, not a count; at each entry the length is `i − firstIndex[sum − k]`.
- **"What if every number were positive?"** → Then a sliding window works in O(1) space: grow the right edge, shrink from the left while the sum exceeds k.
- **"Count stretches whose sum is divisible by k."** → Same shape, keyed by the running total modulo k — and normalise negative remainders, because Swift's `%` keeps the sign of the left side (`-1 % 5 == -1`).
:::
