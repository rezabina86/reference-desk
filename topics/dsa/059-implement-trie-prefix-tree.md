---
title: 50 · Implement Trie (Prefix Tree)
summary: Build a word store that can add words, say whether an exact word was added, and say whether any added word starts with a given beginning.
group: Tries
minutes: 25
sources:
- LeetCode 208 · Implement Trie (Prefix Tree) | https://leetcode.com/problems/implement-trie-prefix-tree/
- Swift standard library · Dictionary.subscript(_:default:) | https://developer.apple.com/documentation/swift/dictionary/subscript(_:default:)-45arb
---

*Medium · G*

Build a type with three operations. `insert(word)` adds a word. `search(word)` returns true only if exactly that word was added before. `startsWith(prefix)` returns true if any added word begins with that prefix — a whole word counts as its own prefix. Words and prefixes are lowercase English letters.

| Calls | What the queries return |
|---|---|
| insert("cart"), search("car"), startsWith("car"), insert("car"), search("car"), search("cart"), startsWith("cat") | `false, true, true, true, false` — `car` is only a prefix until it is added |
| insert("apple"), search("app"), startsWith("apple"), search("apples") | `false, true, false` |
| search("x"), startsWith("x") | `false, false` — nothing added yet |

Constraints that matter: words of 1 to 2,000 letters, up to 30,000 calls in total. Each call should cost the length of its word, not the number of words stored — so a list scanned with `hasPrefix` is out.

The tests drive the type with a list of calls and compare what `search` and `startsWith` return, in order.

::: Starter code and tests
In an Xcode test target:

```swift
import Testing

struct ImplementTrieTests {

    enum Call: Sendable {
        case insert(String)
        case search(String)
        case startsWith(String)
    }

    @Test(arguments: [
        ([Call.insert("cart"), .search("car"), .startsWith("car"), .insert("car"), .search("car"), .search("cart"), .startsWith("cat")], [false, true, true, true, false]),
        ([Call.insert("apple"), .search("app"), .startsWith("apple"), .search("apples")], [false, true, false]),
        ([Call.search("x"), .startsWith("x")], [false, false]),
    ])
    func answersExactAndPrefixQueries(calls: [Call], expected: [Bool]) {
        let trie = Trie()
        var results: [Bool] = []
        for call in calls {
            switch call {
            case let .insert(word): trie.insert(word)
            case let .search(word): results.append(trie.search(word))
            case let .startsWith(prefix): results.append(trie.startsWith(prefix))
            }
        }
        #expect(results == expected)
    }

    // MARK: - Privates
    private final class Trie {
        func insert(_ word: String) {}
        func search(_ word: String) -> Bool { false }
        func startsWith(_ prefix: String) -> Bool { false }
    }
}
```

In a playground:

```swift
final class Trie {
    func insert(_ word: String) {} // your solution
    func search(_ word: String) -> Bool { false }
    func startsWith(_ prefix: String) -> Bool { false }
}

enum Call {
    case insert(String)
    case search(String)
    case startsWith(String)
}

let cases: [([Call], [Bool])] = [
    ([.insert("cart"), .search("car"), .startsWith("car"), .insert("car"), .search("car"), .search("cart"), .startsWith("cat")], [false, true, true, true, false]),
    ([.insert("apple"), .search("app"), .startsWith("apple"), .search("apples")], [false, true, false]),
    ([.search("x"), .startsWith("x")], [false, false]),
]
for (calls, expected) in cases {
    let trie = Trie()
    var got: [Bool] = []
    for call in calls {
        switch call {
        case let .insert(word): trie.insert(word)
        case let .search(word): got.append(trie.search(word))
        case let .startsWith(prefix): got.append(trie.startsWith(prefix))
        }
    }
    print(got == expected ? "PASS" : "FAIL", got, "expected", expected)
}
```
:::

::: Pattern and cue
**Trie: a tree with one letter per step.** The cue is in the name, and in *"starts with"*: a question about prefixes over a set of words. Each node stands for one prefix; a flag marks the nodes where a whole word ends.
:::

::: Approach
Start from an empty root node. To insert a word, walk down from the root one letter at a time, following the child for that letter, and create the child when it's missing. At the last letter, mark the node as the end of a word. To answer either question, walk the same way without creating anything: if some letter has no child, the answer is no. If the walk finishes, `startsWith` is yes, because some inserted word passed through here; `search` is yes only if this node is marked as a word's end.

Time O(L) per call for a word or prefix of L letters, independent of how many words are stored. Space O(total letters inserted) at worst; shared prefixes are stored once.
:::

::: Swift solution
```swift
final class Trie {
    private final class Node {
        var children: [Character: Node] = [:]
        var isWord = false
    }

    private let root = Node()

    func insert(_ word: String) {
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
        find(word)?.isWord ?? false
    }

    func startsWith(_ prefix: String) -> Bool {
        find(prefix) != nil
    }

    /// The node where `text`'s path ends, or nil if the path breaks off.
    private func find(_ text: String) -> Node? {
        var node = root
        for character in text {
            guard let child = node.children[character] else { return nil }
            node = child
        }
        return node
    }
}
```

`search` and `startsWith` share one walk and differ only in the last check: `isWord` against "the path exists". Inserting the same word twice just sets the flag again.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, five more (a word inserted twice, a one-letter word, a prefix longer than every word, a 1,000-letter word, words that are prefixes of each other inserted longest first), a 2,000-letter word with the iterative `deinit` from the follow-up below, and 300 random call sequences checked against a `Set<String>` with `hasPrefix`.
:::

::: Walk it through
**insert("cart"), search("car"), startsWith("car"), insert("car"), search("car"), search("cart"), startsWith("cat")**

| Call | What happens | Returns |
|---|---|---|
| insert("cart") | creates `c → a → r → t`, marks `t` | — |
| search("car") | path `c → a → r` exists, `r` isn't marked | `false` |
| startsWith("car") | path `c → a → r` exists | `true` |
| insert("car") | path already there, marks `r` | — |
| search("car") | ends on `r`, now marked | `true` |
| search("cart") | ends on `t`, marked | `true` |
| startsWith("cat") | `a` has no child `t` | `false` |

**search("x") on an empty trie** — the root has no children at all, so the first letter breaks the path: `false`, and the same for `startsWith("x")`.
:::

::: The Swift trap
**The `default:` subscript reads without storing.** The neat-looking insert loop

```swift
for character in word {
    node = node.children[character, default: Node()]
}
```

compiles and is wrong: reading `children[character, default: Node()]` returns a brand-new node when the key is missing but doesn't put it in the dictionary. The loop walks down a chain of throwaway nodes, sets `isWord` on the last one, and the trie stays empty — every `search` is `false`. The `default:` subscript only stores when you *mutate through it* in place, as in `counts[c, default: 0] += 1`. With a class value you need the reference, so create the child, store it, then step into it.
:::

::: What they ask next
- **"Delete a word."** → Walk to its node and clear `isWord`; then, on the way back up (recursively), remove children that are no longer a word and have no children of their own.
- **"Return all words that start with a prefix, for autocomplete."** → Walk to the prefix's node, then depth-first through its subtree, collecting a word wherever `isWord` is set; sort the keys at each node for alphabetical order, and stop after k results for a suggestion list.
- **"Words can be 2,000 letters long. Anything else to worry about?"** → Freeing the trie: each node frees its children first, one stack level per letter, and a 2,000-letter chain crashed when freed on a 512 KB background thread; give `Trie` a `deinit` that empties the tree with an explicit stack (the code is in the [Tries primer](#/dsa/tries)).
:::
