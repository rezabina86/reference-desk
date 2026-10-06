---
title: 26 · Binary Search
summary: Find the position of a target number in a sorted list of distinct numbers, or report that it isn't there, without checking every entry.
group: Binary search
minutes: 25
sources:
- LeetCode 704 · Binary Search | https://leetcode.com/problems/binary-search/
- The Swift Programming Language · Advanced Operators (overflow) | https://docs.swift.org/swift-book/documentation/the-swift-programming-language/advancedoperators/
---

*Easy · G — the warm-up; write the loop without having to think about the boundaries*

You get a list of distinct integers sorted from smallest to largest, and a target. Return the index where the target sits, or −1 if it isn't in the list. You must not look at every entry: the work has to grow with the logarithm of the list's length.

| Numbers | Target | Answer |
|---|---|---|
| `[-4, 0, 3, 8, 12]` | `8` | `3` |
| `[-4, 0, 3, 8, 12]` | `5` | `-1` — would sit between 3 and 8, but isn't there |
| `[7]` | `7` | `0` — one entry; the edge case for the loop condition |

Constraints that matter: up to 10,000 numbers, all distinct, sorted ascending. A linear scan is O(n); the target is O(log n).

::: Starter code and tests
In an Xcode test target:

```swift
import Testing

struct BinarySearchTests {

    @Test(arguments: [
        ([-4, 0, 3, 8, 12], 8, 3),
        ([-4, 0, 3, 8, 12], 5, -1),
        ([7], 7, 0),
    ])
    func returnsTheIndexOfTheTargetOrMinusOne(numbers: [Int], target: Int, expected: Int) {
        #expect(search(numbers, target) == expected)
    }

    // MARK: - Privates
    private func search(_ numbers: [Int], _ target: Int) -> Int {
        -1
    }
}
```

In a playground:

```swift
func search(_ numbers: [Int], _ target: Int) -> Int {
    -1 // your solution
}

let cases: [([Int], Int, Int)] = [
    ([-4, 0, 3, 8, 12], 8, 3),
    ([-4, 0, 3, 8, 12], 5, -1),
    ([7], 7, 0),
]
for (numbers, target, expected) in cases {
    let got = search(numbers, target)
    print(got == expected ? "PASS" : "FAIL", numbers, target, "→", got, "expected", expected)
}
```

The placeholder returns −1, the "not found" answer, so it already passes the second case.
:::

::: Pattern and cue
**Binary search, exact match.** The cues are *"sorted"* and *"O(log n)"*. Comparing the target with the middle entry tells you which half it must be in, so one comparison throws away half of what's left.
:::

::: Approach
Keep two markers, one at each end of the part of the list where the target could still be. Look at the entry halfway between them. If it's the target, you're done. If it's smaller than the target, the target can only be to its right, so move the left marker just past the middle. If it's bigger, move the right marker just before the middle. When the markers cross, the part that could hold the target is empty: the answer is −1.

Time O(log n): the searched part halves every step. Space O(1): two markers and a middle.
:::

::: Swift solution
```swift
func search(_ numbers: [Int], _ target: Int) -> Int {
    var low = 0
    var high = numbers.count - 1

    while low <= high {
        let mid = low + (high - low) / 2         // never overflows, unlike (low + high) / 2
        if numbers[mid] == target {
            return mid
        } else if numbers[mid] < target {
            low = mid + 1
        } else {
            high = mid - 1
        }
    }
    return -1
}
```

`low` and `high` are both inclusive, so the loop runs while `low <= high` — with `<`, a one-entry list would never be checked. Both updates step *past* `mid`, which is what guarantees the loop ends.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, six more (an empty list, a one-entry miss, both ends of a two-entry list, a target above the largest and below the smallest), a search in a list of a million numbers, and 3,000 random sorted lists checked against `firstIndex(of:)`.
:::

::: Walk it through
**`[-4, 0, 3, 8, 12]`, target 8**

| low | high | mid | numbers[mid] | Action |
|---|---|---|---|---|
| 0 | 4 | 2 | 3 | 3 < 8: low = 3 |
| 3 | 4 | 3 | 8 | found: return 3 |

**Same list, target 5**

| low | high | mid | numbers[mid] | Action |
|---|---|---|---|---|
| 0 | 4 | 2 | 3 | 3 < 5: low = 3 |
| 3 | 4 | 3 | 8 | 8 > 5: high = 2 |
| 3 | 2 | — | — | low > high: return −1 |

**`[7]`, target 7** — low = high = 0, so `low <= high` holds once, mid = 0, found. An empty list starts with high = −1 and returns −1 without touching the array.
:::

::: The Swift trap
**`(low + high) / 2` doesn't wrap in Swift — it crashes.** In C or Java, adding two large indices silently overflows into a negative number (the bug that sat in Java's own library for years). In Swift, `Int` addition that overflows stops the program. Array indices never come close to `Int.max`, so here it can't actually happen, but the same loop over an answer range — "the smallest value up to `Int.max` such that…" — will hit it. `low + (high - low) / 2` can't overflow for any valid `low` and `high`, so write it every time and say why. The other Swift point to say out loud: `numbers.firstIndex(of: target)` is one line and correct, but it's O(n), which the statement forbids.
:::

::: What they ask next
- **"The list has duplicates. Return the first position of the target."** → Don't stop at a match: set `high = mid` and keep going (the lower-bound shape), then check that the entry at `low` really is the target.
- **"Return where the target would be inserted to keep the list sorted."** → That's the lower bound: the first index whose value is ≥ the target, which can be `count`.
- **"Write it recursively."** → Pass `low` and `high`, not array slices — a slice keeps its parent's indices, so `slice[0]` traps.
:::
