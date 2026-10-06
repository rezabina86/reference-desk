---
title: 72 · Climbing Stairs
summary: Count the different orders of one-step and two-step moves that take you up a staircase of n steps.
group: 1-D dynamic programming
minutes: 15
sources:
- LeetCode 70 · Climbing Stairs | https://leetcode.com/problems/climbing-stairs/
- Swift standard library · Int.addingReportingOverflow(_:) | https://developer.apple.com/documentation/swift/int/addingreportingoverflow(_:)
---

*Easy · G — the warm-up for this block*

A staircase has n steps. Each move takes you up either one step or two. Count how many different sequences of moves land you exactly on the top step. Two sequences are different if they differ anywhere: one-then-two and two-then-one are two ways.

| Steps | Answer |
|---|---|
| `1` | `1` — a single one-step move |
| `4` | `5` — 1+1+1+1, 1+1+2, 1+2+1, 2+1+1, 2+2 |
| `6` | `13` |

Constraints that matter: n is between 1 and 45. Listing every sequence is exponential — around 1.8 billion of them at n = 45 — so the target is O(n) time, and O(1) space is easy to reach.

::: Starter code and tests
In an Xcode test target:

```swift
import Testing

struct ClimbingStairsTests {

    @Test(arguments: [
        (1, 1),
        (4, 5),
        (6, 13),
    ])
    func countsTheDistinctMoveSequencesToTheTop(steps: Int, expected: Int) {
        #expect(climbStairs(steps) == expected)
    }

    // MARK: - Privates
    private func climbStairs(_ steps: Int) -> Int {
        0
    }
}
```

In a playground:

```swift
func climbStairs(_ steps: Int) -> Int {
    0 // your solution
}

let cases: [(Int, Int)] = [
    (1, 1),
    (4, 5),
    (6, 13),
]
for (steps, expected) in cases {
    let got = climbStairs(steps)
    print(got == expected ? "PASS" : "FAIL", steps, "→", got, "expected", expected)
}
```
:::

::: Pattern and cue
**1-D dynamic programming, counting.** The cue is *"how many different ways"* combined with a small set of moves that can be combined in any order. Every way to reach step i ended with either a one-step move from i − 1 or a two-step move from i − 2, and those two groups never overlap — so the count for i is the sum of two smaller counts.
:::

::: Approach
Subproblem: the number of ways to stand on step i. Recurrence: ways to step i = ways to step i − 1 + ways to step i − 2, because the last move was either one step or two.

Fill these counts from the bottom up. Standing on the ground (step 0) has one way — doing nothing — and step 1 has one way. Every later step adds the two counts just below it. Since each count only needs the two before it, keep two numbers and slide them up the staircase instead of keeping a whole list. (These are the Fibonacci numbers, shifted by one.)

Time O(n): one addition per step. Space O(1): two running counts.
:::

::: Swift solution
```swift
func climbStairs(_ steps: Int) -> Int {
    guard steps > 1 else { return 1 }
    var twoBelow = 1   // ways to stand on step 0: one, doing nothing
    var oneBelow = 1   // ways to reach step 1
    for _ in 2...steps {
        (twoBelow, oneBelow) = (oneBelow, oneBelow + twoBelow)
    }
    return oneBelow
}
```

The tuple assignment moves both counts up one step at once: the right side is evaluated completely before either variable changes, so there's no temporary variable and no chance of reading a count you just overwrote.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, four more (0, 2, 3, and 45 → 1,836,311,903, the largest allowed), and every n from 0 to 25 checked against the plain exponential recursion.
:::

::: Walk it through
**n = 6**

| Step | twoBelow | oneBelow (ways to this step) |
|---|---|---|
| start | 1 | 1 |
| 2 | 1 | 2 |
| 3 | 2 | 3 |
| 4 | 3 | 5 |
| 5 | 5 | 8 |
| 6 | 8 | 13 |

Answer 13.

**n = 1** — the guard returns 1 before any range is built. Without it, `2...1` would be a range whose end is below its start, and Swift traps on it.
:::

::: The Swift trap
**The count overflows long before the recursion finishes, and Swift traps instead of wrapping.** The counts are Fibonacci numbers, which grow by about 1.6× per step. With 64-bit `Int` the limit is n = 91; at n = 92 the addition passes `Int.max` and the program stops with an overflow trap. Within the stated n ≤ 45 this never fires, but "what if n is 1,000?" is a common follow-up — the answer is that the statement would then ask for the count modulo 1,000,000,007, and you take `% 1_000_000_007` after every addition. Don't reach for `&+`: it wraps silently and gives a wrong number instead of a crash.

The second trap is the first solution most people write, `climbStairs(n - 1) + climbStairs(n - 2)` with no memo. It's correct and it's O(1.6ⁿ): at n = 45 it makes billions of calls. Say why it's slow (the same step is solved again and again) before you fix it.
:::

::: What they ask next
- **"You may climb 1, 2 or 3 steps — or any step size in a given list."** → Same recurrence over the allowed sizes: ways[i] = sum of ways[i − s] for each size s ≤ i. O(n·k) time, and a window of the last max(s) counts.
- **"Some steps are broken and can't be stood on."** → Set ways[i] = 0 for a broken step and keep going; the recurrence handles the rest.
- **"Can you do better than O(n)?"** → Yes, with matrix exponentiation of [[1,1],[1,0]] in O(log n) — mention it, but nobody expects it written for this bar.
:::
