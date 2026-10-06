---
title: 71 · Jump Game
summary: Standing on the first square of a row, where each square says how far you may jump from it, decide whether you can land on the last square.
group: Greedy
minutes: 20
sources:
- LeetCode 55 · Jump Game | https://leetcode.com/problems/jump-game/
- The Swift Programming Language · For-In Loops | https://docs.swift.org/swift-book/documentation/the-swift-programming-language/controlflow/#For-In-Loops
---

*Medium · G*

You stand on the first square of a row of squares. Each square holds a number: the **longest** jump forward you may make from it — any shorter jump, including none, is also allowed. Return `true` if some sequence of jumps lands you on the last square, and `false` otherwise. A row of one square means you're already there.

| Squares | Answer |
|---|---|
| `[2, 0, 3, 0, 0, 1]` | `true` — jump 2 to the 3, then 3 to the end |
| `[1, 1, 0, 2]` | `false` — every path stops on the 0 |
| `[0]` | `true` — the first square is the last |

Constraints that matter: up to 10,000 squares, each value from 0 to 100,000. Trying every sequence of jumps explodes; marking every reachable square from every square is O(n²). The target is one pass, O(n).

::: Starter code and tests
In an Xcode test target:

```swift
import Testing

struct JumpGameTests {

    @Test(arguments: [
        ([2, 0, 3, 0, 0, 1], true),
        ([1, 1, 0, 2], false),
        ([0], true),
    ])
    func decidesWhetherTheLastSquareCanBeReached(steps: [Int], expected: Bool) {
        #expect(canJump(steps) == expected)
    }

    // MARK: - Privates
    private func canJump(_ steps: [Int]) -> Bool {
        false
    }
}
```

In a playground:

```swift
func canJump(_ steps: [Int]) -> Bool {
    false // your solution
}

let cases: [([Int], Bool)] = [
    ([2, 0, 3, 0, 0, 1], true),
    ([1, 1, 0, 2], false),
    ([0], true),
]
for (steps, expected) in cases {
    let got = canJump(steps)
    print(got == expected ? "PASS" : "FAIL", steps, "→", got, "expected", expected)
}
```
:::

::: Pattern and cue
**Greedy farthest frontier.** The cue is *"can you reach"* the end with *forward* moves of *up to* some length. Because any shorter jump is allowed, every square up to the farthest reachable one is also reachable — so the whole state is a single number, the frontier.
:::

::: Approach
Walk the squares from left to right, keeping track of the farthest square you know you can reach. At each square, first check that you can actually stand on it: if it lies beyond the farthest reachable square, there's a gap no jump crosses, and the answer is `false`. Otherwise, from here you could get as far as this square's position plus its number; if that's farther than before, move the frontier out. As soon as the frontier reaches the last square, the answer is `true`.

Time O(n): one pass. Space O(1): one number.
:::

::: Swift solution
```swift
func canJump(_ steps: [Int]) -> Bool {
    var reach = 0
    for (index, step) in steps.enumerated() {
        if index > reach { return false }        // this square can't be reached
        reach = max(reach, index + step)
        if reach >= steps.count - 1 { return true }
    }
    return true
}
```

The check `index > reach` comes **before** using the square's number. Use the number first and a square you can never reach would push the frontier out on your behalf — `[0, 5]` would wrongly return `true`.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, four more (`[0, 1]`, a first square that reaches past the end, a 0 in front of the last square, `[1, 0]`), and 3,000 random rows checked against a brute force that marks every square reachable from every reachable square.
:::

::: Walk it through
**`[2, 0, 3, 0, 0, 1]`** — the last square is index 5.

| Index | Value | Reachable? | Frontier after | Done? |
|---|---|---|---|---|
| 0 | 2 | 0 ≤ 0, yes | 2 | no |
| 1 | 0 | 1 ≤ 2, yes | 2 | no |
| 2 | 3 | 2 ≤ 2, yes | 5 | 5 ≥ 5: `true` |

**`[1, 1, 0, 2]`** — the last square is index 3. The frontier goes 1, 2, then stays 2 at the 0. At index 3, 3 > 2: that square can't be reached, so `false`. The 2 on it never matters.
:::

::: The Swift trap
**`for i in 0...reach` doesn't grow when `reach` does.** The natural way to say "visit every square up to the frontier" is a loop over `0...reach`, updating `reach` inside the body. In C, the condition `i <= reach` is re-checked every time round; in Swift, the range `0...reach` is built once, when the loop starts, with whatever `reach` was then. On `[1, 1, 1, 0]` it visits only square 0 and stops with the frontier at 1 — measured on Swift 6.4 — so the code answers `false` for a row that's solvable. Loop over all the indices and check `index > reach` explicitly, as above, or use a `while` loop whose condition reads `reach` each time.
:::

::: What they ask next
- **"Fewest jumps to reach the end, assuming you can."** → Jump Game II: BFS in disguise. Treat the squares reachable with k jumps as one window; the next window ends at the farthest point any square in it reaches. Count windows. Still O(n).
- **"Walk it backwards instead."** → Keep a `goal` starting at the last square; moving left, if `i + steps[i] >= goal`, the goal moves to `i`. The answer is whether the goal reaches 0. Same O(n), and some find it easier to argue.
- **"Why not dynamic programming?"** → It works — `canReach[i]` from all earlier squares — but it's O(n²) here, and the frontier proves that one number already holds everything the table would.
:::
