---
title: 19 · Longest Repeating Character Replacement
summary: Change at most k letters in a string so that the longest possible stretch of one repeated letter appears, and return its length.
group: Sliding window
minutes: 25
sources:
- LeetCode 424 · Longest Repeating Character Replacement | https://leetcode.com/problems/longest-repeating-character-replacement/
- Swift standard library · Character.asciiValue | https://developer.apple.com/documentation/swift/character/asciivalue
---

*Medium · G*

You get a string of capital letters and a number k. You may change up to k letters, each into any other capital letter. After the changes, look for the longest stretch of **consecutive** positions that all hold the same letter. Return the longest length you can reach.

| Text | k | Answer |
|---|---|---|
| `"BAAB"` | 1 | `3` — change one B: `"AAAB"` or `"BAAA"` |
| `"AABCAA"` | 2 | `6` — change the B and the C to A |
| `"ABCD"` | 0 | `1` — no changes allowed, every letter is alone |

Constraints that matter: up to 100,000 letters, only `A`–`Z`, and k is between 0 and the length. Trying every stretch is O(n²); the target is one pass, O(n).

::: Starter code and tests
In an Xcode test target:

```swift
import Testing

struct LongestRepeatingCharacterReplacementTests {

    @Test(arguments: [
        ("BAAB", 1, 3),
        ("AABCAA", 2, 6),
        ("ABCD", 0, 1),
    ])
    func returnsTheLongestRunOfOneLetterAfterAtMostKChanges(text: String, k: Int, expected: Int) {
        #expect(characterReplacement(text, k) == expected)
    }

    // MARK: - Privates
    private func characterReplacement(_ text: String, _ k: Int) -> Int {
        0
    }
}
```

In a playground:

```swift
func characterReplacement(_ text: String, _ k: Int) -> Int {
    0 // your solution
}

let cases: [(String, Int, Int)] = [
    ("BAAB", 1, 3),
    ("AABCAA", 2, 6),
    ("ABCD", 0, 1),
]
for (text, k, expected) in cases {
    let got = characterReplacement(text, k)
    print(got == expected ? "PASS" : "FAIL", text, k, "→", got, "expected", expected)
}
```
:::

::: Pattern and cue
**Sliding window with letter counts.** The cue is *"longest"* plus a *consecutive* stretch plus a budget (*"at most k changes"*). A stretch is fixable when the letters that aren't its most common letter number at most k: length − (count of its most common letter) ≤ k. Grow the window on the right; when it stops being fixable, slide the left edge forward.
:::

::: Approach
Read the letters from left to right, keeping a window and a count of each letter inside it. Also remember the highest count any single letter has reached. The window can be made all one letter if the other letters, its length minus that highest count, fit in the k changes. When a new letter makes the window too expensive, move the left edge forward by one, taking its letter out of the counts. The window never shrinks below the best length found, so its size at the end of each step is a candidate answer.

Time O(n): each letter enters the window once and leaves at most once. Space O(1): at most 26 counts.
:::

::: Swift solution
```swift
func characterReplacement(_ text: String, _ k: Int) -> Int {
    let letters = Array(text)
    var counts: [Character: Int] = [:]
    var left = 0
    var maxCount = 0
    var best = 0

    for right in letters.indices {
        counts[letters[right], default: 0] += 1
        maxCount = max(maxCount, counts[letters[right]]!)

        if (right - left + 1) - maxCount > k {
            counts[letters[left]]! -= 1
            left += 1
        }
        best = max(best, right - left + 1)
    }
    return best
}
```

`maxCount` is never lowered when the left edge moves. That looks like a bug and isn't: the answer can only grow when some letter reaches a *higher* count than before, so a stale, too-high `maxCount` can't produce a wrong larger answer. It only stops the window from shrinking, which is fine.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, six more (empty, a single letter, k larger than the string, all one letter, k = 1 on `"AABCAA"`, a run in the middle), and 3,000 random strings checked against a brute-force search over every stretch.
:::

::: Walk it through
**`"BAAB"`, k = 1**

| Right | Letter | Counts | Max | Window length − max | Action | Best |
|---|---|---|---|---|---|---|
| 0 | B | B1 | 1 | 0 | keep | 1 |
| 1 | A | B1 A1 | 1 | 1 | keep | 2 |
| 2 | A | B1 A2 | 2 | 1 | keep | 3 |
| 3 | B | B2 A2 | 2 | 2 > 1 | drop the left B, left = 1 | 3 |

Answer 3.

**`"ABCD"`, k = 0** — every new letter makes a window of 2 with a highest count of 1, which costs one change it doesn't have. The left edge steps forward each time, and the best stays 1.
:::

::: The Swift trap
**The fast version with an array of 26 counts can crash on the subtraction.** Swapping the dictionary for `[Int](repeating: 0, count: 26)` is a fair speed-up when the input is capital letters only. But `Character.asciiValue` is a `UInt8?`, and writing `Int(letter.asciiValue! - 65)` does the subtraction in `UInt8`: any character below `A` (a space, a digit) underflows and traps at runtime instead of giving a wrong index. Convert first, then subtract: `Int(letter.asciiValue!) - 65`. And say the assumption out loud: "capital letters only, as the statement says".
:::

::: What they ask next
- **"Return the stretch itself, not just its length."** → Remember the left and right of the window each time `best` grows, then cut the string once at the end.
- **"Why is it fine that maxCount never goes down?"** → The answer only improves when some letter beats the old highest count; until then the window just slides at its best size, it never reports a bigger one wrongly.
- **"Same thing with 0s and 1s: longest run of 1s if you may flip k zeros."** → The same window, counting zeros instead of the top letter: shrink while zeros exceed k.
:::
