---
title: 14 · Minimum Window Substring
summary: Find the shortest stretch of a text that contains every character of a second string, counting repeats.
minutes: 25
sources:
- LeetCode 76 · Minimum Window Substring | https://leetcode.com/problems/minimum-window-substring/
- Swift standard library · ArraySlice | https://developer.apple.com/documentation/swift/arrayslice
---

*Hard · optional · G · Z — Sixt asked a close cousin: the shortest part of an array that holds every distinct value*

**Optional.** This one is above the bar most German loops set. Do it if 13 went well; skip it without guilt if not.

You get a text and a target string. Find the shortest stretch of **consecutive** characters in the text that contains every character of the target, as many times as the target has it. Return that stretch, or an empty string if there isn't one. If the target has two A's, the stretch needs two A's. Assume the shortest stretch is unique.

| Text | Target | Answer |
|---|---|---|
| `"XAYBZACB"` | `"ABC"` | `"ACB"` |
| `"AABBA"` | `"AAB"` | `"AAB"` — repeats count: it needs two A's |
| `"ab"` | `"abc"` | `""` — no stretch has a `c` |

Constraints that matter: both strings up to 100,000 characters, letters only, upper and lower case different. The target is one pass over the text, O(n + m).

::: Pattern and cue
**Sliding window, grow until it fits, then shrink while it still fits.** The cue is *"shortest"* plus a *consecutive* stretch plus a condition that a stretch either meets or doesn't (*"contains every character"*). It's problem 12's window turned around: there you shrank to fix a broken window; here you shrink to make a good window as short as possible.
:::

::: Approach
Count what the target needs: how many of each character, and how many characters are still missing in total. Move the right edge along the text. Each time it takes in a character the target still needs, the missing total drops by one. When nothing is missing, the window contains everything: record it if it's the shortest so far, then move the left edge forward, giving back each character it passes. As soon as giving one back makes something missing again, stop shrinking and go back to growing on the right.

Time O(n + m): counting the target is O(m), and each character of the text enters and leaves the window at most once. Space O(k), the number of distinct characters.
:::

::: Swift solution
```swift
func minWindow(_ text: String, _ target: String) -> String {
    let letters = Array(text)
    var need: [Character: Int] = [:]
    for character in target { need[character, default: 0] += 1 }
    var missing = target.count

    var left = 0
    var bestStart = 0
    var bestLength = Int.max

    for right in letters.indices {
        let incoming = letters[right]
        if let count = need[incoming] {
            if count > 0 { missing -= 1 }
            need[incoming] = count - 1
        }

        while missing == 0 {
            if right - left + 1 < bestLength {
                bestStart = left
                bestLength = right - left + 1
            }
            let outgoing = letters[left]
            if let count = need[outgoing] {
                need[outgoing] = count + 1
                if count + 1 > 0 { missing += 1 }
            }
            left += 1
        }
    }
    return bestLength == .max ? "" : String(letters[bestStart..<bestStart + bestLength])
}
```

`need` goes negative on purpose: −1 for an A means "one A more than the target needs is in the window". Only when a count climbs back above 0 is something truly missing.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, four more (one character equal to the target, a target needing a repeat the text lacks, a window at the very end, a longer mixed text), and 3,000 random pairs checked against a brute-force search for the shortest covering stretch.
:::

::: Walk it through
**`"XAYBZACB"`, target `"ABC"`** — need A1 B1 C1, missing 3.

| Step | What happens | Missing | Window | Best |
|---|---|---|---|---|
| right 0–4 | take X, A, Y, B, Z; A and B were needed | 1 | `XAYBZ` | — |
| right 5 | A again; A goes to −1, nothing changes | 1 | `XAYBZA` | — |
| right 6 | C completes it | 0 | `XAYBZAC` | 7 |
| shrink | drop X, A (A back to 0, still fine), Y | 0 | `BZAC` | 4 |
| shrink | drop B; B goes to 1, missing again | 1 | `ZAC` | 4 |
| right 7 | B completes it | 0 | `ZACB` | 4 |
| shrink | drop Z | 0 | `ACB` | 3 |
| shrink | drop A; A goes to 1, missing again | 1 | `CB` | 3 |

Answer `"ACB"`.

**`"ab"`, target `"abc"`** — the window takes `a` and `b`, but `c` is never seen, so missing never reaches 0 and `bestLength` stays at its sentinel: the answer is `""`.
:::

::: The Swift trap
**Force-unwrapping the counts crashes on characters the target doesn't have.** It's tempting to write `need[incoming]! -= 1`, but most characters of the text aren't in the target at all, and the force-unwrap traps on the first one (`X` in the example). Either unwrap with `if let`, as above, or use `need[incoming, default: 0]` and accept that unrelated characters get counts too. Second trap: building the answer. `String` has no integer subscript, so keep `Array(text)`, remember the start and length, and make the string once at the end with `String(letters[start..<start + length])`. Cutting a new string every time the best improves is O(n) each time.
:::

::: What they ask next
- **"Every distinct value of an array, not a target string."** (Sixt's version) → The target is the set of distinct values, each needed once; count them first, then run the same window.
- **"Return just the length."** → Drop the start and the string building; return `bestLength`, or 0.
- **"The target is huge but the text is short."** → Count only the target characters that appear in the text; the window logic is the same.
:::
