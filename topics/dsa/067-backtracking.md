---
title: Backtracking — the idea
summary: Build every possible answer one choice at a time, undoing the last choice to try the next one, and stop early on branches that can't work.
group: Backtracking
minutes: 10
sources:
- Wikipedia · Backtracking | https://en.wikipedia.org/wiki/Backtracking
- Swift language guide · Nested functions | https://docs.swift.org/swift-book/documentation/the-swift-programming-language/functions/#Nested-Functions
- Swift standard library · Sequence.lexicographicallyPrecedes(_:) | https://developer.apple.com/documentation/swift/sequence/lexicographicallyprecedes(_:)
---

Some questions don't have a clever shortcut: they ask for *every* arrangement that fits. Backtracking is the disciplined way to list them all without missing one or producing one twice. The answer is exponential in size, so the code can't be faster than exponential; the skill is writing it cleanly and cutting dead branches early.

## When to reach for it

- **"All subsets"**, **"all combinations"**, **"all permutations"**, **"all arrangements"**, **"every way to …"**.
- **"Return the list of …"** where the list itself can be exponentially long.
- A **target to hit by picking items** (a sum, a length) with every valid pick to return.
- A **path through a grid** that may not reuse a cell: word search, mazes.
- Small inputs: n up to about 10–20 is the hint that exponential is expected.

## The idea in plain words

Think of trying outfits from a small wardrobe. You pick a shirt, then trousers, then shoes. When the outfit is complete you write it down, take the shoes off, and try the next pair. When you've tried every pair of shoes, you take the trousers off too and try the next trousers, and so on back up. You never start from scratch; you only undo the *last* choice and try its next option. And if a shirt clashes with every pair of trousers, you stop trying shoes with it at all: that is pruning.

In code: one growing **path** (the current partial answer), and a function that, for each option still allowed, **chooses** it (append), **explores** everything that follows (recursive call), then **un-chooses** it (remove last). Whenever the path is a complete answer, a copy goes into the results.

## The template in Swift

All the ways to pick `size` items from a list, order not mattering:

```swift
func combinations<Item>(of items: [Item], size: Int) -> [[Item]] {
    var results: [[Item]] = []
    var path: [Item] = []

    func explore(from start: Int) {
        if path.count == size {                           // a complete answer
            results.append(path)                          // appending copies the array: a snapshot
            return
        }
        guard items.count - start >= size - path.count else { return }   // prune: not enough items left
        for index in start..<items.count {
            path.append(items[index])                     // choose
            explore(from: index + 1)                      // explore: only later items, so no repeats
            path.removeLast()                             // un-choose
        }
    }

    explore(from: 0)
    return results
}
```

`explore` is a nested function: it reads and changes `results` and `path` from the enclosing function directly, so nothing has to be passed down or returned up.

## Variations

- **Record at every step, not only at the end.** Every partial path is an answer: Subsets. Same loop from `start`, no completeness check.
- **Order matters, every item once.** The loop always starts at 0 and skips items already on the path, tracked with a `used` array: Permutations.
- **Items may repeat, and a target prunes.** Recurse with `index` instead of `index + 1` so the same item can be picked again, and stop when the running total passes the target; sorting first lets you `break` instead of `continue`: Combination Sum.
- **The choices are neighbours in a grid.** Choose a neighbouring cell, mark it visited, explore, unmark it: Word Search. The "un-choose" step is the unmarking.

## Complexity

It is the size of the output times the cost of copying each answer. Subsets of n items: 2ⁿ answers, each copied in up to O(n), so O(n · 2ⁿ). Permutations: n! answers, O(n · n!). A grid word search: each start cell can branch into 3 directions per letter, O(rows · columns · 3ᴸ) for a word of length L. Space besides the output is the recursion depth plus the path: O(n), or O(L) for the grid.

Saying "this is exponential, and it has to be, because the answer itself is that big" is part of the expected answer.

## Swift traps

- **`results.append(path)` is already a copy.** Swift arrays are values, so you don't need the `path[:]` or `new ArrayList<>(path)` that Python and Java need; later changes to `path` don't touch the stored answer. The copy still costs O(length), which is where the extra factor of n in the complexity comes from.
- **`[[Int]]` has no `.sorted()`.** `Array` isn't `Comparable`, so sorting a list of answers to compare it with an expected one doesn't compile until you write `sorted { $0.lexicographicallyPrecedes($1) }`. Decide whether to sort *inside* each answer too: yes for subsets and combinations (order inside doesn't matter), never for permutations (order inside is the answer).
- **`start..<end` traps when `start > end`.** A `Range` with its lower bound above its upper bound is a runtime crash, not an empty loop. `index + 1` never passes `count`, so the template is safe; hand-written bounds like `start..<target` need the check.
- **Recursion depth is the input size.** Fine at the n ≤ 20 these problems allow; Swift has no tail-call guarantee, so don't recurse once per *output* item.
- **Passing a slice down keeps the parent's indices.** Recursing on `Array(items[index...])` copies every time; recursing on `items[index...]` as an `ArraySlice` doesn't copy but starts at `index`, not 0. Passing a start index, as above, avoids both.

## The problems in this topic

- [57 · Subsets](#/dsa/subsets) — Medium
- [58 · Permutations](#/dsa/permutations) — Medium
- [59 · Combination Sum](#/dsa/combination-sum) — Medium
- [60 · Word Search](#/dsa/word-search) — Medium
