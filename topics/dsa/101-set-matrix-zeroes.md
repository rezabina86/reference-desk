---
title: 84 · Set Matrix Zeroes
summary: Wherever a grid holds a 0, wipe that cell's whole row and whole column to 0, changing the grid you were given and using almost no extra memory.
group: Matrix
minutes: 25
sources:
- LeetCode 73 · Set Matrix Zeroes | https://leetcode.com/problems/set-matrix-zeroes/
- The Swift Programming Language · Structures and Classes Are Value Types | https://docs.swift.org/swift-book/documentation/the-swift-programming-language/classesandstructures/#Structures-and-Enumerations-Are-Value-Types
---

*Medium · G*

You get a grid of integers with m rows and n columns. Every cell that holds a 0 in the **original** grid spreads: its entire row and its entire column become 0. Change the grid you were given rather than returning a new one. A 0 created by this spreading does not spread any further — only the zeros that were there at the start count.

| Grid | After |
|---|---|
| `[[1, 2, 3], [4, 0, 6], [7, 8, 9]]` | `[[1, 0, 3], [0, 0, 0], [7, 0, 9]]` |
| `[[0, 2, 3, 0], [5, 6, 7, 8], [1, 1, 4, 2]]` | `[[0, 0, 0, 0], [0, 6, 7, 0], [0, 1, 4, 0]]` — zeros in the first row |
| `[[3], [0], [4]]` | `[[0], [0], [0]]` — a single column |

Constraints that matter: between 1 and 200 rows and columns; values are any 32-bit integers. Two sets of "rows to clear" and "columns to clear" is an accepted O(m + n)-space answer; the target is O(1) extra space, with O(m × n) time.

::: Starter code and tests
In an Xcode test target:

```swift
import Testing

struct SetMatrixZeroesTests {

    @Test(arguments: [
        ([[1, 2, 3], [4, 0, 6], [7, 8, 9]], [[1, 0, 3], [0, 0, 0], [7, 0, 9]]),
        ([[0, 2, 3, 0], [5, 6, 7, 8], [1, 1, 4, 2]], [[0, 0, 0, 0], [0, 6, 7, 0], [0, 1, 4, 0]]),
        ([[3], [0], [4]], [[0], [0], [0]]),
    ])
    func zeroesTheRowAndColumnOfEveryOriginalZero(input: [[Int]], expected: [[Int]]) {
        var matrix = input
        setZeroes(&matrix)
        #expect(matrix == expected)
    }

    // MARK: - Privates
    private func setZeroes(_ matrix: inout [[Int]]) {
    }
}
```

In a playground:

```swift
func setZeroes(_ matrix: inout [[Int]]) {
    // your solution
}

let cases: [([[Int]], [[Int]])] = [
    ([[1, 2, 3], [4, 0, 6], [7, 8, 9]], [[1, 0, 3], [0, 0, 0], [7, 0, 9]]),
    ([[0, 2, 3, 0], [5, 6, 7, 8], [1, 1, 4, 2]], [[0, 0, 0, 0], [0, 6, 7, 0], [0, 1, 4, 0]]),
    ([[3], [0], [4]], [[0], [0], [0]]),
]
for (input, expected) in cases {
    var matrix = input
    setZeroes(&matrix)
    print(matrix == expected ? "PASS" : "FAIL", input, "→", matrix, "expected", expected)
}
```
:::

::: Pattern and cue
**Mark in place, using the first row and column as storage.** The cue is *"in place"* together with *"constant extra space"* on a grid where the decision is per row and per column. You need one yes/no note per row and per column; the grid already has a row of n cells and a column of m cells you can borrow for those notes.
:::

::: Approach
Zeroing as soon as you find a 0 doesn't work: the new zeros look like original ones and wipe out everything. So split the job into "decide" and "apply". First, remember in two flags whether the first row and the first column contain a 0 of their own. Then scan the rest of the grid; for every 0 you find, write a 0 at the start of its row (in the first column) and at the top of its column (in the first row) — those cells are going to be zero anyway. Next, go over the rest of the grid again and clear every cell whose row-start or column-top holds a 0. Last, use the two flags to clear the first row and first column themselves; they go last because they hold the notes everything else reads.

