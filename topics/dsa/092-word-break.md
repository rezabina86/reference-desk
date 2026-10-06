---
title: 77 · Word Break
summary: Decide whether a string with no spaces can be cut into pieces that are all words from a given list.
group: 1-D dynamic programming
minutes: 25
sources:
- LeetCode 139 · Word Break | https://leetcode.com/problems/word-break/
- Swift standard library · Set | https://developer.apple.com/documentation/swift/set
---

*Medium · G*

You get a string with no spaces and a list of dictionary words. Decide whether the string can be cut into consecutive pieces, each of which is a word from the list. Every letter must belong to exactly one piece, and a word may be used any number of times.

| Text | Words | Answer |
|---|---|---|
| `"penpineapple"` | `["pen", "pine", "apple", "pineapple"]` | `true` — pen · pineapple, or pen · pine · apple |
| `"dogsit"` | `["dog", "dogs", "it", "sat"]` | `true` — dogs · it; cutting after "dog" first leads nowhere |
| `"carpet"` | `["car", "pets"]` | `false` — after "car", "pet" isn't a word |

Constraints that matter: the text is up to 300 letters, up to 1,000 words of up to 20 letters each, all lowercase. Trying every way to cut is exponential; the target is O(n × L) lookups, where L is the longest word.

::: Starter code and tests
In an Xcode test target:

```swift
import Testing

struct WordBreakTests {

    @Test(arguments: [
        ("penpineapple", ["pen", "pine", "apple", "pineapple"], true),
        ("dogsit", ["dog", "dogs", "it", "sat"], true),
        ("carpet", ["car", "pets"], false),
    ])
    func decidesWhetherTheTextSplitsIntoListedWords(text: String, words: [String], expected: Bool) {
        #expect(wordBreak(text, words) == expected)
    }

    // MARK: - Privates
    private func wordBreak(_ text: String, _ words: [String]) -> Bool {
        false
    }
}
```

In a playground:

```swift
func wordBreak(_ text: String, _ words: [String]) -> Bool {
    false // your solution
}

let cases: [(String, [String], Bool)] = [
    ("penpineapple", ["pen", "pine", "apple", "pineapple"], true),
    ("dogsit", ["dog", "dogs", "it", "sat"], true),
    ("carpet", ["car", "pets"], false),
]
for (text, words, expected) in cases {
    let got = wordBreak(text, words)
    print(got == expected ? "PASS" : "FAIL", text, words, "→", got, "expected", expected)
}
```
:::

::: Pattern and cue
**1-D dynamic programming over prefixes.** The cue is *"can it be cut into"* — a yes/no question over a sequence where each choice (where the next cut goes) leaves a smaller version of the same question. The choices overlap: in `"dogsit"`, the remainder `"it"` is reached only through `"dogs"`, but in a longer text the same remainder can be reached through many different cuts, and a plain recursion re-checks it every time.
:::

::: Approach
Subproblem: can the first i letters be cut into listed words? Recurrence: the first i letters can be cut if, for some j before i, the first j letters can be cut **and** the letters from j to i form a listed word.

Put the words in a set for instant lookup. Keep one yes/no per prefix length, from 0 to the full length; the empty prefix is a yes. For each end position, look back at every possible start of a last word — never further back than the longest word in the list — and check two things: the prefix before that start is a yes, and the piece in between is a word. One success is enough to mark this prefix yes. The answer is the yes/no for the whole text.

Time O(n × L × L): n end positions, at most L starts each, and building and hashing a piece of up to L letters. With L capped at 20 that's effectively linear. Space O(n + total length of the words) for the prefix list and the set.
:::

::: Swift solution
```swift
func wordBreak(_ text: String, _ words: [String]) -> Bool {
    let letters = Array(text)
    let dictionary = Set(words)
    let longest = words.map(\.count).max() ?? 0
    guard !letters.isEmpty else { return true }
    var splittable = [Bool](repeating: false, count: letters.count + 1)
    splittable[0] = true                         // the empty prefix needs no words
    for end in 1...letters.count {
        for start in stride(from: end - 1, through: max(0, end - longest), by: -1)
        where splittable[start] {
            if dictionary.contains(String(letters[start..<end])) {
                splittable[end] = true
                break                            // one way to cut is enough
            }
        }
    }
    return splittable[letters.count]
}
```

The `where splittable[start]` filter skips the string-building for starts that can't lead anywhere, and the `max(0, end - longest)` bound stops the look-back at the longest word. `stride(from:through:by:)` produces an empty sequence when the start is already below the end, so no range is ever inverted.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, six more (a one-letter text, `"aaaa"` with `["a", "aa"]`, a text whose last letter is in no word, `"dogsat"`, an empty word list, and 30 `a`s followed by `b` — the input that makes the plain recursion explode), and 2,000 random two-letter texts and dictionaries checked against a brute-force recursion.
:::

::: Walk it through
**`"dogsit"` with `["dog", "dogs", "it", "sat"]`** — longest word 4. Position k means "the first k letters".

| End | Pieces tried (only from starts already marked yes) | Mark |
|---|---|---|
| 0 | — | yes |
| 1 | `d` | no |
| 2 | `do` | no |
| 3 | `dog` ✓ | yes |
| 4 | `s` (from 3), `dogs` ✓ (from 0) | yes |
| 5 | `i` (from 4), `si` (from 3) | no |
| 6 | `it` ✓ (from 4) | yes |

Answer true. The cut after "dog" alone (end 3) leads only to "sit", which isn't listed; the table finds the other route through end 4.

**`"carpet"` with `["car", "pets"]`** — end 3 is a yes ("car"). Ends 4, 5 and 6 only have start 3 to build on, and `p`, `pe`, `pet` aren't words. Answer false.
:::

::: The Swift trap
**Building pieces with `String` indices inside the loop is slow and hard to get right.** `text[start..<end]` with integer bounds doesn't compile — `String` has no integer subscript — and the workaround `text.index(text.startIndex, offsetBy: start)` walks the string from the beginning every time, adding a hidden O(n) to each of the O(n × L) lookups. Convert once with `Array(text)`, slice the `[Character]` array, and turn only the piece into a `String` for the set lookup.

Two related slips. `Set(words)` matters: `words.contains(piece)` on the array is a linear scan through up to 1,000 words per check. And `words.map(\.count).max()` returns an optional — an empty word list gives `nil`, which the `?? 0` turns into a look-back of zero, so every non-empty text correctly answers false.
:::

::: What they ask next
- **"Return every way to split the text (Word Break II)."** → Top-down recursion with a memo from start position to the list of sentences for the remainder; the output can be exponential, so the memo only stops repeated work, not output size.
- **"The dictionary is huge and words are long."** → Store the words in a trie and, from each yes-position, walk forward through the trie letter by letter, marking every end where a word finishes: no substring building at all.
- **"Why not greedy — take the longest word that fits?"** → With the same list, `"dogsit"` defeats shortest-first (dog, then "sit" is stuck) and `"dogsat"` defeats longest-first (dogs, then "at" is stuck); only trying every cut point is safe.
:::
