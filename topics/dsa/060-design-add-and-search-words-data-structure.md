---
title: 51 · Design Add and Search Words Data Structure
summary: Build a word store whose search accepts a dot as a stand-in for any single letter.
group: Tries
minutes: 25
sources:
- LeetCode 211 · Design Add and Search Words Data Structure | https://leetcode.com/problems/design-add-and-search-words-data-structure/
---

*Medium · G*

Build a type with two operations. `addWord(word)` stores a word. `search(pattern)` returns true if some stored word matches the pattern, where a pattern is a word in which any letter may be replaced by `.`, and a `.` matches exactly one letter, any letter. A pattern must match the **whole** word: same length, every position agreeing. Words are lowercase English letters.

| Calls | What the searches return |
|---|---|
| addWord("ring"), addWord("rung"), addWord("sing"), search("r.ng"), search("s..."), search("ri"), search("...."), search("..."), search("r.n.") | `true, true, false, true, false, true` |
| addWord("a"), search("."), search("a.") | `true, false` — a dot is exactly one letter |
| search(".") | `false` — nothing added |

Constraints that matter: words up to 25 letters, at most 2 dots per search, up to 10,000 calls. A `Set<String>` can't answer a pattern without trying every word, and expanding each dot into 26 letters multiplies the lookups.

The tests drive the type with a list of calls and compare what `search` returns, in order.

::: Starter code and tests
In an Xcode test target:

```swift
import Testing

struct AddAndSearchWordsTests {

    enum Call: Sendable {
        case addWord(String)
        case search(String)
    }

    @Test(arguments: [
        ([Call.addWord("ring"), .addWord("rung"), .addWord("sing"), .search("r.ng"), .search("s..."), .search("ri"), .search("...."), .search("..."), .search("r.n.")], [true, true, false, true, false, true]),
        ([Call.addWord("a"), .search("."), .search("a.")], [true, false]),
        ([Call.search(".")], [false]),
    ])
    func matchesADotAgainstAnyOneLetter(calls: [Call], expected: [Bool]) {
        let dictionary = WordDictionary()
        var results: [Bool] = []
        for call in calls {
            switch call {
            case let .addWord(word): dictionary.addWord(word)
            case let .search(pattern): results.append(dictionary.search(pattern))
            }
        }
        #expect(results == expected)
    }

    // MARK: - Privates
    private final class WordDictionary {
        func addWord(_ word: String) {}
        func search(_ word: String) -> Bool { false }
    }
}
```

In a playground:

```swift
final class WordDictionary {
    func addWord(_ word: String) {} // your solution
    func search(_ word: String) -> Bool { false }
}

enum Call {
    case addWord(String)
    case search(String)
}

let cases: [([Call], [Bool])] = [
    ([.addWord("ring"), .addWord("rung"), .addWord("sing"), .search("r.ng"), .search("s..."), .search("ri"), .search("...."), .search("..."), .search("r.n.")], [true, true, false, true, false, true]),
    ([.addWord("a"), .search("."), .search("a.")], [true, false]),
    ([.search(".")], [false]),
]
for (calls, expected) in cases {
    let dictionary = WordDictionary()
    var got: [Bool] = []
    for call in calls {
        switch call {
        case let .addWord(word): dictionary.addWord(word)
        case let .search(pattern): got.append(dictionary.search(pattern))
        }
    }
    print(got == expected ? "PASS" : "FAIL", got, "expected", expected)
}
```
:::

::: Pattern and cue
**Trie with a depth-first search at the wildcards.** The cue is *"search"* over stored words where *"any letter"* may stand in a position. A trie answers the fixed letters by following one child; a `.` is the only place where the search has to branch into every child.
:::

::: Approach
Store the words in a trie: one node per prefix, a flag where a word ends. To search, walk the pattern and the trie together from the root. For a normal letter, follow that letter's child, or fail if there isn't one. For a dot, any child will do, so try each child in turn with the rest of the pattern, and succeed as soon as one of them does. When the pattern is used up, succeed only if the node you're on is the end of a stored word — otherwise you've matched a prefix, not a word.

Time O(L) to add a word of L letters. A search without dots is O(L) too; each dot can branch into up to 26 children, so with at most 2 dots a search visits at most 26² paths of length L. Space O(total letters added).
:::

::: Swift solution
```swift
final class WordDictionary {
    private final class Node {
        var children: [Character: Node] = [:]
        var isWord = false
    }

    private let root = Node()

    func addWord(_ word: String) {
        var node = root
        for character in word {
            if let child = node.children[character] {
                node = child
            } else {
                let child = Node()
                node.children[character] = child
                node = child
            }
        }
        node.isWord = true
    }

    func search(_ word: String) -> Bool {
        search(Array(word), from: 0, in: root)
    }

    private func search(_ letters: [Character], from index: Int, in node: Node) -> Bool {
        if index == letters.count { return node.isWord }
        let letter = letters[index]
        if letter == "." {
            return node.children.values.contains { search(letters, from: index + 1, in: $0) }
        }
        guard let child = node.children[letter] else { return false }
        return search(letters, from: index + 1, in: child)
    }
}
```

`contains` stops at the first child whose branch matches, so a dot doesn't explore the rest once the answer is known. `if index == letters.count { return node.isWord }` is what makes `"ri"` fail even though `ring` was added.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, five more (a pattern that is all dots, a dot in the last position, a word added twice, a pattern longer than every word, dots that only match through one of several branches), and 300 random sequences checked against matching every stored word letter by letter.
:::

::: Walk it through
**After addWord("ring"), addWord("rung"), addWord("sing"): search("r.n.")**

| Position | Pattern letter | Nodes tried | Result |
|---|---|---|---|
| 0 | `r` | root → `r` | follow |
| 1 | `.` | `r` has children `i` and `u`; say `i` comes up first | branch |
| 2 | `n` | `ri` → `rin` | follow |
| 3 | `.` | `rin` has child `g` | branch |
| 4 | end | `ring` is a word | `true` — `u` is never needed |

**search("...")** — the dots follow every path three letters deep (`rin`, `run`, `sin`), but none of those nodes is the end of a word, so every branch returns false: `false`. Which child a dot tries first depends on the dictionary's order, which isn't fixed; the answer doesn't.
:::

::: The Swift trap
**Slicing the string at every level turns O(L) into O(L²), and you can't index it anyway.** The natural recursion passes "the rest of the pattern" down: `search(String(pattern.dropFirst()), …)`. `dropFirst()` itself is cheap — a `Substring` sharing storage — but wrapping it in `String(...)` copies the rest at every step, and `pattern[i]` with an `Int` doesn't compile. Convert once with `Array(word)` and pass an index, as above. Passing `letters` down the recursion doesn't copy it either: arrays are copy-on-write, and nothing here writes to it. And `letter == "."` works because the literal `"."` is inferred as a `Character` from the comparison.
:::

::: What they ask next
- **"Most searches have no dots — can that path be faster?"** → Also keep a `Set<String>` of words; a pattern without a `.` is a single O(L) hash lookup, and only patterns with dots walk the trie.
- **"Another way, without a trie?"** → Bucket the words by length in a dictionary of arrays and compare the pattern against each word of the right length; simple, O(words of that length × L) per search.
- **"What if `*` matches any run of letters, including none?"** → At a `*`, branch two ways: skip the `*`, or consume one letter from the node and stay on the `*`; memoise on (node, index) to stop the branching from blowing up.
:::
