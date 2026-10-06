---
title: 12 · Two Sum II — Input Array Is Sorted
summary: Given a list of whole numbers already in ascending order and a target, find the two entries that add up to it, using no extra memory.
group: Two pointers
minutes: 25
sources:
- LeetCode 167 · Two Sum II — Input Array Is Sorted | https://leetcode.com/problems/two-sum-ii-input-array-is-sorted/
- Swift standard library · addingReportingOverflow(_:) | https://developer.apple.com/documentation/swift/int/addingreportingoverflow(_:)
---

*Medium — problem 3 again, with one new constraint that changes the best answer*

You get an array of integers sorted from smallest to largest, and a target. Exactly two different entries add up to the target. Return their positions **counted from 1**, smaller first. The catch: you may only use a constant amount of extra memory — no dictionary.

| Numbers | Target | Answer | Why |
|---|---|---|---|
| `[2, 3, 5, 8, 13]` | `16` | `[2, 5]` | 3 + 13 |
| `[-3, -1, 0, 4]` | `-4` | `[1, 2]` | −3 + −1 |
| `[5, 5]` | `10` | `[1, 2]` | two different entries with the same value |

Constraints that matter: between 2 and 30,000 numbers, each between −1,000 and 1,000; exactly one answer exists. The dictionary answer from problem 3 still works, but it uses O(n) memory, which this version forbids.

::: Starter code and tests
In an Xcode test target:

```swift
import Testing

struct TwoSumSortedTests {

    @Test(arguments: [
        ([2, 3, 5, 8, 13], 16, [2, 5]),
        ([-3, -1, 0, 4], -4, [1, 2]),
        ([5, 5], 10, [1, 2]),
    ])
    func returnsTheOneBasedPositionsOfThePair(numbers: [Int], target: Int, expected: [Int]) {
        #expect(twoSum(numbers, target) == expected)
    }

    // MARK: - Privates
    private func twoSum(_ numbers: [Int], _ target: Int) -> [Int] {
        []
    }
}
```

In a playground:

```swift
func twoSum(_ numbers: [Int], _ target: Int) -> [Int] {
    [] // your solution
}

let cases: [([Int], Int, [Int])] = [
    ([2, 3, 5, 8, 13], 16, [2, 5]),
    ([-3, -1, 0, 4], -4, [1, 2]),
    ([5, 5], 10, [1, 2]),
]
for (numbers, target, expected) in cases {
    let got = twoSum(numbers, target)
    print(got == expected ? "PASS" : "FAIL", numbers, target, "→", got, "expected", expected)
}
```
:::

::: Pattern and cue
**Two pointers, from both ends inward.** The cues are *"sorted"* and *"constant extra memory"*. Sorted means that moving right always gives a bigger number and moving left a smaller one — so a sum that is too small has exactly one fix (move the left end up) and a sum that is too big has exactly one fix (move the right end down). No lookup table is needed, because the order itself tells you which way to go.
:::

::: Approach
Start with one finger on the smallest number and one on the largest. Add them. If the sum is the target, you are done. If it is too small, the smallest number can't be part of the answer — even paired with the largest, it falls short — so move the left finger right. If it is too big, the largest can't be part of it, so move the right finger left. Each step rules out one number for good.

Time O(n): every step moves one finger inward, and they can only meet once. Space O(1): two positions and a sum.
:::

::: Swift solution
```swift
func twoSum(_ numbers: [Int], _ target: Int) -> [Int] {
    var left = 0
    var right = numbers.count - 1

    while left < right {
        let (sum, overflowed) = numbers[left].addingReportingOverflow(numbers[right])
        if !overflowed && sum == target {
            return [left + 1, right + 1]          // positions are 1-based
        }
        // On overflow the true sum is past Int's range in the direction of the larger value.
        let tooBig = overflowed ? numbers[right] > 0 : sum > target
        if tooBig { right -= 1 } else { left += 1 }
    }
    return []
}
```

Within the stated constraints the plain `let sum = numbers[left] + numbers[right]` is fine — say so, and say why you'd guard it in production (see the trap).

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above plus seven more — the minimum two entries, zeros, a long run of equal values before the partner, a mixed-sign array, and three arrays holding `Int.max` or `Int.min`, which crash the unguarded version — and 3,000 random sorted arrays checked against a brute-force search over every pair.
:::

::: Walk it through
**`[2, 3, 5, 8, 13]`, target 16**

| Left | Right | Sum | Action |
|---|---|---|---|
| 1 → `2` | 5 → `13` | 15 | too small → left moves |
| 2 → `3` | 5 → `13` | 16 | found → `[2, 5]` |

**`[5, 5]`, target 10** — left on position 1, right on position 2, sum 10, answer `[1, 2]`. The two fingers start on different entries, so equal values are never a problem.
:::

::: The Swift trap
**The sum of two valid entries can crash.** The answer pair always fits in `Int` — its sum is the target — but the pairs you try on the way don't have to. With `[1, 2, Int.max]` and target 3, the first step adds `1 + Int.max`, and Swift traps where C would wrap. Rewriting the check as `numbers[left] > target - numbers[right]` only moves the problem to the subtraction. `addingReportingOverflow` gives you the wrapped result plus a flag, and in a sorted array the direction of an overflow tells you which finger to move: overflowing upward means the sum is too big.

The other slip here is not Swift's fault: the answer is **1-based**. Returning `[left, right]` passes every self-made test and fails the grader. Read the statement back (the R in REACTO) and you catch it.
:::

::: What they ask next
- **"Why does moving the left pointer never skip the answer?"** → If the sum is too small with the largest remaining number, the current left number can't reach the target with anything, so discarding it is safe. Same argument mirrored for the right.
- **"Return every pair, not just one."** → On a match, record it, move both fingers, and skip past repeats of each value so pairs aren't duplicated. That skip is the heart of the next problem.
- **"The array isn't sorted."** → Either sort pairs of (value, position) — O(n log n), O(n) space — or use the dictionary from problem 3, O(n) and O(n). Sorting in place and returning positions doesn't work: the positions move.
:::
