---
title: 10 · Continuous Subarray Sum
summary: Given a list of whole numbers and a number k, say whether some stretch of at least two neighbouring entries adds up to a multiple of k.
group: Prefix sums
minutes: 25
sources:
- LeetCode 523 · Continuous Subarray Sum | https://leetcode.com/problems/continuous-subarray-sum/
- The Swift Programming Language · Remainder Operator | https://docs.swift.org/swift-book/documentation/the-swift-programming-language/basicoperators/#Remainder-Operator
---

*Medium*

You get an array of non-negative integers and a positive number k. Look for a stretch of **two or more** entries that sit next to each other and whose total is a multiple of k. Zero counts as a multiple of every k. Return `true` if at least one such stretch exists.

| Numbers | k | Answer |
|---|---|---|
| `[5, 2, 4, 1]` | `6` | `true` — 2 + 4 = 6 |
| `[6, 1]` | `6` | `false` — the 6 on its own is a multiple, but a stretch needs two entries |
| `[0, 0]` | `7` | `true` — 0 + 0 = 0, a multiple of 7 |

Constraints that matter: up to 100,000 numbers, each between 0 and 10⁹, and k between 1 and 2³¹ − 1. Checking every stretch is O(n²). The target is O(n).

::: Starter code and tests
In an Xcode test target:

```swift
import Testing

struct ContinuousSubarraySumTests {

    @Test(arguments: [
        ([5, 2, 4, 1], 6, true),
        ([6, 1], 6, false),
        ([0, 0], 7, true),
    ])
    func reportsWhetherAStretchOfTwoOrMoreSumsToAMultipleOfK(numbers: [Int], k: Int, expected: Bool) {
        #expect(checkSubarraySum(numbers, k) == expected)
    }

    // MARK: - Privates
    private func checkSubarraySum(_ numbers: [Int], _ k: Int) -> Bool {
        false
    }
}
```

In a playground:

```swift
func checkSubarraySum(_ numbers: [Int], _ k: Int) -> Bool {
    false // your solution
}

let cases: [([Int], Int, Bool)] = [
    ([5, 2, 4, 1], 6, true),
    ([6, 1], 6, false),
    ([0, 0], 7, true),
]
for (numbers, k, expected) in cases {
    let got = checkSubarraySum(numbers, k)
    print(got == expected ? "PASS" : "FAIL", numbers, k, "→", got, "expected", expected)
}
```
:::

::: Pattern and cue
**Prefix sums keyed by remainder.** The cue is *"a stretch of neighbouring entries"* plus *"adds up to"*: a subarray sum, which is the difference of two running totals. *"A multiple of k"* changes what you look up. Two running totals differ by a multiple of k exactly when they leave the same remainder after dividing by k, so the question becomes "have I seen this remainder before, far enough back?"
:::

::: Approach
Walk the array keeping a running total, but store only its remainder after dividing by k. Keep a dictionary from each remainder to the **first** position where it appeared, starting with remainder 0 at position −1, which stands for "nothing taken yet". At each position, work out the new remainder. If it has appeared before, the entries between that earlier position and this one add up to a multiple of k; if there are at least two of them, the answer is `true`. If the remainder is new, record where it first appeared. Never overwrite an earlier position: the earliest one gives the longest stretch, and the longest is the one most likely to reach two entries.

Time O(n): one pass with O(1) average dictionary work per entry. Space O(min(n, k)): there are at most k different remainders.
:::

::: Swift solution
```swift
func checkSubarraySum(_ numbers: [Int], _ k: Int) -> Bool {
    var firstIndexByRemainder: [Int: Int] = [0: -1]   // the empty prefix, before index 0
    var remainder = 0

    for (index, number) in numbers.enumerated() {
        remainder = ((remainder + number) % k + k) % k
        if let earlier = firstIndexByRemainder[remainder] {
            if index - earlier >= 2 { return true }
        } else {
            firstIndexByRemainder[remainder] = index     // only the first time
        }
    }
    return false
}
```

The `if let … else` keeps the earliest position for each remainder. The `+ k) % k` does nothing for the non-negative inputs in the statement; it is there so the function stays right if negatives are allowed, which the trap below explains.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, seven more (a single number, k = 1, a multiple only across the whole array, `[0]` alone, `[1, 2, 3]` with k 5 where the stretch is the last two entries, `[2, 4, 3]` with k 6 where it is the first two, negatives with k 5), and 3,000 random arrays (values from −6 to 6, k from 1 to 7) checked against an O(n²) brute force over every stretch.
:::

::: Walk it through
**`[5, 2, 4, 1]`, k = 6**

| Index | Number | Remainder | Seen before? | Action |
|---|---|---|---|---|
| — | — | 0 | — | start: `0 → −1` |
| 0 | 5 | 5 | no | record `5 → 0` |
| 1 | 2 | 1 | no | record `1 → 1` |
| 2 | 4 | 5 | yes, at 0 | 2 − 0 = 2 entries (the 2 and the 4) → `true` |

**`[6, 1]`, k = 6** — at index 0 the remainder is 0, seen at −1: that stretch has 0 − (−1) = 1 entry, too short, and the remainder isn't re-recorded. At index 1 the remainder is 1, new. End: `false`. Had the first match overwritten `0 → −1` with `0 → 0`, a later remainder 0 would measure from the wrong place.
:::

::: The Swift trap
**Swift's `%` keeps the sign of the left side.** `-4 % 6` is `-4`, not `2`. A running total of −4 and one of 2 differ by 6, a multiple of 6, but if you key the dictionary on the raw `%` they land under different keys and the stretch is missed. The statement keeps every number non-negative, so it won't fire on the examples, but the first follow-up is often "and with negatives?" — so write the normalising form `((x % k) + k) % k` from the start. And `x % 0` traps at runtime; here k ≥ 1 is promised, but say that you checked.
:::

::: What they ask next
- **"Count the stretches whose sum is divisible by k, with no length limit."** → The same remainders, but store a count per remainder and add it at each step, as in [9 · Subarray Sum Equals K](#/dsa/subarray-sum-equals-k).
- **"Return the stretch itself."** → When the check succeeds, the stretch runs from `earlier + 1` to `index`.
- **"Why remainders and not the running totals themselves?"** → Totals that differ by k, 2k, 3k… would need a lookup for every multiple; remainders collapse all of them into one key.
:::
