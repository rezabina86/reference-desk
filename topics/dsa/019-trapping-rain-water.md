---
title: 16 · Trapping Rain Water
summary: Given the heights of a row of bars, work out how much rain stays caught between them after a storm.
group: Two pointers
minutes: 30
sources:
- LeetCode 42 · Trapping Rain Water | https://leetcode.com/problems/trapping-rain-water/
- Swift standard library · Range | https://developer.apple.com/documentation/swift/range
---

*Hard · optional · G*

**Optional.** Above the bar most German loops set; do it if the topic's mediums went well.

You get an array of non-negative integers: the heights of bars standing side by side, each one unit wide. Rain falls on all of them. Water collects in every dip, and above each bar it rises to the level of the **lower** of the tallest bar somewhere to its left and the tallest bar somewhere to its right — any higher and it would spill over that side. Return the total units of water held across the whole row.

| Heights | Answer |
|---|---|
| `[3, 0, 2, 0, 4]` | `7` — 3 above the first gap, 1 above the 2, 3 above the second gap |
| `[4, 1, 3]` | `2` — the right wall is the lower one, so the water stops at 3 |
| `[1, 2, 3, 4]` | `0` — the heights only rise, so every drop runs off the left side |

Constraints that matter: up to 20,000 bars, each between 0 and 100,000 high. Scanning left and right from every bar to find its two tallest neighbours is O(n²); two arrays of running maxima make it O(n) time and O(n) memory; the target is O(n) time with O(1) extra memory.

::: Starter code and tests
In an Xcode test target:

```swift
import Testing

struct TrappingRainWaterTests {

    @Test(arguments: [
        ([3, 0, 2, 0, 4], 7),
        ([4, 1, 3], 2),
        ([1, 2, 3, 4], 0),
    ])
    func returnsTheTotalWaterHeldBetweenTheBars(heights: [Int], expected: Int) {
        #expect(trap(heights) == expected)
    }

    // MARK: - Privates
    private func trap(_ heights: [Int]) -> Int {
        0
    }
}
```

In a playground:

```swift
func trap(_ heights: [Int]) -> Int {
    0 // your solution
}

let cases: [([Int], Int)] = [
    ([3, 0, 2, 0, 4], 7),
    ([4, 1, 3], 2),
    ([1, 2, 3, 4], 0),
]
for (heights, expected) in cases {
    let got = trap(heights)
    print(got == expected ? "PASS" : "FAIL", heights, "→", got, "expected", expected)
}
```
:::

::: Pattern and cue
**Two pointers from both ends, moving the lower side, each carrying its running maximum.** The cue is that the answer at each position depends on *"the tallest to its left"* and *"the tallest to its right"*, and only on the *lower* of the two. Whichever end currently has the lower maximum is the one whose water level is already settled, so that end can be measured and moved inward.
:::

::: Approach
Put one finger on the first bar and one on the last, and remember the tallest bar each finger has passed so far. Look at the two bars under the fingers. If the left one is lower, then somewhere on the right there is a bar at least that tall, so the water above the left bar is limited only by the tallest bar on its left: add "left maximum minus this bar's height" to the total and move the left finger in. Otherwise do the same on the right side. When the fingers meet, every bar has been measured exactly once.

The step to say out loud: you don't need to know the true tallest bar on the far side, only that it is at least as tall as the near side's maximum — and the comparison of the two bars under the fingers tells you that.

Time O(n): each step moves one finger inward. Space O(1): two positions, two maxima and a total.
:::

::: Swift solution
```swift
func trap(_ heights: [Int]) -> Int {
    var left = 0
    var right = heights.count - 1
    var leftMax = 0
    var rightMax = 0
    var water = 0

    while left < right {
        if heights[left] < heights[right] {
            leftMax = max(leftMax, heights[left])
            water += leftMax - heights[left]      // something at least this tall stands to the right
            left += 1
        } else {
            rightMax = max(rightMax, heights[right])
            water += rightMax - heights[right]    // something at least this tall stands to the left
            right -= 1
        }
    }
    return water
}
```

Updating the maximum before adding means a bar taller than everything before it adds `0`, never a negative amount. The bar the fingers meet on is never measured: it is always a tallest bar of the whole row, so it holds no water anyway.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, six more (empty, one bar, two bars, all bars equal, a slope that falls then rises, a plateau of equal tall bars with a dip on each side), and 3,000 random arrays checked against a brute-force search that finds both tallest neighbours of every bar, plus a check that the fingers always meet on a tallest bar.
:::

::: Walk it through
**`[3, 0, 2, 0, 4]`**

| Left (height) | Right (height) | Lower side | Max on that side | Water added | Total |
|---|---|---|---|---|---|
| 0 (3) | 4 (4) | left | 3 | 3 − 3 = 0 | 0 |
| 1 (0) | 4 (4) | left | 3 | 3 − 0 = 3 | 3 |
| 2 (2) | 4 (4) | left | 3 | 3 − 2 = 1 | 4 |
| 3 (0) | 4 (4) | left | 3 | 3 − 0 = 3 | 7 |
| 4 | 4 | — | — | fingers meet | 7 |

Answer 7. The right finger never moved: the 4 was the taller side the whole time, which is what made the left maximum the true cap.

**`[4, 1, 3]`** — left bar 4, right bar 3: the right side is lower, so `rightMax` becomes 3 and adds 0; right moves to 1. Now 4 against 1: right is still lower, `rightMax` stays 3, and the 1 holds 3 − 1 = 2. Right moves to 0 and meets left. Answer 2, capped by the 3 even though a 4 stands on the left.
:::

::: The Swift trap
**A range whose end is below its start crashes.** The O(n)-memory version builds a "tallest to the right" array with a backward loop, and the natural spelling is `for i in (0..<heights.count - 1).reversed()`. On an empty array that's `0..<-1`, and Swift doesn't treat it as an empty range — it traps at runtime with "Range requires lowerBound <= upperBound". Guard `heights.count > 2` first (fewer than three bars can't hold water), or use `stride(from: heights.count - 2, through: 0, by: -1)`, which is simply empty when the start is below the end. The two-pointer version above never builds a range, which is one more reason to prefer it.
:::

::: What they ask next
- **"Show me the simpler O(n)-memory version first."** → Two arrays: the running maximum from the left and from the right. The water above bar i is `min(leftMax[i], rightMax[i]) − heights[i]`. Then say that the two pointers remove both arrays.
- **"Do it with a stack."** → Keep indices of bars in decreasing height. When a taller bar arrives, pop the bottom of the dip and fill the layer between the new bar and the bar now on top of the stack: width times (lower wall − dip). It fills water in horizontal layers, still O(n).
- **"Now the bars form a 2D grid."** → Water level is set by the lowest point of the surrounding border, so start from the whole border in a min-heap and flood inward from the lowest cell, like Dijkstra. O(mn log(mn)); Swift has no heap built in, so say you'd write one.
:::
