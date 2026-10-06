---
title: 82 · Unique Paths
summary: Count the routes from the top-left corner of a grid to the bottom-right corner when every move goes one square right or one square down.
group: 2-D dynamic programming
minutes: 20
sources:
- LeetCode 62 · Unique Paths | https://leetcode.com/problems/unique-paths/
- Swift standard library · Array.init(repeating:count:) | https://developer.apple.com/documentation/swift/array/init(repeating:count:)
---

*Medium · G*

A robot stands on the top-left square of a grid with a given number of rows and columns. Each move takes it one square to the right or one square down — never left, never up. Count the different routes that bring it to the bottom-right square.

| Rows | Columns | Answer |
|---|---|---|
| `2` | `3` | `3` — RRD, RDR, DRR |
| `4` | `4` | `20` |
| `1` | `5` | `1` — a single row allows only one route: straight right |

Constraints that matter: rows and columns are each between 1 and 100, and the answer fits in a 32-bit integer (at most 2 × 10⁹). Walking every route is exponential; the target is O(rows × columns) time, and O(columns) space is the usual follow-up.

::: Starter code and tests
In an Xcode test target:

```swift
import Testing

struct UniquePathsTests {

    @Test(arguments: [
        (2, 3, 3),
        (4, 4, 20),
        (1, 5, 1),
    ])
    func countsTheRightAndDownRoutesToTheCorner(rows: Int, columns: Int, expected: Int) {
        #expect(uniquePaths(rows, columns) == expected)
    }

    // MARK: - Privates
    private func uniquePaths(_ rows: Int, _ columns: Int) -> Int {
        0
    }
}
```

In a playground:

```swift
func uniquePaths(_ rows: Int, _ columns: Int) -> Int {
    0 // your solution
}

let cases: [(Int, Int, Int)] = [
    (2, 3, 3),
    (4, 4, 20),
    (1, 5, 1),
]
for (rows, columns, expected) in cases {
    let got = uniquePaths(rows, columns)
    print(got == expected ? "PASS" : "FAIL", rows, columns, "→", got, "expected", expected)
}
```
:::

::: Pattern and cue
**2-D dynamic programming on a grid, counting.** The cue is *"how many routes"* on a *grid* with moves restricted to *right or down*. Every route into a square arrives either from the square above it or from the square to its left, and those two groups of routes never overlap — so a square's count is the sum of two neighbours' counts, which are filled before it if you go row by row.
:::

::: Approach
Subproblem: the number of routes from the start to the square at row r, column c. Recurrence: routes to (r, c) = routes to (r − 1, c) + routes to (r, c − 1).

Make a table with one entry per square. Every square in the top row can only be reached by going straight right, and every square in the left column by going straight down, so they all hold 1. Fill the rest row by row, left to right: each square is the sum of the square above and the square to its left, both already filled. The bottom-right square holds the answer.

Time O(rows × columns): one addition per square. Space O(rows × columns) for the table — O(columns) once rolled into a single row (see the follow-ups).
:::

::: Swift solution
```swift
func uniquePaths(_ rows: Int, _ columns: Int) -> Int {
    // rows × columns, all 1: the top row and left column are already right.
    var routes = Array(repeating: Array(repeating: 1, count: columns), count: rows)
    for row in 1..<rows {
        for column in 1..<columns {
            routes[row][column] = routes[row - 1][column] + routes[row][column - 1]
        }
    }
    return routes[rows - 1][columns - 1]
}
```

Starting every square at 1 makes the edges correct for free, so both loops begin at 1. With one row or one column, `1..<1` is simply empty and the answer is the 1 already there.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, four more (1 × 1, 5 × 1, 3 × 7, and 23 × 12 → 193,536,720), and every grid up to 9 × 9 checked against a brute-force recursion over the routes.
:::

::: Walk it through
**2 rows, 3 columns**

| | col 0 | col 1 | col 2 |
|---|---|---|---|
| row 0 | 1 | 1 | 1 |
| row 1 | 1 | 1 + 1 = 2 | 1 + 2 = 3 |

Answer 3.

**1 row, 5 columns** — the table is one row of 1s; the outer loop `1..<1` doesn't run. Answer 1.
:::

::: The Swift trap
**The nested `Array(repeating:)` reads inside out: the inner count is the number of columns.** `Array(repeating: Array(repeating: 1, count: columns), count: rows)` builds `rows` arrays of `columns` entries, so `routes[row][column]` is the right order. Swap the two counts and every square grid still passes — `4 × 4` gives 20 — while the first non-square grid traps with "Index out of range" — the rows are too short for the column indices. That's why the examples include `2 × 3` and `1 × 5`: test a non-square grid before you claim it works.

A second, smaller one: the repeated inner array is a **value**. Each row is its own copy, so writing `routes[1][1]` doesn't change `routes[0][1]` — unlike repeating a class instance, which would share one object across every row.
:::

::: What they ask next
- **"Use O(columns) memory."** → Keep one row; for each new row, sweep left to right with `row[c] += row[c - 1]`: before the update `row[c]` is the square above, `row[c - 1]` is already the square to the left.
- **"Some squares are blocked (Unique Paths II)."** → A blocked square holds 0, and the edges are no longer all 1: an edge square is 1 only until the first block, then 0.
- **"Do it without a table."** → Every route is some arrangement of rows − 1 downs and columns − 1 rights, so the answer is the binomial C(rows + columns − 2, rows − 1); compute it with a running product that divides at each step to stay exact and small.
:::
