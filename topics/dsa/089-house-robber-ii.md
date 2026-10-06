---
title: 74 · House Robber II
summary: Pick amounts from houses arranged in a circle to collect the largest total, never taking from two neighbours, where the first and last houses are neighbours too.
group: 1-D dynamic programming
minutes: 20
sources:
- LeetCode 213 · House Robber II | https://leetcode.com/problems/house-robber-ii/
- Swift standard library · ArraySlice | https://developer.apple.com/documentation/swift/arrayslice
---

*Medium · G*

The same street as the previous problem, but now the houses stand in a circle: the last house is next to the first. You may take the cash from any houses except two that are next to each other, and the first and last count as next to each other. Return the largest total you can collect.

| Cash per house | Answer |
|---|---|
| `[4, 2, 5]` | `5` — in a ring of three every pair touches, so one house only |
| `[1, 6, 2, 3]` | `9` — the 6 and the 3 |
| `[7]` | `7` — a single house has no neighbours to clash with |

Constraints that matter: between 1 and 100 houses, each with 0 to 1,000. The target is O(n) time and O(1) extra space — two passes of the previous problem.

::: Starter code and tests
In an Xcode test target:

```swift
import Testing

struct HouseRobberIITests {

    @Test(arguments: [
        ([4, 2, 5], 5),
        ([1, 6, 2, 3], 9),
        ([7], 7),
    ])
    func returnsTheLargestTotalAroundTheCircle(houses: [Int], expected: Int) {
        #expect(robCircle(houses) == expected)
    }

    // MARK: - Privates
    private func robCircle(_ houses: [Int]) -> Int {
        0
    }
}
```

In a playground:

```swift
func robCircle(_ houses: [Int]) -> Int {
    0 // your solution
}

let cases: [([Int], Int)] = [
    ([4, 2, 5], 5),
    ([1, 6, 2, 3], 9),
    ([7], 7),
]
for (houses, expected) in cases {
    let got = robCircle(houses)
    print(got == expected ? "PASS" : "FAIL", houses, "→", got, "expected", expected)
}
```
:::

::: Pattern and cue
**1-D dynamic programming, with the circle broken into two lines.** The cue is the previous problem's *"largest total, no two neighbours"* plus *"in a circle"*. A circle has no start, which is what makes a left-to-right recurrence awkward. But the first and last house can't both be taken, so at least one of them is left out — and with either one removed, the circle becomes a plain row.
:::

::: Approach
Subproblem and recurrence: exactly those of House Robber — the best total from the first i houses of a row is the larger of (best of i − 1) and (best of i − 2 + house i) — applied to two rows.

Any good plan leaves out the first house or the last house (or both). So solve the row "every house except the last" and the row "every house except the first" with the previous problem's two running totals, and return the larger answer. A plan that leaves out both ends is included in either row, so nothing is missed. One house on its own is the exception: removing an end leaves nothing, so return its cash directly.

Time O(n): two passes. Space O(1): the two rows are views into the same array, not copies.
:::

::: Swift solution
```swift
func robCircle(_ houses: [Int]) -> Int {
    guard houses.count > 1 else { return houses.first ?? 0 }
    return max(robRow(houses.dropLast()), robRow(houses.dropFirst()))
}

func robRow(_ houses: ArraySlice<Int>) -> Int {
    var skipped = 0   // best total while leaving the previous house alone
    var best = 0      // best total so far
    for cash in houses {                        // iterate; never index from 0
        (skipped, best) = (best, max(best, skipped + cash))
    }
    return best
}
```

`dropLast()` and `dropFirst()` return `ArraySlice` views in O(1), so neither pass copies the array. The guard handles the single house, the one case where both rows would be empty.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, four more (empty, two houses, `[5, 1, 1, 5]` where the two 5s touch around the ring, all equal), and 3,000 random rings checked against a brute force over every allowed set of houses.
:::

::: Walk it through
**`[1, 6, 2, 3]`**

| Row | Houses | Running (skipped, best) after each house | Best |
|---|---|---|---|
| without the last | 1, 6, 2 | (0, 1) → (1, 6) → (6, 6) | 6 |
| without the first | 6, 2, 3 | (0, 6) → (6, 6) → (6, 9) | 9 |

Answer max(6, 9) = 9.

**`[5, 1, 1, 5]`** — on a straight street the answer would be 10, the two 5s. Here they are neighbours around the ring. Without the last house the row `5, 1, 1` gives 6; without the first, `1, 1, 5` gives 6. Answer 6 — the brute force agrees.
:::

::: The Swift trap
**A slice keeps the parent array's indices.** `houses.dropFirst()` is an `ArraySlice` whose first index is **1**, not 0. If the helper is written C-style — `houses[0]`, `houses[1]`, `for i in 2..<houses.count` — the first pass happens to work and the second reads the wrong houses or traps with "Index out of range". Three safe ways out: iterate with `for cash in houses` as above, so indices never appear; use `houses.startIndex` and `houses.index(after:)`; or convert with `Array(houses.dropFirst())` and accept the O(n) copy, saying why. Writing the helper to take `[Int]` and calling it with a slice doesn't compile, which is how many people find out about the difference mid-interview.
:::

::: What they ask next
- **"Why doesn't leaving out both ends get missed?"** → A plan that skips both the first and last house is a valid plan for either row, so it's counted in both maxima already.
- **"Do it in one pass."** → Run the two sets of running totals side by side in the same loop, feeding house i to the first set when i < n − 1 and to the second when i > 0. Same complexity; only worth it if asked.
- **"Houses are on a grid and you can't take two that share a side."** → No longer a 1-D recurrence: it's a maximum-weight independent set, and on a general grid you'd need DP over rows with a bitmask of the previous row (fine for narrow grids only).
:::
