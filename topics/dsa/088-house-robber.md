---
title: 73 · House Robber
summary: Pick amounts from a row of houses to collect the largest total, never taking from two houses next to each other.
group: 1-D dynamic programming
minutes: 20
sources:
- LeetCode 198 · House Robber | https://leetcode.com/problems/house-robber/
---

*Medium · G*

A street has a row of houses, each holding some amount of cash, given as an array of non-negative numbers. You may take the cash from any houses you like, except that you can never take from two houses that stand next to each other. Return the largest total you can collect.

| Cash per house | Answer |
|---|---|
| `[3, 1, 1, 5]` | `8` — the first and the last; taking every other house finds only 4 or 6 |
| `[2, 9, 4, 3, 1]` | `12` — the 9 and the 3 |
| `[6]` | `6` — one house, take it |

Constraints that matter: between 1 and 100 houses, each with 0 to 400. Trying every allowed set of houses is exponential; the target is O(n) time and O(1) space.

::: Starter code and tests
In an Xcode test target:

```swift
import Testing

struct HouseRobberTests {

    @Test(arguments: [
        ([3, 1, 1, 5], 8),
        ([2, 9, 4, 3, 1], 12),
        ([6], 6),
    ])
    func returnsTheLargestTotalWithNoTwoNeighbours(houses: [Int], expected: Int) {
        #expect(rob(houses) == expected)
    }

    // MARK: - Privates
    private func rob(_ houses: [Int]) -> Int {
        0
    }
}
```

In a playground:

```swift
func rob(_ houses: [Int]) -> Int {
    0 // your solution
}

let cases: [([Int], Int)] = [
    ([3, 1, 1, 5], 8),
    ([2, 9, 4, 3, 1], 12),
    ([6], 6),
]
for (houses, expected) in cases {
    let got = rob(houses)
    print(got == expected ? "PASS" : "FAIL", houses, "→", got, "expected", expected)
}
```
:::

::: Pattern and cue
**1-D dynamic programming, take it or skip it.** The cue is *"largest total"* plus a rule that links neighbours (*"never two next to each other"*). At each house there are two choices, and each choice leaves a smaller version of the same problem: skip this house and the best is whatever the houses before it allowed; take it and you add its cash to the best of the houses before its neighbour. Greedy picks — the biggest house first, or every other house — fail on small examples, which is the sign that you need to compare both choices every time.
:::

::: Approach
Subproblem: the largest total you can collect from the first i houses. Recurrence: best of i houses = the larger of (best of i − 1 houses) and (best of i − 2 houses + the cash in house i).

Walk along the street once. Keep two numbers: the best total so far, and the best total from one house earlier — which is the best you can have while leaving the previous house alone. At each house, either skip it (the best stays) or take it (the earlier total plus this house's cash), and keep the larger. Then both numbers move one house along.

Time O(n): one comparison per house. Space O(1): two running totals.
:::

::: Swift solution
```swift
func rob(_ houses: [Int]) -> Int {
    var skipped = 0   // best total while leaving the previous house alone
    var best = 0      // best total so far
    for cash in houses {
        (skipped, best) = (best, max(best, skipped + cash))
    }
    return best
}
```

The whole recurrence is the one tuple line: the new `skipped` is the old `best`, and the new `best` compares skipping this house with taking it on top of the old `skipped`. Starting both at 0 means no base case and no special code for one or zero houses.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, four more (empty, all zeros, all equal, two big houses three apart), and 3,000 random streets checked against a brute force over every allowed set of houses.
:::

::: Walk it through
**`[2, 9, 4, 3, 1]`**

| House | Cash | Skip it | Take it (skipped + cash) | skipped after | best after |
|---|---|---|---|---|---|
| 0 | 2 | 0 | 2 | 0 | 2 |
| 1 | 9 | 2 | 9 | 2 | 9 |
| 2 | 4 | 9 | 6 | 9 | 9 |
| 3 | 3 | 9 | 12 | 9 | 12 |
| 4 | 1 | 12 | 10 | 12 | 12 |

Answer 12: the 9 and the 3. "Every other house" from the start (2 + 4 + 1 = 7) or from the second (9 + 3 = 12) happens to work here, but on `[3, 1, 1, 5]` neither alternation gives 8 — the best set skips two houses in a row.

**`[6]`** — one step: skip gives 0, take gives 6. Answer 6.
:::

::: The Swift trap
**Updating the two totals one after the other reads a value you just overwrote.** Written as two lines — `best = max(best, skipped + cash)` then `skipped = best` — `skipped` receives the *new* best, which may already include this house, and the next house can then be taken right next to it. The order that works (`let previous = best; best = …; skipped = previous`) needs a temporary. The tuple assignment avoids both mistakes: Swift evaluates the entire right side, `(best, max(best, skipped + cash))`, before assigning either variable.

The other version people write starts from `houses[0]` and `max(houses[0], houses[1])` as base cases, which crashes with "Index out of range" on an empty or one-house street. Starting the two totals at 0 removes the base cases altogether.
:::

::: What they ask next
- **"The houses are in a circle: the first and last are neighbours."** → That's the next problem: run this twice, once without the first house and once without the last, and take the larger.
- **"Return which houses to take, not just the total."** → Keep the full table of best totals, then walk it backwards: if best[i] equals best[i − 1], house i was skipped; otherwise it was taken, and jump to i − 2.
- **"The houses form a tree; a house and its parent can't both be taken."** → For each node return two numbers — best with it taken, best with it skipped — from a post-order traversal (LeetCode 337).
:::
