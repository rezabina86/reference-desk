---
title: 81 · Palindromic Substrings
summary: Count how many runs of consecutive characters in a string read the same forwards and backwards, counting each position separately.
group: 1-D dynamic programming
minutes: 20
sources:
- LeetCode 647 · Palindromic Substrings | https://leetcode.com/problems/palindromic-substrings/
- Swift standard library · String.count | https://developer.apple.com/documentation/swift/string/count
---

*Medium · G*

You get a string. Count the stretches of **consecutive** characters that read the same forwards and backwards. Stretches are told apart by where they start and end, not by what they contain: in `"zzz"`, each of the three single `z`s counts, and so do both copies of `"zz"`. Every single character is a palindrome on its own.

| Text | Answer |
|---|---|
| `"aba"` | `4` — `a`, `b`, `a`, `aba` |
| `"zzz"` | `6` — three `z`, two `zz`, one `zzz` |
| `"ab"` | `2` — just the two letters |

Constraints that matter: up to 1,000 characters, lowercase letters. Checking every stretch separately is O(n³); the target is O(n²) time and O(1) extra space.

::: Starter code and tests
In an Xcode test target:

```swift
import Testing

struct PalindromicSubstringsTests {

    @Test(arguments: [
        ("aba", 4),
        ("zzz", 6),
        ("ab", 2),
    ])
    func countsEveryStretchThatReadsTheSameBothWays(text: String, expected: Int) {
        #expect(countSubstrings(text) == expected)
    }

    // MARK: - Privates
    private func countSubstrings(_ text: String) -> Int {
        0
    }
}
```

In a playground:

```swift
func countSubstrings(_ text: String) -> Int {
    0 // your solution
}

let cases: [(String, Int)] = [
    ("aba", 4),
    ("zzz", 6),
    ("ab", 2),
]
for (text, expected) in cases {
    let got = countSubstrings(text)
    print(got == expected ? "PASS" : "FAIL", text, "→", got, "expected", expected)
}
```
:::

::: Pattern and cue
**Expand around every centre, counting each step.** The cue is *"palindromic"* plus *"substrings"* plus *"how many"*. As in the previous problem, a palindrome is a smaller palindrome with a matching pair of characters added at its ends — the DP recurrence. Growing outward from a centre visits a whole family of nested palindromes, one per successful step, so counting the steps counts them all.
:::

::: Approach
Subproblem: is the stretch from i to j a palindrome? Recurrence: yes when the characters at i and j match and the stretch from i + 1 to j − 1 is a palindrome (an empty or one-character middle always is).

Walk the recurrence outward instead of storing it. Every palindrome has exactly one centre — a character (odd length) or a gap between two characters (even length) — so trying all 2n − 1 centres finds every palindrome exactly once. From each centre, step one finger left and one right as long as the characters match; each match is one more palindrome, nested around the previous one. Add one per step.

Time O(n²): 2n − 1 centres, each growing at most n/2 steps. Space O(n) for the character array, O(1) beyond it.
:::

::: Swift solution
```swift
func countSubstrings(_ text: String) -> Int {
    let letters = Array(text)
    let count = letters.count                    // read once; String.count is O(n)
    var total = 0
    for centre in 0..<count {
        for (start, end) in [(centre, centre), (centre, centre + 1)] {   // odd, then even
            var left = start, right = end
            while left >= 0, right < count, letters[left] == letters[right] {
                total += 1                       // each successful step is one more palindrome
                left -= 1
                right += 1
            }
        }
    }
    return total
}
```

The inner `for` runs the same expansion from the two kinds of centre, so there's one loop body instead of two copies. Nothing else needs remembering: the count *is* the number of successful steps.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, three more (empty, one character, `"abba"` → 6), and 3,000 random strings over three letters checked against a brute force that tests every stretch.
:::

::: Walk it through
**`"zzz"`**

| Centre | Steps that match | Palindromes counted | Total |
|---|---|---|---|
| on z (0) | `z` | 1 | 1 |
| gap 0–1 | `zz` | 1 | 2 |
| on z (1) | `z`, then `zzz` | 2 | 4 |
| gap 1–2 | `zz` | 1 | 5 |
| on z (2) | `z` | 1 | 6 |
| gap after 2 | right finger is off the end | 0 | 6 |

Answer 6.

**`"ab"`** — each letter's own centre counts 1; the gap between them fails at once (`a` ≠ `b`). Answer 2.
:::

::: The Swift trap
**`text.count` in a loop condition is a hidden O(n) every time.** A Swift `String` doesn't store its character count: `count` walks the whole string to group bytes into characters. Writing `while left >= 0 && right < text.count && …` therefore re-walks the string on every step and turns the O(n²) solution into O(n³) — it still passes the examples, and times out on a long input. Convert once with `Array(text)` and read the array's `count`, which is stored and O(1). The same applies to `text.count` anywhere inside a nested loop: hoist it.
:::

::: What they ask next
- **"Write the DP table version."** → An n × n `[[Bool]]`, filled with i from n − 1 down to 0 and j from i up, `table[i][j] = letters[i] == letters[j] && (j - i < 2 || table[i + 1][j - 1])`, adding one for every true cell. Same time, O(n²) memory.
- **"Count only distinct palindromes."** → Insert each found stretch's text into a `Set<String>` during the expansion — O(n) per insert, so O(n³) worst case; a palindromic tree (eertree) does it in O(n), named rather than written.
- **"Return the longest instead of the count."** → The previous problem: the same expansion, tracking the best start and length.
:::
