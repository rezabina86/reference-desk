---
title: 57 · Subsets
summary: Given a list of different numbers, return every possible selection of them, from picking none to picking all.
group: Backtracking
minutes: 25
sources:
- LeetCode 78 · Subsets | https://leetcode.com/problems/subsets/
- Swift standard library · Sequence.lexicographicallyPrecedes(_:) | https://developer.apple.com/documentation/swift/sequence/lexicographicallyprecedes(_:)
---

*Medium · G*

You get an array of integers, no two the same. Return every subset: every group you can form by keeping some of the numbers and leaving out the rest, including keeping none and keeping all. No subset may appear twice, and `[4, 8]` and `[8, 4]` count as the same subset. The subsets can come back in any order, and so can the numbers inside each one.

| Numbers | Answer |
|---|---|
| `[4, 8]` | `[[], [4], [8], [4, 8]]` |
| `[7]` | `[[], [7]]` — the empty selection always counts |
| `[1, 2, 3]` | `[[], [1], [2], [3], [1, 2], [1, 3], [2, 3], [1, 2, 3]]` — 2³ = 8 |

Constraints that matter: up to 10 numbers, all different, between −10 and 10. With n numbers there are 2ⁿ subsets, so the output alone is exponential and no algorithm can beat O(2ⁿ). Because order is free at both levels, the tests sort the numbers inside each subset, then sort the list of subsets, before comparing.

::: Starter code and tests
In an Xcode test target:

```swift
import Testing

struct SubsetsTests {

    @Test(arguments: [
        ([4, 8], [[], [4], [8], [4, 8]]),
        ([7], [[], [7]]),
        ([1, 2, 3], [[], [1], [2], [3], [1, 2], [1, 3], [2, 3], [1, 2, 3]]),
    ])
    func returnsEverySelectionOfTheNumbers(numbers: [Int], expected: [[Int]]) {
        #expect(normalised(subsets(numbers)) == normalised(expected))
    }

    // MARK: - Privates
    private func subsets(_ numbers: [Int]) -> [[Int]] {
        []
    }

    private func normalised(_ sets: [[Int]]) -> [[Int]] {
        sets.map { $0.sorted() }.sorted { $0.lexicographicallyPrecedes($1) }
    }
}
```

In a playground:

```swift
func subsets(_ numbers: [Int]) -> [[Int]] {
    [] // your solution
}

func normalised(_ sets: [[Int]]) -> [[Int]] {
    sets.map { $0.sorted() }.sorted { $0.lexicographicallyPrecedes($1) }
}

let cases: [([Int], [[Int]])] = [
    ([4, 8], [[], [4], [8], [4, 8]]),
    ([7], [[], [7]]),
    ([1, 2, 3], [[], [1], [2], [3], [1, 2], [1, 3], [2, 3], [1, 2, 3]]),
]
for (numbers, expected) in cases {
    let got = subsets(numbers)
    let pass = normalised(got) == normalised(expected)
    print(pass ? "PASS" : "FAIL", numbers, "→", got, "expected", expected)
}
```
:::

::: Pattern and cue
**Backtracking, recording at every step.** The cue is *"every subset"*: the answer is all the selections, so they have to be generated one by one. Each number is either in or out; walking the numbers left to right and only ever adding later ones guarantees each selection is produced exactly once.
:::

::: Approach
Keep one growing selection, starting empty. Record it as an answer straight away: every selection, at every stage, is a valid subset. Then, for each number to the right of the last one you picked, add it to the selection, repeat the whole process from just after it, and take it out again before trying the next number. Because you only ever add numbers to the right of the last pick, `[4, 8]` is produced once and `[8, 4]` never.

Time O(n · 2ⁿ): there are 2ⁿ subsets, and recording each copies up to n numbers. Space O(n) besides the output: the recursion is at most n calls deep and the selection holds at most n numbers.
:::

::: Swift solution
```swift
func subsets(_ numbers: [Int]) -> [[Int]] {
    var result: [[Int]] = []
    var path: [Int] = []

    func explore(from start: Int) {
        result.append(path)                       // every partial selection is a subset
        for index in start..<numbers.count {
            path.append(numbers[index])           // choose
            explore(from: index + 1)              // only numbers to the right: no repeats
            path.removeLast()                     // un-choose
        }
    }

    explore(from: 0)
    return result
}
```

`explore(from: index + 1)` is the line that rules out duplicates: a selection is built in left-to-right order of the input, so each one has exactly one way to be built.

The loop-free alternative, worth mentioning: every integer from 0 to 2ⁿ − 1 is a subset in binary, bit i meaning "take `numbers[i]`".

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, four more (an empty array returns `[[]]`, negative numbers, ten numbers giving 1,024 subsets, the numbers given in descending order), and 500 random arrays checked against the bitmask enumeration, plus a check that no subset appears twice.
:::

::: Walk it through
**`[4, 8]`**

| Call | Path when recorded | Then tries |
|---|---|---|
| `explore(from: 0)` | `[]` | 4, then 8 |
| `explore(from: 1)` after choosing 4 | `[4]` | 8 |
| `explore(from: 2)` after choosing 8 | `[4, 8]` | nothing (range `2..<2` is empty) |
| back up: remove 8, remove 4; choose 8, `explore(from: 2)` | `[8]` | nothing |

Result `[[], [4], [4, 8], [8]]`; normalised, it equals the expected answer.

**`[7]`** — `explore(from: 0)` records `[]`, chooses 7, records `[7]`, and the inner loop is the empty range `1..<1`. Two subsets.
:::

::: The Swift trap
**`result.append(path)` already takes a snapshot; don't copy again, and don't expect it to be free.** In Python the same line stores a reference to the one list that keeps changing, so every stored subset ends up empty and people learn to write `path[:]`. Swift arrays are values: appending stores the current contents, and the next `path.append` copies-on-write instead of changing the stored answer. Writing `result.append(Array(path))` is harmless but redundant. The snapshot still costs O(length of path), and that copy is exactly where the n in O(n · 2ⁿ) comes from.
:::

::: What they ask next
- **"The input can contain duplicates; return each distinct subset once."** → Sort first, then inside the loop skip `numbers[index]` when `index > start` and it equals `numbers[index - 1]`: the same value is only tried once per position.
- **"Only the subsets of size k."** → Record only when `path.count == k`, and stop going deeper once it is reached; that is the combinations template in the [backtracking primer](#/dsa/backtracking).
- **"Do it without recursion."** → Start with `[[]]`; for each number, append a copy of every existing subset with the number added. Or count from 0 to 2ⁿ − 1 and read the bits.
:::