Time O(m × n): two passes over the grid plus one over each edge. Space O(1): two flags and the loop indices.
:::

::: Swift solution
```swift
func setZeroes(_ matrix: inout [[Int]]) {
    guard let columnCount = matrix.first?.count, columnCount > 0 else { return }
    let rowCount = matrix.count
    let firstRowHasZero = matrix[0].contains(0)
    let firstColumnHasZero = matrix.contains { $0[0] == 0 }

    // 1. Mark: a zero inside the grid writes a 0 at the head of its row and of its column.
    for row in 1..<rowCount {
        for column in 1..<columnCount where matrix[row][column] == 0 {
            matrix[row][0] = 0
            matrix[0][column] = 0
        }
    }
    // 2. Clear the inside, reading the marks.
    for row in 1..<rowCount {
        for column in 1..<columnCount where matrix[row][0] == 0 || matrix[0][column] == 0 {
            matrix[row][column] = 0
        }
    }
    // 3. Clear the marker row and column last, from the two flags saved at the start.
    if firstRowHasZero {
        for column in 0..<columnCount { matrix[0][column] = 0 }
    }
    if firstColumnHasZero {
        for row in 0..<rowCount { matrix[row][0] = 0 }
    }
}
```

The two flags are read before any marks are written; once step 1 runs, a 0 in the first row could be an original or a note, and you can no longer tell which. The `guard` matters too: with zero columns, `1..<columnCount` would be `1..<0`, and a range whose end is below its start traps.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, nine more (an empty grid, one empty row, `[[5]]`, `[[0]]`, a single row, a grid with no zeros, zeros on the anti-diagonal `[[1, 0], [0, 1]]`, a zero only in the first column, zeros inside and in the first column at once), and 3,000 random grids up to 6 × 6 checked against a brute force that collects zero rows and columns in two sets.
:::

::: Walk it through
**`[[1, 2, 3], [4, 0, 6], [7, 8, 9]]`** — first row and first column have no zero: both flags false.

| Step | Grid | What happened |
|---|---|---|
| Mark | `[[1, 0, 3], [0, 0, 6], [7, 8, 9]]` | the 0 at (1, 1) writes a 0 at the head of row 1, (1, 0), and the top of column 1, (0, 1) |
| Clear inside | `[[1, 0, 3], [0, 0, 0], [7, 0, 9]]` | row 1 is marked, so (1, 2) clears; column 1 is marked, so (2, 1) clears |
| Edges | unchanged | both flags are false |

The note at (0, 1) is itself the right final value: the column was going to be zero anyway.

**`[[0, 2, 3, 0], [5, 6, 7, 8], [1, 1, 4, 2]]`** — both flags are true, because (0, 0) is a 0. The inside (rows 1–2, columns 1–3) has no zeros, so the mark step writes nothing. Clearing the inside reads the existing 0 at (0, 3) as a column note and clears (1, 3) and (2, 3). Then the flags clear the whole first row and the whole first column: `[[0, 0, 0, 0], [0, 6, 7, 0], [0, 1, 4, 0]]`. An original 0 in the first row and a note look identical — which is fine, because both mean "clear this column".
:::

::: The Swift trap
**Looping over rows gives you copies.** The natural way to clear a row, `for var row in matrix { … row[c] = 0 … }`, compiles without a warning and changes nothing: `[[Int]]` is an array of values, so `row` is a private copy. The same goes for `var firstRow = matrix[0]` followed by writes. Always write through the grid, `matrix[row][column] = 0`; Swift then mutates the stored row in place without copying it, because the function owns the only reference.
:::

::: What they ask next
- **"Do it with O(m + n) space first."** → Two `Set<Int>`s (or two `[Bool]` arrays) of rows and columns that hold a 0, filled in one pass, applied in a second. Simpler, and a fine opening answer to improve on.
- **"Why can't you mark with a sentinel like -1?"** → Any integer value could be a real entry; the first-row/column trick works because those cells will become 0 anyway.
- **"Can you do it with one flag?"** → Let the corner cell (0, 0) be the first row's note and keep a single flag for the first column; then the order matters: clear the inside, then the first row from the corner, then the first column from the flag.
:::
