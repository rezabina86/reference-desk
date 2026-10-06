---
title: 83 · Longest Common Subsequence
summary: Find how many characters two strings can share in the same order, when each string may skip characters freely.
group: 2-D dynamic programming
minutes: 25
sources:
- LeetCode 1143 · Longest Common Subsequence | https://leetcode.com/problems/longest-common-subsequence/
- Swift standard library · Array.init(repeating:count:) | https://developer.apple.com/documentation/swift/array/init(repeating:count:)
---

*Medium · G*

You get two strings. From each, you may cross out any characters you like, keeping the rest in their original order. Find the longest string you can end up with in **both** — the same characters in the same order in each, though not necessarily next to each other. Return its length; 0 if the strings share no character.

| First | Second | Answer |
|---|---|---|
| `"stone"` | `"longest"` | `3` — `"one"`: o, n, e appear in that order in both |
| `"abc"` | `"def"` | `0` — nothing in common |
| `"aaaa"` | `"aa"` | `2` — repeats only count as often as both strings have them |

Constraints that matter: each string has 1 to 1,000 lowercase letters. There are 2ⁿ ways to choose what to keep from one string; the target is O(m × n) time — a million table cells at the limit.

::: Starter code and tests
In an Xcode test target:

```swift
import Testing

struct LongestCommonSubsequenceTests {

    @Test(arguments: [
        ("stone", "longest", 3),
        ("abc", "def", 0),
        ("aaaa", "aa", 2),
    ])
    func returnsTheLengthOfTheLongestSharedInOrderSelection(first: String, second: String, expected: Int) {
        #expect(longestCommonSubsequence(first, second) == expected)
    }

    // MARK: - Privates
    private func longestCommonSubsequence(_ first: String, _ second: String) -> Int {
        0
    }
}
```

In a playground:

```swift
func longestCommonSubsequence(_ first: String, _ second: String) -> Int {
    0 // your solution
}

let cases: [(String, String, Int)] = [
    ("stone", "longest", 3),
    ("abc", "def", 0),
    ("aaaa", "aa", 2),
]
for (first, second, expected) in cases {
    let got = longestCommonSubsequence(first, second)
    print(got == expected ? "PASS" : "FAIL", first, second, "→", got, "expected", expected)
}
```
:::

::: Pattern and cue
**2-D dynamic programming over two strings.** The cue is *two strings* plus *"subsequence"* (skip freely, keep the order) plus *"longest"*. Look at the last character of each prefix: if they match, that character can end the shared sequence; if they don't, at least one of them isn't part of it and can be dropped. Either way the question shrinks to shorter prefixes of the two strings — a smaller question indexed by **two** lengths, so the answers form a grid.
:::

::: Approach
Subproblem: the longest common subsequence of the first i letters of the first string and the first j letters of the second. Recurrence: if letter i of the first equals letter j of the second, it is 1 + the answer for (i − 1, j − 1); otherwise it is the larger of the answers for (i − 1, j) and (i, j − 1).

Make a table with one more row than the first string has letters and one more column than the second. Row 0 and column 0 stand for "no letters yet" and hold 0 — nothing is shared with an empty prefix. Fill the rest row by row, left to right. When the two current letters match, take the square diagonally up-left and add one. When they don't, take the larger of the square above (drop this letter of the first string) and the square to the left (drop this letter of the second). The bottom-right square is the answer.

Time O(m × n): constant work per square. Space O(m × n) for the table — O(min(m, n)) with a single rolling row.
:::

::: Swift solution
```swift
func longestCommonSubsequence(_ first: String, _ second: String) -> Int {
    let a = Array(first), b = Array(second)
    // One extra row and column of zeros: an empty prefix shares nothing.
    var table = Array(repeating: Array(repeating: 0, count: b.count + 1), count: a.count + 1)
    for i in a.indices {
        for j in b.indices {
            table[i + 1][j + 1] = a[i] == b[j]
                ? table[i][j] + 1                          // both letters join the answer
                : max(table[i][j + 1], table[i + 1][j])    // drop one letter or the other
        }
    }
    return table[a.count][b.count]
}
```

Letter `i` of the string lives in table row `i + 1`, so the zero row and column are the base cases and no index ever goes to −1. Looping over `indices` instead of `1...a.count` also keeps an empty string from building an inverted range.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, four more (identical strings, an empty first string, two empty strings, `"kitten"` and `"sitting"` → 4), and 2,000 random pairs of strings over three letters checked against a brute-force recursion.
:::

::: Walk it through
**`"stone"` and `"longest"`** — rows are letters of `"stone"`, columns letters of `"longest"`, ∅ is the empty prefix.

| | ∅ | l | o | n | g | e | s | t |
|---|---|---|---|---|---|---|---|---|
| ∅ | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| s | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 |
| t | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 2 |
| o | 0 | 0 | 1 | 1 | 1 | 1 | 1 | 2 |
| n | 0 | 0 | 1 | 2 | 2 | 2 | 2 | 2 |
| e | 0 | 0 | 1 | 2 | 2 | 3 | 3 | 3 |

Answer 3. Two candidates compete: `"st"` (s and t sit at the end of `"longest"`) reaches 2 early, then `"one"` takes over at the `e`/`e` match, 1 + the 2 diagonally up-left.

**`"aaaa"` and `"aa"`** — every letter matches, but each match steps diagonally, using up one letter of **each** string. Column `aa` reaches 2 at row 2 and can't grow further: the second string has no third `a`. Answer 2.
:::

::: The Swift trap
**Indexing the table with the letter's position reads row −1 at the start.** The recurrence is usually written for 1-based positions — `table[i][j] = table[i - 1][j - 1] + 1` — and translating it naively to Swift's 0-based arrays (`for i in a.indices` with `table[i - 1]`) traps with "Index out of range" on the very first square. Either pad the table with a zero row and column and write to `i + 1`, as above, or loop `for i in 1...a.count` and compare `a[i - 1]` — but that closed range traps when a string is empty, a case the constraints rule out and an interviewer may still ask about.

The other half is building the table: `Array(repeating: Array(repeating: 0, count: b.count + 1), count: a.count + 1)` — the inner count belongs to the **second** string, the outer to the first. Swapped, it works whenever the two strings have the same length and crashes otherwise. And convert both strings with `Array(_:)` first; `String` has no integer subscript.
:::

::: What they ask next
- **"Return the subsequence itself."** → Walk back from the bottom-right: on a match, take the letter and move diagonally; otherwise move toward the larger of up and left. Collect letters and reverse.
- **"Use less memory."** → Keep one row of length min(m, n) + 1, plus a variable holding the old up-left value before each square is overwritten. O(min(m, n)) space.
- **"Fewest edits — inserts, deletes, replacements — to turn one into the other (Edit Distance)."** → The same table with base cases i and j instead of 0, and 1 + the minimum of the three neighbours on a mismatch.
:::
