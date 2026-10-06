---
title: 2-D dynamic programming — the idea
summary: When one position isn't enough to describe a smaller question, describe it with two — a row and a column, or a place in each of two strings — and fill a grid of answers.
group: 2-D dynamic programming
minutes: 8
sources:
- Swift standard library · Array.init(repeating:count:) | https://developer.apple.com/documentation/swift/array/init(repeating:count:)
---

1-D dynamic programming fills a row of boxes, one per position. Some questions need **two** numbers to say which smaller question you mean: "how many paths reach row 3, column 5?" or "what's the longest common part of the first 4 letters of one word and the first 7 of another?". Then the boxes form a grid, each box is filled from its neighbours above and to the left, and the answer sits in a corner. Everything from the 1-D primer carries over — subproblem, recurrence, base cases, fill order — with one more index.

## When to reach for it

- The input is a **grid** and you move in limited directions ("only right or down"), counting paths or minimising cost.
- The input is **two strings or two arrays**, and the question compares them: longest common part, fewest edits to turn one into the other, can one be interleaved from two others.
- A single sequence plus a **budget**: items and a capacity (knapsack), positions and a number of moves left.
- The 1-D subproblem sentence needs an "and": "the best for the first i letters of `a` **and** the first j of `b`".

## The idea in plain words

Think of a times table on squared paper. Each square holds the answer for its row and column, and you fill it in using only squares already filled: the one above, the one to the left, or the one diagonally up-left. The top row and left column are the easy edges — the base cases — usually all 0s or all 1s. You fill row by row, left to right, so every square's neighbours are ready when you reach it. The answer is the bottom-right square.

For two strings, the rows are "how many letters of the first word" (0 to its length) and the columns "how many of the second". The extra row and column for **zero letters** are the base cases: an empty word has nothing in common with anything, and turning an empty word into one of length j takes j insertions.

## The template in Swift

```swift
// Grid: cheapest path from the top-left to the bottom-right, moving only right or down.
func cheapestPath(_ grid: [[Int]]) -> Int {
    let rows = grid.count, columns = grid[0].count
    // rows × columns, all 0. The INNER count is the number of columns.
    var cost = Array(repeating: Array(repeating: 0, count: columns), count: rows)
    for row in 0..<rows {
        for column in 0..<columns {
            let cheapestBefore: Int
            switch (row, column) {
            case (0, 0): cheapestBefore = 0                                   // the start
            case (0, _): cheapestBefore = cost[row][column - 1]               // top edge: only from the left
            case (_, 0): cheapestBefore = cost[row - 1][column]               // left edge: only from above
            default:     cheapestBefore = min(cost[row - 1][column], cost[row][column - 1])
            }
            cost[row][column] = cheapestBefore + grid[row][column]
        }
    }
    return cost[rows - 1][columns - 1]
}

// Two strings: fewest single-letter inserts, deletes or replacements to turn `a` into `b`.
func editDistance(_ a: String, _ b: String) -> Int {
    let a = Array(a), b = Array(b)
    // (a.count + 1) × (b.count + 1): row 0 and column 0 mean "zero letters so far".
    var edits = Array(repeating: Array(repeating: 0, count: b.count + 1), count: a.count + 1)
    for i in 0...a.count { edits[i][0] = i }       // delete all i letters
    for j in 0...b.count { edits[0][j] = j }       // insert all j letters
    for i in a.indices {
        for j in b.indices {
            edits[i + 1][j + 1] = a[i] == b[j]
                ? edits[i][j]                                         // last letters match: free
                : 1 + min(edits[i][j], edits[i][j + 1], edits[i + 1][j])  // replace, delete, insert
        }
    }
    return edits[a.count][b.count]
}

let cheapest = cheapestPath([[2, 1, 4], [3, 9, 1], [5, 1, 2]])   // 10: right, right, down, down
let edits = editDistance("flaw", "lawn")                           // 2: delete f, add n
```

Writing table position `i + 1` for letter `i` is what lets the loops run over `indices` while the zero row and column hold the base cases.

## Variations

- **Count paths in a grid.** Each square adds the square above and the square to the left: Unique Paths. With blocked squares, a blocked square is 0.
- **Cost or value over a grid.** The same fill with `min` or `max` instead of `+`: cheapest path, largest square of 1s.
- **Two strings, diagonal on a match.** When the current letters match, step diagonally; otherwise take the best of dropping a letter from either word: Longest Common Subsequence, and edit distance with its three moves.
- **Roll the grid into one row.** Each row reads only the row above (and itself), so keep one row and overwrite it left to right. For the diagonal case, save the old up-left value in a variable before you overwrite it.

## Complexity

Time is the number of squares times the work per square: O(rows × columns) for a grid, O(m × n) for two strings of lengths m and n, with O(1) per square. Space is O(rows × columns) for the full table, or O(columns) once rolled into a single row — make the row the shorter dimension.

## Swift traps

- **`Array(repeating: Array(repeating: 0, count: columns), count: rows)` — the inner count is the columns.** Swapping them works on square grids and traps with "Index out of range" on the first non-square one, so always test a non-square example.
- **Nested arrays are values, not shared rows.** `Array(repeating: row, count: n)` makes n independent copies (copy-on-write), so writing one row doesn't change the others — unlike a repeated class instance or Python's `[[0] * n] * m`. The flip side: `var row = table[i]; row[j] = 1` changes only the copy, not the table.
- **Index −1 traps.** `table[i - 1][j]` at i = 0 crashes; either handle the edges separately (the grid template) or add a padding row and column of base cases (the strings template).
- **`0...a.count` is fine, `1...a.count` isn't always.** A closed range from 1 to 0 traps when a string is empty; loop over `indices` and write to `i + 1`.
- **No integer subscript on `String`.** Convert each string once with `Array(_:)` before the loops.
- **`[[Int]]` is an array of separate arrays.** For large tables, one flat `[Int]` of size rows × columns indexed `row * columns + column` is faster; say it, don't start with it.

## The problems in this topic

- [82 · Unique Paths](#/dsa/unique-paths) — Medium
- [83 · Longest Common Subsequence](#/dsa/longest-common-subsequence) — Medium
