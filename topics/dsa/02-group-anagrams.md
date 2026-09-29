---
title: 2 · Group Anagrams
summary: Given a list of words, gather together the ones that are made of exactly the same letters.
minutes: 25
sources:
- LeetCode 49 · Group Anagrams | https://leetcode.com/problems/group-anagrams/
- Swift standard library · Dictionary.init(grouping:by:) | https://developer.apple.com/documentation/swift/dictionary/init(grouping:by:)
- SE-0206 · Hashable Enhancements (per-process hash seeding) | https://github.com/swiftlang/swift-evolution/blob/main/proposals/0206-hashable-enhancements.md
---

*Medium · G*

You get a list of words. Two words belong together if one is a rearrangement of the other: same letters, same number of each, any order. Return the words sorted into those groups. The order of the groups, and the order of words inside a group, don't matter.

| Words | Groups |
|---|---|
| `["stone", "notes", "lemon", "tones", "melon", "apple"]` | `[["notes", "stone", "tones"], ["lemon", "melon"], ["apple"]]` |
| `[""]` | `[[""]]` — the empty word is a group of one |
| `["x", "y", "x"]` | `[["x", "x"], ["y"]]` — repeats stay, in the same group |

Constraints that matter: up to 10,000 words, each up to 100 characters, lowercase English letters only. Because order is free, the Xcode test sorts the groups and the words inside them before comparing — your answer can come back in any order.

::: Pattern and cue
**Hash map, used for grouping.** The cue is *"gather together the ones that…"* — that is "group by", and "group by" is a dictionary from a key to a list. The whole problem is choosing the key: something every anagram of a word shares and no non-anagram does.

Two keys work. The word's letters sorted (`"stone"` → `"enost"`), or a count of each letter (`[1, 0, 0, …]`, 26 slots). Both are identical across anagrams and differ otherwise.
:::

::: Approach
For each word, compute its key by sorting its letters. Use the key to file the word into a dictionary: key on one side, the list of words that produced it on the other. When every word is filed, the dictionary's lists are the answer.

Time O(n · k log k), for n words of length up to k: each word is sorted once. The letter-count key makes that O(n · k), which matters only when words are long — with k ≤ 100 the sort is fine, and it is the version you'll write correctly under pressure. Space O(n · k) for the keys and the grouped copies of the words.
:::

::: Swift solution
```swift
func groupAnagrams(_ words: [String]) -> [[String]] {
    let groups = Dictionary(grouping: words) { String($0.sorted()) }
    return Array(groups.values)
}
```

`Dictionary(grouping:by:)` is the standard library's group-by: it builds `[Key: [Element]]` in one pass and keeps each group in input order. Writing the loop by hand — `groups[key, default: []].append(word)` — is equally good; know both, because an interviewer may ask what the one-liner does underneath.

Verified with `swift test` on Swift 6.2.3: the three examples above plus five more — an empty list, repeated words (`["ab", "ba", "ab", "abc"]`), same letters in different counts (`"aab"` vs `"abb"`, not anagrams), mixed case (`"Tea"` vs `"eat"`, not anagrams as written), and `"café"` spelled with a precomposed é against one spelled with e + combining accent (anagrams, because Swift compares `Character`s by canonical equivalence).
:::

::: Walk it through
**`["stone", "notes", "lemon", "tones", "melon", "apple"]`**

| Word | Key | Dictionary after |
|---|---|---|
| stone | enost | `enost: [stone]` |
| notes | enost | `enost: [stone, notes]` |
| lemon | elmno | + `elmno: [lemon]` |
| tones | enost | `enost: [stone, notes, tones]` |
| melon | elmno | `elmno: [lemon, melon]` |
| apple | aelpp | + `aelpp: [apple]` |

The values are the three groups.

**`[""]`** — `"".sorted()` is an empty array, `String([])` is `""`, so the key is the empty string and the result is `[[""]]`. No special case needed; say that you checked.
:::

::: The Swift trap
**Dictionary order changes every run.** Swift seeds its hash function randomly per process (SE-0206), so `groups.values` comes back in a different order each time you run the tests. Compare the result directly against `[["notes", "stone", "tones"], …]` and the test passes on one run and fails on the next — a flaky test you wrote yourself. The fix is to normalise before comparing (sort each group, then sort the groups), which is what the Xcode stub does. Mentioning this before the interviewer sees it fail is a strong signal.

Smaller one: `word.sorted()` returns `[Character]`, not a `String`. Using the array as the key works (`[Character]` is `Hashable`), but wrap it in `String(...)` so the key prints readably when you debug.
:::

::: What they ask next
- **"Can you avoid the sort?"** → Count letters into a 26-slot `[Int]` and use the array as the key; `[Int]` is `Hashable`, a tuple would not be. O(n · k). Only valid while the alphabet is fixed and small.
- **"What about Unicode, or uppercase?"** → Decide what "same letter" means first: lowercase (and fold diacritics if the product wants `é` = `e`) before building the key. The sorted-`Character` key keeps working; the 26-slot array doesn't.
- **"Return only the groups with more than one word."** → Filter the values: `groups.values.filter { $0.count > 1 }`. Same cost.
:::
