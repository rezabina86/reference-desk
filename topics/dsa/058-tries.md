---
title: Tries — the idea
summary: A tree of letters in which words that start the same share a path, so prefix questions cost the length of the prefix, not the number of words.
group: Tries
minutes: 7
sources:
- Wikipedia · Trie | https://en.wikipedia.org/wiki/Trie
- Swift standard library · Dictionary.subscript(_:default:) | https://developer.apple.com/documentation/swift/dictionary/subscript(_:default:)-45arb
---

A trie (said "try", from re*trie*val) stores a set of words as a tree of letters. It answers one kind of question very well: *which words start like this?*

## When to reach for it

- **"Prefix"**, **"starts with"**, **"autocomplete"**, **"suggestions"** over a fixed list of words.
- **Many lookups against one dictionary of words**, where a `Set<String>` can only answer "is this exact word in it?".
- **A wildcard** in the search (`.` for any one letter), so a hash lookup can't be used directly.
- Searching a grid or a long text for **many words at once** (Word Search II), where one shared tree replaces one search per word.

## The idea in plain words

Think of the contacts search on a phone. Type `M` and the list narrows to names starting with M; type `a` and it narrows again to `Ma…`. A trie is that narrowing, built into the data. The root stands for "nothing typed yet". Each step down follows one letter, so every node stands for one prefix, and words that begin the same way share the same first steps. `car`, `card` and `cart` share the path `c → a → r`, then split.

The path alone can't say whether a prefix is also a word: `car` is a word and lies on the way to `card`, while `ca` is not. So each node carries one flag, *a word ends here*.

## The template in Swift

```swift
final class TrieNode {
    var children: [Character: TrieNode] = [:]
    var isWord = false
}

final class PrefixTree {
    private let root = TrieNode()

    func insert(_ word: String) {
        var node = root
        for character in word {
            if let child = node.children[character] {
                node = child
            } else {
                let child = TrieNode()
                node.children[character] = child      // store it, then step into it
                node = child
            }
        }
        node.isWord = true
    }

    /// The node at the end of `text`'s path, or nil if the path breaks off.
    private func node(for text: String) -> TrieNode? {
        var node = root
        for character in text {
            guard let child = node.children[character] else { return nil }
            node = child
        }
        return node
    }

    func contains(_ word: String) -> Bool { node(for: word)?.isWord ?? false }

    func hasPrefix(_ prefix: String) -> Bool { node(for: prefix) != nil }

    /// Every stored word that starts with `prefix`, in alphabetical order.
    func words(withPrefix prefix: String) -> [String] {
        guard let start = node(for: prefix) else { return [] }
        var result: [String] = []
        func collect(_ node: TrieNode, _ path: String) {
            if node.isWord { result.append(path) }
            for character in node.children.keys.sorted() {
                collect(node.children[character]!, path + String(character))
            }
        }
        collect(start, prefix)
        return result
    }
}
```

## Variations

- **Exact word versus prefix.** The same walk; a word needs the flag at the end, a prefix only needs the path to exist.
- **Wildcard search.** At a `.`, there is no single child to follow, so try every child and succeed if any branch does — a depth-first search that branches only where the pattern does.
- **Collect everything under a prefix.** Walk to the prefix's node, then visit the whole subtree below it, as in `words(withPrefix:)`: this is autocomplete.
- **Trie plus a grid search.** Put all the words in one trie and walk the grid and the trie together, abandoning a path as soon as the trie has no such prefix.

## Complexity

Insert, exact search and prefix search are O(L) for a word or prefix of length L, whatever the number of words stored — that independence is the whole point. Space is O(total characters inserted) in the worst case, less when words share prefixes. A wildcard search can visit far more: with every letter a `.`, it may walk every node down to that depth.

## Swift traps

- **`children[c, default: TrieNode()]` used as a value doesn't store anything.** `node = node.children[character, default: TrieNode()]` compiles and hands back a fresh node that is never added to the dictionary, so every insert is silently lost and every search returns false. Store the new child first, as the template does.
- **A node must be a class.** With a struct, `var node = root` is a copy, and changing the copy's children or flag never reaches the tree.
- **`[Character: TrieNode]` or an array of 26?** An array indexed by letter is faster and is the textbook answer, but it assumes lowercase English. `Character.asciiValue` is a `UInt8?`, and `Int(c.asciiValue! - 97)` traps on anything below `a`; convert first: `Int(c.asciiValue!) - 97`. The dictionary works for any `Character`, including accented letters and emoji, each of which is a single `Character` in Swift.
- **A very long word can crash the app when the trie is freed.** Releasing a node releases its dictionary, which releases each child, which releases *its* dictionary — one level of stack per letter, with nothing in your code that looks recursive. A single 2,000-letter word (the limit in Implement Trie) crashed both a debug and a release build when the trie was freed on a background thread with the usual 512 KB stack — the debug build already at 1,100 levels, on Swift 6.4 — and Swift Testing runs tests on background threads. Real words are fine; if long ones are possible, empty the tree with an explicit stack when it goes away, as below.

```swift
// inside PrefixTree
deinit {
    var pending = Array(root.children.values)
    root.children.removeAll()
    while let node = pending.popLast() {
        pending.append(contentsOf: node.children.values)
        node.children.removeAll()        // so freeing `node` has nothing left to recurse into
    }
}
```

The recursive searches in this topic also use one stack frame per letter; Add and Search Words caps words at 25 letters, nowhere near the limit.

## The problems in this topic

- [50 · Implement Trie (Prefix Tree)](#/dsa/implement-trie-prefix-tree) — Medium
- [51 · Design Add and Search Words Data Structure](#/dsa/design-add-and-search-words-data-structure) — Medium
