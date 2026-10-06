---
title: 80 · Longest Palindromic Substring
summary: Return the longest run of consecutive characters in a string that reads the same forwards and backwards.
group: 1-D dynamic programming
minutes: 25
sources:
- LeetCode 5 · Longest Palindromic Substring | https://leetcode.com/problems/longest-palindromic-substring/
- Swift standard library · Character | https://developer.apple.com/documentation/swift/character
---

*Medium · G*

You get a string. Among all its stretches of **consecutive** characters, find the longest one that reads the same from left to right as from right to left, and return that stretch itself. A single character always counts. If two different stretches tie for longest, either is accepted; the examples here each have only one answer, so the tests can compare strings directly.

| Text | Answer |
|---|---|
| `"racecars"` | `"racecar"` — odd length, one middle letter |
| `"abccbx"` | `"bccb"` — even length, the middle is between the two c's |
| `"q"` | `"q"` |

Constraints that matter: up to 1,000 characters, letters and digits. Checking every stretch is O(n²) stretches at O(n) each, O(n³) overall; the target is O(n²) time with O(1) extra space.

::: Starter code and tests
In an Xcode test target:

```swift
import Testing

struct LongestPalindromicSubstringTests {

    @Test(arguments: [
        ("racecars", "racecar"),
        ("abccbx", "bccb"),
        ("q", "q"),
    ])
    func returnsTheLongestStretchThatReadsTheSameBothWays(text: String, expected: String) {
        #expect(longestPalindrome(text) == expected)
    }

    // MARK: - Privates
    private func longestPalindrome(_ text: String) -> String {
        ""
    }
}
```

In a playground:

```swift
func longestPalindrome(_ text: String) -> String {
    "" // your solution
}

let cases: [(String, String)] = [
    ("racecars", "racecar"),
    ("abccbx", "bccb"),
    ("q", "q"),
]
for (text, expected) in cases {
    let got = longestPalindrome(text)
    print(got == expected ? "PASS" : "FAIL", text, "→", got, "expected", expected)
}
```
:::

::: Pattern and cue
**Expand around every centre — the DP recurrence, walked outward.** The cue is *"palindrome"* plus *"substring"* (consecutive) plus *"longest"*. A palindrome is a smaller palindrome with one matching character added at each end. That is a DP recurrence over (start, end) pairs, and it can be filled as a table — but it is cheaper to start from each possible middle and grow outward while the ends match, which visits the same pairs without storing them.
:::

::: Approach
Subproblem: is the stretch from position i to position j a palindrome? Recurrence: it is when the characters at i and j are equal **and** the stretch from i + 1 to j − 1 is a palindrome (an empty or one-character middle always is).

Rather than filling a table of every (i, j), grow each palindrome from its middle. Every palindrome has a centre: a single character for odd lengths, or the gap between two neighbours for even lengths, so a string of n characters has 2n − 1 centres. From each centre, put one finger on each side and step both outward while the characters under them match. When they stop matching (or run off the end), the stretch between them is the longest palindrome with that centre. Remember the start and length of the best one, and cut the string once at the end.

Time O(n²): 2n − 1 centres, each expanding at most n/2 steps. Space O(n) for the character array, O(1) beyond it.
:::

::: Swift solution
```swift
func longestPalindrome(_ text: String) -> String {
    let letters = Array(text)
    guard !letters.isEmpty else { return "" }
    var bestStart = 0
    var bestLength = 1

    func expand(_ left: Int, _ right: Int) {
        var left = left, right = right
        while left >= 0, right < letters.count, letters[left] == letters[right] {
            left -= 1
            right += 1
        }
        let length = right - left - 1          // the loop stopped one step past each end
        if length > bestLength {
            bestStart = left + 1
            bestLength = length
        }
    }

    for centre in letters.indices {
        expand(centre, centre)                 // odd length: one middle character
        expand(centre, centre + 1)             // even length: the gap after this character
    }
    return String(letters[bestStart..<bestStart + bestLength])
}
```

The `while` conditions are checked left to right, so the bounds checks run before either array read. When the loop ends, both fingers have stepped one place too far, hence `right - left - 1` and `left + 1`.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, four more (empty, `"zz"`, `"xyz"` with no palindrome longer than one, and a word whose two accented letters are each written as e plus a combining accent), and 3,000 random strings over three letters, checking against a brute force that the result is a palindrome, appears in the text, and has the longest possible length.
:::

::: Walk it through
**`"abccbx"`** — the centres that matter:

| Centre | Expansion | Palindrome found | Best |
|---|---|---|---|
| on `a` (0) | can't step out | `a`, length 1 | `a` |
| gap 0–1 | `a` ≠ `b` | none | `a` |
| on `c` (2) | `b` ≠ `c` | `c`, length 1 | `a` |
| gap 2–3 | `c` = `c` → `b` = `b` → `a` ≠ `x` | `bccb`, length 4 | `bccb` |
| on `b` (4) | `c` ≠ `x` | `b`, length 1 | `bccb` |

Answer `"bccb"`. Only the even centre finds it — a solution that tries only odd centres returns a single letter here.

**`"q"`** — the odd centre stops at once with length 1; the even centre starts with the right finger past the end and finds nothing. Answer `"q"`.
:::

::: The Swift trap
**Integer positions on a `String` don't exist, and cutting a new string at every improvement is O(n) each time.** `text[left]` doesn't compile; `text.index(text.startIndex, offsetBy: left)` inside the expansion loop compiles but costs O(left) per read, which turns O(n²) into O(n³). Convert once with `Array(text)`. Then resist building the answer inside `expand` (`best = String(letters[left + 1..<right])`): each such cut allocates and copies. Keep two integers and cut once at the end.

`Array(text)` is also what makes the answer correct for text with accents: it splits into `Character`s, so `"é"` written as `e` plus a combining accent is one element, and a palindrome check never splits it from its accent. `Array(text.utf8)` would compare bytes and can return half a character.
:::

::: What they ask next
- **"Show the DP table version."** → A 2-D `[[Bool]]` where `isPalindrome[i][j] = letters[i] == letters[j] && (j - i < 2 || isPalindrome[i + 1][j - 1])`, filled with i going downward so the inner cell is ready. Same O(n²) time, but O(n²) memory — the expansion is the better answer.
- **"Can it be done in O(n)?"** → Yes, Manacher's algorithm reuses mirror information inside a known palindrome; name it, don't write it.
- **"Count the palindromic stretches instead."** → The next problem: the same expansion, adding one for every successful step instead of tracking the longest.
:::
