---
title: Sliding window — the idea
summary: A stretch of consecutive elements that grows on the right and shrinks on the left, so every stretch worth checking is seen in one pass.
group: Sliding window
minutes: 8
sources:
- Swift standard library · Dictionary.subscript(_:default:) | https://developer.apple.com/documentation/swift/dictionary/subscript(_:default:)
- Swift standard library · Character | https://developer.apple.com/documentation/swift/character
---

An array of n elements has about n²/2 stretches of consecutive elements. Checking each one is the brute force. A sliding window checks only the stretches that could matter: it extends to the right one element at a time and gives up elements on the left only when it has to, so each element enters once and leaves once.

## When to reach for it

- The statement says **"contiguous"**, **"consecutive"**, **"substring"** or **"subarray"** — not "subsequence".
- It asks for the **longest** or **shortest** such stretch, or the best one by some score.
- There is a **condition** a stretch either meets or breaks: no repeats, at most k changes, contains every target character.
- There is a **budget**: at most k distinct values, at most k flips.
- A pair of days or positions where **the left one must come first**, scanned once.

## The idea in plain words

Think of reading a long receipt through a cardboard frame with a slot in it. You slide the right edge of the slot along one line at a time. Whenever what you see breaks the rule — say, the same item appears twice — you pull the left edge forward until the rule holds again. You never move either edge backwards. At every moment you know something about what's inside the slot (counts, the cheapest line, the most common item), and you update that knowledge as one line comes in on the right and another leaves on the left, rather than recounting the whole slot.

The window either looks for the **longest** stretch that still meets the rule (grow, and shrink only to repair it) or the **shortest** stretch that meets it (grow until it meets the rule, then shrink as far as it still does).

## The template in Swift

```swift
// Longest stretch that keeps a rule, judged from the counts inside the window.
func longestStretch<Element: Hashable>(
    in items: [Element],
    fits: ([Element: Int], Int) -> Bool    // counts inside the window, window length
) -> Int {
    var counts: [Element: Int] = [:]
    var left = 0
    var best = 0
    for right in items.indices {
        counts[items[right], default: 0] += 1                 // take in the new element
        while !fits(counts, right - left + 1) {               // repair: give up elements on the left
            counts[items[left], default: 0] -= 1
            if counts[items[left]] == 0 { counts[items[left]] = nil }
            left += 1
        }
        best = max(best, right - left + 1)                    // the window is valid here
    }
    return best
}

// Example: the longest stretch with at most two distinct values.
let longest = longestStretch(in: Array("abaccc")) { counts, _ in counts.count <= 2 }  // 4, "accc"
```

For the shortest stretch, flip the inner loop: `while fits(...)` — record the window, then give up the left element — and keep the smallest length seen.

## Variations

- **A running minimum as the left edge.** The window's left edge is just the best start so far, and it jumps forward whenever a better one appears. Best Time to Buy and Sell Stock.
- **Jump the left edge with a last-seen map.** Instead of stepping left forward one element at a time, remember where each value last appeared and jump past it in one move. Longest Substring Without Repeating Characters.
- **Counts plus a budget.** Keep a count per value and test the window against a budget, such as "length minus the most common count is at most k". Longest Repeating Character Replacement.
- **Grow until it fits, then shrink while it fits.** Track what is still missing; when nothing is, record and shrink. Minimum Window Substring.
- **Fixed size.** When the length is given ("every 5 consecutive days"), add the element entering and subtract the one leaving: no condition, no inner loop.

## Complexity

O(n) time: the right edge visits each element once, and the left edge only moves forward, so it does at most n steps in total across the whole run — the inner `while` doesn't make it O(n²). Space O(k) for the counts, where k is the number of distinct values in a window: at most the alphabet size for strings.

## Swift traps

- **No integer subscript on `String`.** Convert once with `Array(text)` and index the `[Character]`, or use `enumerated()` when you only read forward. Never call `index(_:offsetBy:)` inside the loop.
- **Bytes are not characters.** `Array(text.utf8)` is faster but counts bytes: an accented letter or an emoji is one `Character` and several bytes. Fine only if the statement says ASCII — say so out loud.
- **`counts[key, default: 0] += 1` is the counter.** Force-unwrapping `counts[key]!` crashes on the first key that was never added.
- **Remove keys that reach 0** when the rule depends on the number of distinct keys; `counts.count` still counts a key whose value is 0.
- **No `Deque` in the standard library.** The "maximum of every window" follow-up needs a double-ended queue; in an interview, an array with a head index stands in for one, since `removeFirst()` is O(n).

## The problems in this topic

- [17 · Best Time to Buy and Sell Stock](#/dsa/best-time-to-buy-and-sell-stock) — Easy
- [18 · Longest Substring Without Repeating Characters](#/dsa/longest-substring-without-repeating-characters) — Medium
- [19 · Longest Repeating Character Replacement](#/dsa/longest-repeating-character-replacement) — Medium
- [20 · Minimum Window Substring](#/dsa/minimum-window-substring) — Hard, optional
