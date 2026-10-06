---
title: 28 · Find Minimum in Rotated Sorted Array
summary: Find the smallest number in a list of distinct numbers that was sorted and then shifted around in a circle, in logarithmic time.
group: Binary search
minutes: 25
sources:
- LeetCode 153 · Find Minimum in Rotated Sorted Array | https://leetcode.com/problems/find-minimum-in-rotated-sorted-array/
- Swift standard library · Sequence.min() | https://developer.apple.com/documentation/swift/sequence/min()
---

*Medium · G*

You get a non-empty list of distinct integers that was sorted ascending and then rotated: some entries were moved from the front to the back, keeping their order. The rotation may be zero, so the list may still be fully sorted. Return the smallest value, in O(log n) time.

| Numbers | Answer |
|---|---|
| `[4, 5, 6, 1, 2, 3]` | `1` |
| `[2, 4, 6, 8]` | `2` — not rotated at all; the edge case |
| `[9]` | `9` |

Constraints that matter: up to 5,000 numbers, all distinct, at least one. Scanning for the minimum is O(n); the target is O(log n).

::: Starter code and tests
In an Xcode test target:

```swift
import Testing

struct FindMinimumInRotatedSortedArrayTests {

    @Test(arguments: [
        ([4, 5, 6, 1, 2, 3], 1),
        ([2, 4, 6, 8], 2),
        ([9], 9),
    ])
    func returnsTheSmallestValueOfARotatedList(numbers: [Int], expected: Int) {
        #expect(findMin(numbers) == expected)
    }

    // MARK: - Privates
    private func findMin(_ numbers: [Int]) -> Int {
        0
    }
}
```

In a playground:

```swift
func findMin(_ numbers: [Int]) -> Int {
    0 // your solution
}

let cases: [([Int], Int)] = [
    ([4, 5, 6, 1, 2, 3], 1),
    ([2, 4, 6, 8], 2),
    ([9], 9),
]
for (numbers, expected) in cases {
    let got = findMin(numbers)
    print(got == expected ? "PASS" : "FAIL", numbers, "→", got, "expected", expected)
}
```
:::

::: Pattern and cue
**Binary search for the point where the order breaks.** The cues are *"sorted … rotated"* and *"O(log n)"*. A rotated sorted list climbs, drops once, then climbs again; the minimum is right after the drop. Comparing the middle with the right end tells you which side of the middle the drop is on.
:::

::: Approach
Keep two markers at the ends of the part that must contain the minimum. Look at the middle entry and compare it with the entry at the right marker. If the middle is bigger, the list drops somewhere between them, so the minimum is strictly to the right of the middle. If the middle is smaller, everything from the middle to the right end climbs in order, so the minimum is the middle itself or something to its left — keep the middle. When the markers meet, they sit on the minimum.

Time O(log n): the range halves each step. Space O(1).
:::

::: Swift solution
```swift
func findMin(_ numbers: [Int]) -> Int {
    var low = 0
    var high = numbers.count - 1

    while low < high {
        let mid = low + (high - low) / 2
        if numbers[mid] > numbers[high] {
            low = mid + 1                    // the drop is to the right of mid
        } else {
            high = mid                       // mid itself may be the minimum
        }
    }
    return numbers[low]
}
```

Compare with the **right** end, not the left. In an unrotated list like `[2, 4, 6, 8]`, comparing `mid` with the left end can't tell "the drop is to the right" from "there is no drop", and the search walks away from the minimum. The right end is always on the climb that contains the minimum, so the comparison never lies.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, five more (two entries in both orders, a three-entry rotation, the minimum at the very end, all negative numbers), and 5,000 random rotations of random sorted lists checked against `min()`.
:::

::: Walk it through
**`[4, 5, 6, 1, 2, 3]`**

| low | high | mid | numbers[mid] vs numbers[high] | Action |
|---|---|---|---|---|
| 0 | 5 | 2 | 6 > 3 | low = 3 |
| 3 | 5 | 4 | 2 < 3 | high = 4 |
| 3 | 4 | 3 | 1 < 2 | high = 3 |
| 3 | 3 | — | low == high | return numbers[3] = 1 |

**`[2, 4, 6, 8]`** — mid 1: 4 < 8, high = 1. mid 0: 2 < 4, high = 0. Return 2. Every comparison says "the right side climbs", so the search slides to the left end, which is the minimum of an unrotated list.
:::

::: The Swift trap
**`numbers.min()!` is correct, short, and not the answer.** It's worth saying first, as the baseline: `min()` comes from `Sequence`, walks every element (O(n)), and returns an optional because the sequence might be empty — hence the `!`, which is safe only because the statement promises at least one number. Then explain why the statement asks for O(log n) and write the loop. The Swift detail inside the loop is that `high = mid` (not `mid - 1`) is what keeps a possible answer in range, and `low < high` (not `<=`) is what stops the loop from spinning forever once `low == high`.
:::

::: What they ask next
- **"Return the index of the minimum."** → Return `low` instead of `numbers[low]`; it's also the number of positions the list was rotated.
- **"The list may contain duplicates."** → When `numbers[mid] == numbers[high]`, you can't tell the side; drop `high` by one and continue. Worst case O(n), e.g. `[1, 1, 1, 0, 1]`.
- **"Find the maximum instead."** → It sits just before the minimum: the entry at `(minIndex - 1 + count) % count`.
:::
