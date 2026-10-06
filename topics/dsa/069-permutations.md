---
title: 58 · Permutations
summary: Given a list of different numbers, return every order in which they can be arranged.
group: Backtracking
minutes: 25
sources:
- LeetCode 46 · Permutations | https://leetcode.com/problems/permutations/
- Swift standard library · Sequence.lexicographicallyPrecedes(_:) | https://developer.apple.com/documentation/swift/sequence/lexicographicallyprecedes(_:)
---

*Medium · G · Z — N26 is documented asking permutations*

You get an array of integers, no two the same. Return every arrangement of all of them: each arrangement uses every number exactly once, and two arrangements differ if any position holds a different number. The arrangements can come back in any order, but the order *inside* each one is the answer itself.

| Numbers | Answer |
|---|---|
| `[0, 1]` | `[[0, 1], [1, 0]]` |
| `[9]` | `[[9]]` — one number, one arrangement |
| `[1, 2, 3]` | `[[1, 2, 3], [1, 3, 2], [2, 1, 3], [2, 3, 1], [3, 1, 2], [3, 2, 1]]` — 3! = 6 |

Constraints that matter: up to 6 numbers, all different, between −10 and 10. There are n! arrangements, so the output is the cost; the goal is to produce each exactly once with no wasted work. Because the list of arrangements may come back in any order, the tests sort the list before comparing, but never the numbers inside an arrangement.

::: Starter code and tests
In an Xcode test target:

```swift
import Testing

struct PermutationsTests {

    @Test(arguments: [
        ([0, 1], [[0, 1], [1, 0]]),
        ([9], [[9]]),
        ([1, 2, 3], [[1, 2, 3], [1, 3, 2], [2, 1, 3], [2, 3, 1], [3, 1, 2], [3, 2, 1]]),
    ])
    func returnsEveryOrderingOfTheNumbers(numbers: [Int], expected: [[Int]]) {
        #expect(sortedOrderings(permute(numbers)) == sortedOrderings(expected))
    }

    // MARK: - Privates
    private func permute(_ numbers: [Int]) -> [[Int]] {
        []
    }

    private func sortedOrderings(_ orderings: [[Int]]) -> [[Int]] {
        orderings.sorted { $0.lexicographicallyPrecedes($1) }   // the list only, never inside one
    }
}
```

In a playground:

```swift
func permute(_ numbers: [Int]) -> [[Int]] {
    [] // your solution
}

func sortedOrderings(_ orderings: [[Int]]) -> [[Int]] {
    orderings.sorted { $0.lexicographicallyPrecedes($1) }
}

let cases: [([Int], [[Int]])] = [
    ([0, 1], [[0, 1], [1, 0]]),
    ([9], [[9]]),
    ([1, 2, 3], [[1, 2, 3], [1, 3, 2], [2, 1, 3], [2, 3, 1], [3, 1, 2], [3, 2, 1]]),
]
for (numbers, expected) in cases {
    let got = permute(numbers)
    let pass = sortedOrderings(got) == sortedOrderings(expected)
    print(pass ? "PASS" : "FAIL", numbers, "→", got, "expected", expected)
}
```
:::

::: Pattern and cue
**Backtracking with a used-marker.** The cue is *"every arrangement"* / *"all orderings"*: the answers have to be listed, and order matters inside each one. So unlike subsets, every position may take *any* number not used yet, and the loop always starts from the first number, skipping the ones already placed.
:::

::: Approach
Fill the positions one at a time. For the current position, try each number that isn't already placed: place it, mark it as used, fill the remaining positions the same way, then unmark it and take it back out before trying the next number. When every position is filled, record the arrangement. A list of true/false markers, one per number, answers "already placed?" in constant time.

Time O(n · n!): n! arrangements, each copied in O(n) when recorded; the work of trying and undoing is within the same bound. Space O(n) besides the output: the arrangement being built, the markers, and a recursion n calls deep.
:::

::: Swift solution
```swift
func permute(_ numbers: [Int]) -> [[Int]] {
    var result: [[Int]] = []
    var path: [Int] = []
    var used = Array(repeating: false, count: numbers.count)

    func explore() {
        if path.count == numbers.count {
            result.append(path)
            return
        }
        for index in numbers.indices where !used[index] {
            used[index] = true                    // choose
            path.append(numbers[index])
            explore()                             // fill the remaining positions
            path.removeLast()                     // un-choose, in reverse order
            used[index] = false
        }
    }

    explore()
    return result
}
```

`where !used[index]` is checked as each iteration starts, so it sees the markers as they are at that moment; the un-choose lines restore them before the next number is tried.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, four more (an empty array returns `[[]]`, negative numbers, six numbers giving 720 arrangements, numbers given in descending order), a check that every arrangement uses each number once and none repeats, and 300 random arrays checked against a generator built a different way (inserting each new number at every position of the previous arrangements).
:::

::: Walk it through
**`[0, 1]`**

| Depth | Used | Path | Action |
|---|---|---|---|
| 0 | — | `[]` | try 0 |
| 1 | 0 | `[0]` | try 1 (0 is used) |
| 2 | 0, 1 | `[0, 1]` | full: record `[0, 1]`; back up, remove 1, remove 0 |
| 0 | — | `[]` | try 1 |
| 1 | 1 | `[1]` | try 0 |
| 2 | 1, 0 | `[1, 0]` | full: record `[1, 0]` |

Result `[[0, 1], [1, 0]]`.

**`[9]`** — one level: place 9, the path is full, record `[9]`. Undo, the loop ends. One arrangement.
:::

::: The Swift trap
**Normalising the answer for comparison is easy to get wrong in both directions.** `result.sorted()` doesn't compile: `[Int]` isn't `Comparable`, so a list of arrangements needs `sorted { $0.lexicographicallyPrecedes($1) }`. And the subsets habit of also sorting *inside* each answer turns every arrangement of `[1, 2, 3]` into `[1, 2, 3]`: a wrong solution that returns the same arrangement six times would pass. Sort the outer list only, and check the count is n!.

The swap-based alternative (swap position `i` with each later position, recurse, swap back) avoids the markers but needs `numbers` copied into a `var` first, and `swap(&a[i], &a[j])` doesn't compile in Swift: two overlapping accesses to one array. Use `a.swapAt(i, j)`.
:::

::: What they ask next
- **"The numbers can repeat; return each distinct arrangement once."** → Sort, then skip `numbers[index]` when it equals `numbers[index - 1]` and `used[index - 1]` is false: the second copy of a value may only be placed after the first.
- **"Just the next arrangement in dictionary order, in place."** → Next Permutation: from the right, find the first value smaller than its right neighbour, swap it with the smallest larger value to its right, then reverse the tail. O(n), O(1).
- **"Return only the kth arrangement."** → Don't generate them: the first position is `numbers[(k − 1) / (n − 1)!]`, then repeat with the remainder. O(n²) with an array, no backtracking.
:::
