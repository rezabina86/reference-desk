---
title: 59 · Combination Sum
summary: Given a set of different positive numbers and a target, list every way to reach the target by adding numbers from the set, where each number may be used as often as you like.
group: Backtracking
minutes: 25
sources:
- LeetCode 39 · Combination Sum | https://leetcode.com/problems/combination-sum/
- Swift standard library · ArraySlice | https://developer.apple.com/documentation/swift/arrayslice
---

*Medium · G*

You get an array of different positive integers, the candidates, and a positive target. Return every combination of candidates that adds up to exactly the target. A candidate may be used any number of times. Two combinations are the same if they use the same candidates the same number of times, whatever the order: `[3, 5]` and `[5, 3]` are one combination and must appear once. The combinations can come back in any order, and so can the numbers inside each one.

| Candidates | Target | Answer |
|---|---|---|
| `[3, 5, 2]` | `8` | `[[2, 2, 2, 2], [2, 3, 3], [3, 5]]` |
| `[4, 6]` | `12` | `[[4, 4, 4], [6, 6]]` — `[4, 4, 4]` reuses one candidate three times |
| `[7]` | `3` | `[]` — nothing fits, the answer is an empty list |

Constraints that matter: up to 30 candidates between 2 and 40, all different; the target is at most 40; fewer than 150 combinations ever exist. The search is exponential in the target; the goal is to never produce the same combination twice and to stop going deeper the moment the sum overshoots. Because order is free at both levels, the tests sort each combination and then the list before comparing.

::: Starter code and tests
In an Xcode test target:

```swift
import Testing

struct CombinationSumTests {

    @Test(arguments: [
        ([3, 5, 2], 8, [[2, 2, 2, 2], [2, 3, 3], [3, 5]]),
        ([4, 6], 12, [[4, 4, 4], [6, 6]]),
        ([7], 3, []),
    ])
    func returnsEveryWayToReachTheTargetReusingCandidates(candidates: [Int], target: Int, expected: [[Int]]) {
        #expect(normalised(combinationSum(candidates, target)) == normalised(expected))
    }

    // MARK: - Privates
    private func combinationSum(_ candidates: [Int], _ target: Int) -> [[Int]] {
        []
    }

    private func normalised(_ combinations: [[Int]]) -> [[Int]] {
        combinations.map { $0.sorted() }.sorted { $0.lexicographicallyPrecedes($1) }
    }
}
```

In a playground:

```swift
func combinationSum(_ candidates: [Int], _ target: Int) -> [[Int]] {
    [] // your solution
}

func normalised(_ combinations: [[Int]]) -> [[Int]] {
    combinations.map { $0.sorted() }.sorted { $0.lexicographicallyPrecedes($1) }
}

let cases: [([Int], Int, [[Int]])] = [
    ([3, 5, 2], 8, [[2, 2, 2, 2], [2, 3, 3], [3, 5]]),
    ([4, 6], 12, [[4, 4, 4], [6, 6]]),
    ([7], 3, []),
]
for (candidates, target, expected) in cases {
    let got = combinationSum(candidates, target)
    let pass = normalised(got) == normalised(expected)
    print(pass ? "PASS" : "FAIL", candidates, target, "→", got, "expected", expected)
}
```
:::

::: Pattern and cue
**Backtracking with reuse and a pruning target.** The cue is *"every combination"* that *"adds up to the target"*: all answers must be listed, so they must be generated. *"May be used any number of times"* changes one detail of the template, and *"positive"* numbers make the pruning safe: once the running total passes the target, adding more can only make it worse.
:::

::: Approach
Sort the candidates so the small ones come first. Build a combination one candidate at a time, keeping track of how much of the target is still left. At each step, try each candidate from the current one onwards: never an earlier one, which is what stops `[5, 3]` from appearing next to `[3, 5]`. Trying the current candidate again is allowed, which is how a number gets reused. If the amount left reaches exactly zero, record the combination. If a candidate is bigger than what is left, stop the loop: every candidate after it is bigger still.

Time: exponential, bounded by the number of nodes in the search tree, which is roughly O(n^(T/m)) for target T and smallest candidate m; at these limits it is tiny. Space O(T/m) besides the output: that is the longest possible combination and the deepest recursion.
:::

::: Swift solution
```swift
func combinationSum(_ candidates: [Int], _ target: Int) -> [[Int]] {
    let ascending = candidates.sorted()
    var result: [[Int]] = []
    var path: [Int] = []

    func explore(from start: Int, remaining: Int) {
        if remaining == 0 {
            result.append(path)
            return
        }
        for index in start..<ascending.count {
            let candidate = ascending[index]
            if candidate > remaining { break }    // sorted: everything after is too big as well
            path.append(candidate)
            explore(from: index, remaining: remaining - candidate)   // index, not index + 1: reuse allowed
            path.removeLast()
        }
    }

    explore(from: 0, remaining: target)
    return result
}
```

`explore(from: index, …)` is the one-character difference from the subsets template: passing `index` lets the same candidate be picked again, while never going back to an earlier one keeps each combination in a single order.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, five more (the target equal to one candidate, a target that only one candidate divides, candidates given in descending order, a candidate larger than the target, the limits 30 candidates and target 40), and 500 random inputs checked three ways: every combination sums to the target and uses only candidates, none appears twice, and the count equals an independent count of the ways to make the target, from a coin-change table.
:::

::: Walk it through
**`[3, 5, 2]`, target 8** — sorted to `[2, 3, 5]`.

Each line is one call, `explore(from: start, remaining)`, with the candidate chosen to get there; indentation is depth.

```text
explore(0, 8)
  2 → explore(0, 6)
    2 → explore(0, 4)
      2 → explore(0, 2)
        2 → explore(0, 0)        record [2, 2, 2, 2]
        3 > 2                    break
      3 → explore(1, 1)          3 > 1: break
      5 > 4                      break
    3 → explore(1, 3)
      3 → explore(1, 0)          record [2, 3, 3]
      5 > 3                      break
    5 → explore(2, 1)            5 > 1: break
  3 → explore(1, 5)
    3 → explore(1, 2)            3 > 2: break
    5 → explore(2, 0)            record [3, 5]
  5 → explore(2, 3)              5 > 3: break
```

Result `[[2, 2, 2, 2], [2, 3, 3], [3, 5]]`.

**`[7]`, target 3** — the loop sees 7 > 3 and breaks at once; nothing is recorded and the answer is `[]`.
:::

::: The Swift trap
**Recursing on slices instead of a start index changes what `0` means.** A natural-looking version passes the rest of the list down: `explore(ascending[index...], remaining: …)`. That compiles, and copies nothing, because it is an `ArraySlice`. But a slice keeps its parent's indices: `ascending[2...]` starts at index 2, so a loop written `for i in 0..<slice.count` reads `slice[0]` and traps, and `slice.first` is right while `slice[0]` is not. Either loop over `slice.indices`, or do what the solution does: keep one array and pass a start index. Wrapping it in `Array(...)` at every call "fixes" the indices by copying at every level.
:::

::: What they ask next
- **"Each candidate may be used at most once, and the input may hold duplicates."** → Combination Sum II: recurse with `index + 1`, and skip `ascending[index]` when `index > start` and it equals `ascending[index - 1]`.
- **"Just count the combinations."** → No backtracking: a coin-change table, `ways[t] += ways[t - candidate]` for each candidate in the outer loop. O(n · T).
- **"Why does sorting help?"** → It turns the overshoot check into a `break` instead of a `continue`: once one candidate is too big, every later one is too, so the rest of the loop is skipped.
:::
