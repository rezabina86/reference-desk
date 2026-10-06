---
title: 14 · Container With Most Water
summary: Given a row of vertical walls, pick the two that hold the most water between them.
group: Two pointers
minutes: 25
sources:
- LeetCode 11 · Container With Most Water | https://leetcode.com/problems/container-with-most-water/
---

*Medium · G*

You get an array of non-negative integers. Each entry is the height of a vertical wall standing at that position, one unit apart from its neighbours. Pick any two walls: together with the ground they form a tank, and the water it holds is as high as the **shorter** of the two walls and as wide as the distance between them. The walls in between don't get in the way. Return the largest amount of water any pair can hold.

| Heights | Answer |
|---|---|
| `[2, 7, 3, 6, 4, 8, 1]` | `28` — the 7 at position 1 and the 8 at position 5: height 7, width 4 |
| `[5, 1, 1, 1, 5]` | `20` — the two outer walls: height 5, width 4 |
| `[4, 4]` | `4` — only one pair, height 4, width 1 |

Constraints that matter: between 2 and 100,000 walls, each between 0 and 10,000 high. Trying every pair is O(n²), about five billion pairs at the top end; the target is one pass, O(n).

::: Starter code and tests
In an Xcode test target:

```swift
import Testing

struct ContainerWithMostWaterTests {

    @Test(arguments: [
        ([2, 7, 3, 6, 4, 8, 1], 28),
        ([5, 1, 1, 1, 5], 20),
        ([4, 4], 4),
    ])
    func returnsTheLargestAreaTwoWallsCanHold(heights: [Int], expected: Int) {
        #expect(maxArea(heights) == expected)
    }

    // MARK: - Privates
    private func maxArea(_ heights: [Int]) -> Int {
        0
    }
}
```

In a playground:

```swift
func maxArea(_ heights: [Int]) -> Int {
    0 // your solution
}

let cases: [([Int], Int)] = [
    ([2, 7, 3, 6, 4, 8, 1], 28),
    ([5, 1, 1, 1, 5], 20),
    ([4, 4], 4),
]
for (heights, expected) in cases {
    let got = maxArea(heights)
    print(got == expected ? "PASS" : "FAIL", heights, "→", got, "expected", expected)
}
```
:::

::: Pattern and cue
**Two pointers from both ends, moving the weaker side.** The cue is *"two"* entries of an array whose score depends on the *distance between them* and the *smaller* of the two. Start with the widest pair — the two outer walls — and walk inward. Every step inward loses one unit of width, so the only step that can ever pay off is one that might raise the shorter wall.
:::

::: Approach
Put one finger on the first wall and one on the last. Work out the water between them and keep the best seen so far. Then move the finger that sits on the **shorter** wall one step inward, and repeat until the fingers meet.

Why moving the shorter wall is safe: pair the shorter wall with any wall closer in than the other finger, and the water is capped by that shorter wall's height while the width only shrinks — every one of those pairs is worse than the one just measured. So the shorter wall has nothing left to offer, and it can be dropped. Moving the taller wall instead can never help, because the shorter wall still caps the height. On a tie either finger can move: neither wall can do better with anything in between.

Time O(n): each step moves one finger, and they meet after n − 1 steps. Space O(1): two indices and a running best.
:::

::: Swift solution
```swift
func maxArea(_ heights: [Int]) -> Int {
    var left = 0
    var right = heights.count - 1
    var best = 0

    while left < right {
        let area = min(heights[left], heights[right]) * (right - left)
        best = max(best, area)
        if heights[left] < heights[right] {
            left += 1          // the shorter wall caps every narrower pair it's part of
        } else {
            right -= 1
        }
    }
    return best
}
```

Empty and single-wall input return 0 without a guard: `right` starts at −1 or 0, the loop condition fails, and nothing is subscripted.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, six more (empty, one wall, all walls equal, two zero walls, strictly rising heights, two walls at the 10,000 maximum), and 3,000 random arrays checked against a brute-force O(n²) search over every pair.
:::

::: Walk it through
**`[2, 7, 3, 6, 4, 8, 1]`**

| Left (height) | Right (height) | Water | Best | Move |
|---|---|---|---|---|
| 0 (2) | 6 (1) | 1 × 6 = 6 | 6 | right is shorter → right |
| 0 (2) | 5 (8) | 2 × 5 = 10 | 10 | left is shorter → left |
| 1 (7) | 5 (8) | 7 × 4 = 28 | 28 | left |
| 2 (3) | 5 (8) | 3 × 3 = 9 | 28 | left |
| 3 (6) | 5 (8) | 6 × 2 = 12 | 28 | left |
| 4 (4) | 5 (8) | 4 × 1 = 4 | 28 | left → fingers meet |

Answer 28, after six measurements instead of twenty-one.

**`[4, 4]`** — one measurement: 4 × 1 = 4. The walls tie, the right finger moves, the fingers meet. Answer 4.
:::

::: The Swift trap
**A slice keeps its parent's indices.** The follow-up "now do it for walls 3 to 9 only" tempts you to pass `heights[3...9]` into a version that takes `ArraySlice<Int>` or any `Collection`. Starting `left` at `0` then reads outside the range, or traps, because the slice's first index is 3, not 0. Start from `heights.startIndex` and `heights.index(before: heights.endIndex)`, and measure width with `heights.distance(from:to:)` — or copy into `Array(...)` first and say why. On a plain `[Int]` the version above is correct; the moment the signature widens, the integer arithmetic is the bug.
:::

::: What they ask next
- **"Prove the greedy step is right."** → Every pair that includes the shorter wall and a wall inside the fingers is no taller and strictly narrower than the pair just measured, so discarding that wall loses nothing. That one sentence is the answer they want.
- **"The walls aren't evenly spaced — you get their x positions, sorted."** → Same algorithm with width `x[right] − x[left]`. Width still shrinks every step inward, so the argument still holds.
- **"How is this different from trapping rain water?"** → There, every wall in between matters and water sits over each position; that needs the running maximum from both sides, not a best pair. Different problem, same two-finger shape: it is problem 16.
:::
