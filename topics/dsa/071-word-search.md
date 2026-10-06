---
title: 60 · Word Search
summary: Given a grid of letters and a word, say whether the word can be traced through the grid by stepping between side-by-side cells without using any cell twice.
group: Backtracking
minutes: 25
sources:
- LeetCode 79 · Word Search | https://leetcode.com/problems/word-search/
- Swift language guide · Defer statement | https://docs.swift.org/swift-book/documentation/the-swift-programming-language/statements/#Defer-Statement
---

*Medium · G*

You get a rectangular grid of letters and a word. Return `true` if the word can be spelled by starting at any cell and moving, one letter at a time, to a cell directly above, below, left or right of the current one, never diagonally. A cell may be used at most once within one spelling. Otherwise return `false`.

The grid used in the first two examples:

```text
C A T
O R E
D O G
```

| Grid | Word | Answer |
|---|---|---|
| the grid above | `"RATE"` | `true` — R (middle) → A (up) → T (right) → E (down) |
| the grid above | `"ROD"` | `true` — R → O (down) → D (left) |
| `A B` (one row) | `"ABA"` | `false` — the only A would have to be used twice |

Constraints that matter: the grid is at most 6 × 6, the word at most 15 letters, upper- and lower-case English letters only. Every start cell can branch three ways per letter, so the search is exponential in the word length; the goal is to cut each branch at the first wrong letter and to undo every "visited" mark on the way back.

::: Starter code and tests
The grid is passed to the test as an array of strings, one per row, and turned into `[[Character]]` inside it.

In an Xcode test target:

```swift
import Testing

struct WordSearchTests {

    @Test(arguments: [
        (["CAT", "ORE", "DOG"], "RATE", true),
        (["CAT", "ORE", "DOG"], "ROD", true),
        (["AB"], "ABA", false),
    ])
    func reportsWhetherTheWordCanBeTracedThroughNeighbouringCells(rows: [String], word: String, expected: Bool) {
        let board = rows.map { Array($0) }
        #expect(exist(board, word) == expected)
    }

    // MARK: - Privates
    private func exist(_ board: [[Character]], _ word: String) -> Bool {
        false
    }
}
```

In a playground:

```swift
func exist(_ board: [[Character]], _ word: String) -> Bool {
    false // your solution
}

let cases: [([String], String, Bool)] = [
    (["CAT", "ORE", "DOG"], "RATE", true),
    (["CAT", "ORE", "DOG"], "ROD", true),
    (["AB"], "ABA", false),
]
for (rows, word, expected) in cases {
    let got = exist(rows.map { Array($0) }, word)
    print(got == expected ? "PASS" : "FAIL", rows, word, "→", got, "expected", expected)
}
```
:::

::: Pattern and cue
**Backtracking on a grid.** The cue is *"neighbouring cells"* plus *"a cell may not be used twice"*: you are searching for a path, every step has up to four choices, and a cell's "used" status must be set while the path runs through it and cleared when the path backs out. Choose a neighbour, explore, un-choose.
:::

::: Approach
Try every cell as the starting point. From a cell, the search asks: does this cell hold the next letter of the word, and is it not already on the current path? If not, this branch is dead. If so, mark the cell as used, and ask the same question of its four neighbours for the following letter. Whatever the answer, clear the mark before returning, so other paths can use the cell. When the letter count reaches the end of the word, the whole word has been traced.

Time O(r · c · 3ᴸ) for an r × c grid and a word of length L: each start cell begins a search that branches into at most three new cells per letter (the fourth neighbour is where it came from). Space O(L) for the recursion plus O(r · c) for the visited marks.
:::

::: Swift solution
```swift
func exist(_ board: [[Character]], _ word: String) -> Bool {
    let letters = Array(word)
    guard !letters.isEmpty else { return true }
    guard let columns = board.first?.count, columns > 0 else { return false }
    let rows = board.count
    var visited = Array(repeating: Array(repeating: false, count: columns), count: rows)

    func search(_ row: Int, _ column: Int, _ index: Int) -> Bool {
        guard row >= 0, row < rows, column >= 0, column < columns,
              !visited[row][column],
              board[row][column] == letters[index] else { return false }
        if index == letters.count - 1 { return true }       // the last letter matched

        visited[row][column] = true                          // choose
        defer { visited[row][column] = false }               // un-choose on every way out
        return search(row + 1, column, index + 1)
            || search(row - 1, column, index + 1)
            || search(row, column + 1, index + 1)
            || search(row, column - 1, index + 1)
    }

    for row in 0..<rows {
        for column in 0..<columns where search(row, column, 0) {
            return true
        }
    }
    return false
}
```

The `defer` is the un-choose step: it runs whichever of the four calls returns `true` first, and also when all four fail, so the mark can't leak into the next path. `||` stops at the first `true`, so a found word ends the search immediately.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, ten more (a one-cell grid matching and not matching, two paths that turn a corner and a twin where the corner is missing, a word that needs a cell twice in a 2 × 2 grid and the same grid traced without reuse, a 3 × 3 grid of one repeated letter with a word that fills every cell and one a letter too long to fit, a word whose letters are all present but not adjacent), and 1,000 random small grids checked against a brute force that enumerates every simple path in the grid; half of the words were read off a random walk so `true` cases are common.
:::

::: Walk it through
**`"ROD"`** on the grid above. Rows and columns count from 0.

| Call (row, column, index) | Cell | Wanted | Result |
|---|---|---|---|
| starts at (0,0) … (1,0) | C, A, T, O | R | each fails at once |
| (1,1), 0 | R | R | match; mark (1,1); try down |
| (2,1), 1 | O | O | match; mark (2,1); try down |
| (3,1), 2 | — | D | outside the grid: false; try up |
| (1,1), 2 | R | D | visited: false; try right |
| (2,2), 2 | G | D | false; try left |
| (2,0), 2 | D | D | last letter: **true** |

Each `defer` clears its mark as the `true` travels back up, and the outer loop returns `true`.

**`["AB"]`, `"ABA"`** — from (0,0): A matches, marked; right to (0,1): B matches, marked; its neighbours are outside the grid or (0,0), which is visited. Every branch fails, the marks are cleared, and starting at (0,1) fails on the first letter. Answer `false`.
:::

::: The Swift trap
**A `String` can't be indexed by the letter number, and a grid passed down the recursion by value gets copied.** `word[index]` doesn't compile; converting once with `Array(word)` gives `[Character]` and O(1) access for the whole search. The quieter trap is the visited marks: if you write the search as a separate function that receives the grid (or the visited marks) as an ordinary parameter, Swift won't let you write to it, and the obvious fix, `var marked = grid` then passing `marked` down, copies the whole grid at the first write in every call: O(r · c) extra per step. Keep one grid in the enclosing function and let the nested function capture it, as above, or pass it `inout`. And the popular trick of overwriting the cell with `"#"` instead of a visited grid is fine only while the word can't contain `#`; a separate `visited` grid has no such condition.
:::

::: What they ask next
- **"Many words, one grid: return every word that appears."** → Word Search II: put the words in a trie and run one search per start cell that walks the trie alongside the grid, pruning when no word has the current prefix.
- **"Can you fail fast before searching?"** → Count the letters: if the grid has fewer of any letter than the word needs, return `false` at once. And if the word's last letter is rarer in the grid than its first, search for the reversed word.
- **"Diagonal moves are allowed too."** → Eight neighbours instead of four; the same code with a list of direction offsets, and the branching factor becomes 7.
:::
