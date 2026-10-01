---
title: 12 · Longest Substring Without Repeating Characters
summary: Find the length of the longest run of consecutive characters in a string where no character appears twice.
minutes: 25
sources:
- LeetCode 3 · Longest Substring Without Repeating Characters | https://leetcode.com/problems/longest-substring-without-repeating-characters/
- Swift standard library · Character | https://developer.apple.com/documentation/swift/character
---

*Medium · G*

You get a string. Look at every stretch of **consecutive** characters in it and keep only the ones where no character appears more than once. Return the length of the longest such stretch. Spaces, digits and symbols count as characters like any other. A stretch has to be contiguous: picking letters from here and there doesn't count.

| Text | Answer |
|---|---|
| `"kayak"` | `3` — `"kay"` or `"yak"` |
| `"abba"` | `2` — `"ab"` or `"ba"`; the edge case that catches most first attempts |
| `"zzzz"` | `1` |

Constraints that matter: up to 50,000 characters — letters, digits, symbols and spaces. Checking every stretch is O(n²) stretches, and checking each one for repeats makes it worse; the target is one pass, O(n).

::: Pattern and cue
**Sliding window with a last-seen map.** The cue is *"longest"* plus *"substring"* — a contiguous stretch — plus a condition that the stretch either meets or breaks (*"without repeating"*). Grow the window on the right one character at a time; when the new character breaks the rule, move the left edge just far enough to fix it, and never move it back.
:::

::: Approach
Read the string from left to right, keeping a window of characters that has no repeats, and a note of where each character was last seen. For each new character, check whether its last appearance is inside the current window. If it is, the window has to shrink: its left edge jumps to the position just after that earlier copy. If the earlier copy is already outside the window — to the left of the left edge — ignore it. Then record the character's new position, and compare the window's length with the best so far.

Time O(n): the right edge visits each character once, and the left edge only jumps forward. Space O(k), where k is the number of distinct characters — at most the alphabet size.
:::

::: Swift solution
```swift
func lengthOfLongestSubstring(_ text: String) -> Int {
    var lastSeen: [Character: Int] = [:]
    var left = 0
    var best = 0

    for (right, character) in text.enumerated() {
        if let seen = lastSeen[character], seen >= left {
            left = seen + 1                      // jump past the earlier copy, never backwards
        }
        lastSeen[character] = right
        best = max(best, right - left + 1)
    }
    return best
}
```

`enumerated()` gives each character with its position counted from 0, so the code never subscripts the string. The `seen >= left` check is the whole difficulty: drop it and `"abba"` returns 3.

Verified with `swift test` on Swift 6.2.3 in Swift 6 mode: the three examples above, seven more (empty, one character, all distinct, text with spaces, `"dvdf"`, an accented letter written two different ways, a repeated flag emoji), and 3,000 random strings checked against a brute-force search over every start position.
:::

::: Walk it through
**`"kayak"`**

| Right | Character | Last seen | Left after | Window | Best |
|---|---|---|---|---|---|
| 0 | k | — | 0 | `k` | 1 |
| 1 | a | — | 0 | `ka` | 2 |
| 2 | y | — | 0 | `kay` | 3 |
| 3 | a | 1 (inside) | 2 | `ya` | 3 |
| 4 | k | 0 (outside) | 2 | `yak` | 3 |

Answer 3. The last row is the subtle one: `k` was seen before, but at position 0, which the window already left behind, so nothing moves.

**`"abba"`** — `a`, `b` give a window of 2. The second `b` was last seen at 1, inside the window, so left jumps to 2: window `b`. The final `a` was last seen at 0, which is behind left, so left stays at 2: window `ba`, length 2. Without the inside-the-window check, left would jump *back* to 1 and report `bba`, length 3 — a window with `b` twice.
:::

::: The Swift trap
**You can't write `text[i]`, and counting bytes gives the wrong answer.** A Swift `String` has no integer subscript, so the C-style loop doesn't compile. The two common escapes behave differently. `Array(text)` gives you `[Character]` with integer indices — fine, O(n) memory, and correct. `Array(text.utf8)` is faster and also compiles, but it counts bytes, not characters: `"é"` written as a single code point and `"e"` followed by a combining accent are the **same** `Character` in Swift, and a flag emoji is one `Character` made of eight bytes. On `"\u{E9}e\u{301}"` the right answer is 1; the byte version says 3. If the interviewer says "ASCII only", bytes are a fair optimisation — say that you're making that assumption out loud.
:::

::: What they ask next
- **"At most k distinct characters, instead of no repeats."** → Same window, but keep a count per character; when the number of distinct keys passes k, move left forward, decrementing counts and removing keys that hit 0, until it's back to k.
- **"Return the substring itself."** → Track the left and right of the best window as you go, then build the string from those offsets once at the end.
- **"Why a dictionary and not an array of 128?"** → An array indexed by ASCII value is faster and fixed-size, but only works if the input is ASCII. The dictionary is correct for any `Character`.
:::
