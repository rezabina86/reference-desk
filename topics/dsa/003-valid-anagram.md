---
title: 2 · Valid Anagram
summary: Given two words, say whether the second uses exactly the same letters as the first, the same number of times each.
group: Arrays and hashing
minutes: 15
sources:
- LeetCode 242 · Valid Anagram | https://leetcode.com/problems/valid-anagram/
- Swift standard library · Character | https://developer.apple.com/documentation/swift/character
---

*Easy · G*

You get two strings. Return `true` if you could rearrange the characters of the first to spell the second exactly: every character used, each one as many times as it appears. Otherwise return `false`. Order doesn't matter; counts do.

| First | Second | Answer |
|---|---|---|
| `"below"` | `"elbow"` | `true` |
| `"aab"` | `"abb"` | `false` — same letters, different counts |
| `""` | `""` | `true` — two empty strings are rearrangements of each other |

Constraints that matter: each string up to 50,000 lowercase English letters. Sorting both and comparing is O(n log n); the target is O(n). The usual follow-up is "what if the input is any Unicode text?", so pick a solution that survives it.

::: Starter code and tests
In an Xcode test target:

```swift
import Testing

struct ValidAnagramTests {

    @Test(arguments: [
        ("below", "elbow", true),
        ("aab", "abb", false),
        ("", "", true),
    ])
    func reportsWhetherTheSecondWordRearrangesTheFirst(first: String, second: String, expected: Bool) {
        #expect(isAnagram(first, second) == expected)
    }

    // MARK: - Privates
    private func isAnagram(_ first: String, _ second: String) -> Bool {
        false
    }
}
```

In a playground:

```swift
func isAnagram(_ first: String, _ second: String) -> Bool {
    false // your solution
}

let cases: [(String, String, Bool)] = [
    ("below", "elbow", true),
    ("aab", "abb", false),
    ("", "", true),
]
for (first, second, expected) in cases {
    let got = isAnagram(first, second)
    print(got == expected ? "PASS" : "FAIL", first, second, "→", got, "expected", expected)
}
```
:::

::: Pattern and cue
**Hash map of counts.** The cue is *"the same number of times each"*: the order of the characters is irrelevant and only how many of each there are matters. That is a count per character, and a count per key is `counts[key, default: 0] += 1`.
:::

::: Approach
Keep one tally per character. Go through the first string and add one for each character; then go through the second and take one away for each character. If the two strings are rearrangements of each other, every addition is cancelled by a removal, so every tally ends at exactly zero. Any tally left above or below zero means a character appeared a different number of times.

Time O(n + m) for strings of length n and m: each character is touched once, plus one pass over the tallies. Space O(k) for k distinct characters, at most 26 for lowercase English.

Sorting both strings and comparing (`first.sorted() == second.sorted()`) is a correct one-line first answer at O(n log n). Say it, then say why counting beats it.
:::

::: Swift solution
```swift
func isAnagram(_ first: String, _ second: String) -> Bool {
    var balance: [Character: Int] = [:]
    for character in first { balance[character, default: 0] += 1 }
    for character in second { balance[character, default: 0] -= 1 }
    return balance.values.allSatisfy { $0 == 0 }
}
```

One dictionary instead of two: the first string counts up, the second counts down, and the check at the end is that everything cancelled. Strings of different lengths need no special case, because some tally can't reach zero.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, six more (different lengths, a single letter against itself, capital against lowercase, `"café"` with a single-code-point é against `"éfac"` with e plus a combining accent, emoji, a one-letter difference in a long string), and 3,000 random pairs checked against the sorted comparison.
:::

::: Walk it through
**`"below"` and `"elbow"`**

| Step | Balance after |
|---|---|
| count up `below` | `b:1 e:1 l:1 o:1 w:1` |
| count down `elbow` | `b:0 e:0 l:0 o:0 w:0` |

Every tally is 0, so the answer is `true`.

**`"aab"` and `"abb"`** — counting up gives `a:2 b:1`; counting down gives `a:1 b:−1`. Two tallies are off, so the answer is `false`. A check that only asks "does every character of one appear in the other?" would wrongly say `true` here.
:::

::: The Swift trap
**Don't shortcut with `count`, and don't count bytes.** A tempting early exit is `guard first.count == second.count else { return false }`. On a Swift `String`, `count` isn't stored: it walks the whole string to group bytes into characters, so the "cheap" check is an extra O(n) pass. And it must stay `count`, not `utf8.count`: `"é"` written as one code point is 2 bytes, written as `e` plus a combining accent it is 3, yet Swift treats both as the same `Character`. So `"café"` and `"éfac"` (with the second spelling) are anagrams, and a byte-length check says they are not. The dictionary solution needs no length check at all.

If the input is promised to be lowercase ASCII, a fixed array of 26 counts indexed by `Int(character.asciiValue!) - 97` is faster. Say the assumption before you write it.
:::

::: What they ask next
- **"What if the input is any Unicode text?"** → The `[Character: Int]` version already handles it; the 26-slot array doesn't. Decide first whether `"É"` and `"é"` should match, and lowercase both strings if so.
- **"Many words: group the ones that are anagrams of each other."** → Use the sorted letters (or the count array) as a dictionary key: that is [4 · Group Anagrams](#/dsa/group-anagrams).
- **"Is some rearrangement of the short word hidden in the long one?"** → A sliding window the length of the short word over the long one, keeping the same tallies as it moves.
:::
