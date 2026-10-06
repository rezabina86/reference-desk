---
title: 89 · Missing Number
summary: A list holds all but one of the whole numbers from 0 to its own length, each at most once; find the one that isn't there.
group: Bit manipulation
minutes: 15
sources:
- LeetCode 268 · Missing Number | https://leetcode.com/problems/missing-number/
- The Swift Programming Language · Overflow Operators | https://docs.swift.org/swift-book/documentation/the-swift-programming-language/advancedoperators/#Overflow-Operators
---

*Easy · G*

You get an array of n different integers, in any order, all taken from the range 0 to n. That range has n + 1 values and the array has only n, so exactly one value from the range is absent. Return it. It can be any of them, including 0 or n itself.

| Numbers | Answer |
|---|---|
| `[4, 0, 1, 3]` | `2` |
| `[0, 1, 2]` | `3` — the missing value is n itself |
| `[0]` | `1` — the smallest input |

Constraints that matter: n is between 1 and 10,000, all values distinct. Sorting is O(n log n) and a `Set` is O(n) space; the target is one pass, O(n) time and O(1) extra space.

::: Starter code and tests
In an Xcode test target:

```swift
import Testing

struct MissingNumberTests {

    @Test(arguments: [
        ([4, 0, 1, 3], 2),
        ([0, 1, 2], 3),
        ([0], 1),
    ])
    func findsTheOneValueAbsentFromZeroThroughN(numbers: [Int], expected: Int) {
        #expect(missingNumber(numbers) == expected)
    }

    // MARK: - Privates
    private func missingNumber(_ numbers: [Int]) -> Int {
        0
    }
}
```

In a playground:

```swift
func missingNumber(_ numbers: [Int]) -> Int {
    0 // your solution
}

let cases: [([Int], Int)] = [
    ([4, 0, 1, 3], 2),
    ([0, 1, 2], 3),
    ([0], 1),
]
for (numbers, expected) in cases {
    let got = missingNumber(numbers)
    print(got == expected ? "PASS" : "FAIL", numbers, "→", got, "expected", expected)
}
```
:::

::: Pattern and cue
**XOR cancels pairs.** The cue is *"all the numbers from 0 to n except one"*, *"each once"*, plus *"constant extra space"*. XOR together every value the range should contain and every value the array does contain: each present value appears twice and cancels to 0, and the absent one is left on its own.
:::

::: Approach
Imagine a register of everyone who should be at a meeting and the list of everyone who signed in. Cross each signature off against the register, and the one name not crossed off is who's missing. XOR does the crossing off: `x ^ x` is 0, `x ^ 0` is `x`, and the order doesn't matter. The register is the numbers 0 to n, and the array's positions already supply 0 to n − 1 — so start from n, and for each position XOR in both the position and the value stored there. Every value that is present meets its twin and vanishes; what's left is the missing one.

Time O(n): one pass. Space O(1): one integer.
:::

::: Swift solution
```swift
func missingNumber(_ numbers: [Int]) -> Int {
    var result = numbers.count            // n itself, the one value with no position
    for (index, value) in numbers.enumerated() {
        result ^= index ^ value
    }
    return result
}
```

Starting from `numbers.count` is the easy line to forget: positions only run from 0 to n − 1, so without it n never enters the XOR, and `[0, 1, 2]` comes back as 0 instead of 3.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, five more (`[1]` missing 0, an empty array missing 0, `[2, 0]`, `[3, 1, 2]` missing 0, a reversed `[5, 4, 3, 2, 1, 0]` missing 6), and 3,000 shuffled ranges up to 200 with one random value removed, checked against a brute force that searches 0…n in a `Set`.
:::

::: Walk it through
**`[4, 0, 1, 3]`** — n = 4, so result starts at 4

| index | value | result after `^= index ^ value` | what's cancelled so far |
|---|---|---|---|
| 0 | 4 | 4 ^ 0 ^ 4 = 0 | 4 twice; 0 once |
| 1 | 0 | 0 ^ 1 ^ 0 = 1 | 0 twice; 1 once |
| 2 | 1 | 1 ^ 2 ^ 1 = 2 | 1 twice; 2 once |
| 3 | 3 | 2 ^ 3 ^ 3 = 2 | 3 twice |

Every value from 0 to 4 went in, the array's values went in again, and only 2 went in once. Answer 2.

**`[0, 1, 2]`** — result starts at 3. Each position equals its value, so every step XORs a number with itself and changes nothing. The 3 put in at the start is the answer.
:::

::: The Swift trap
**The sum formula traps where C would wrap.** The other classic answer is arithmetic: the numbers 0 to n add up to `n * (n + 1) / 2`, so subtract the array's sum from that. At these sizes it's fine, but say what happens at scale: in C or Java the sum overflows silently and, because wrap-around arithmetic is exact modulo 2⁶⁴, the subtraction still lands on the right answer. Swift's `+` and `*` crash on overflow instead. Swapping in `&*` doesn't rescue the formula either, because the `/ 2` after a wrapped multiplication is no longer exact. The safe arithmetic version skips the formula and folds the difference as it goes — `result = result &+ index &- value`, starting from n — where wrapping is harmless because only additions and subtractions are involved. XOR has no carries at all, so it can't overflow in the first place.
:::

::: What they ask next
- **"Without bit tricks?"** → The sum version: `numbers.count * (numbers.count + 1) / 2 - numbers.reduce(0, +)`. Mention the overflow point above.
- **"Two numbers are missing."** → XOR everything as before to get `a ^ b`; any 1 bit in it is a position where a and b differ. Split all values (range and array) by that bit and XOR each group separately: one group yields a, the other b.
- **"The array may be modified — any other O(1)-space way?"** → Cyclic placement: swap each value into the position equal to it (skipping n), then the first position whose value doesn't match is missing, or n if all match.
:::
