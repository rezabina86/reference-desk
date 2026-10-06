---
title: 86 · Rotate Image
summary: Turn a square grid of numbers a quarter turn clockwise, changing the grid you were given instead of building a new one.
group: Matrix
minutes: 25
sources:
- LeetCode 48 · Rotate Image | https://leetcode.com/problems/rotate-image/
- The Swift Programming Language · Memory Safety (conflicting access to in-out parameters) | https://docs.swift.org/swift-book/documentation/the-swift-programming-language/memorysafety/
---

*Medium · G*

You get an n × n grid of integers — think of the pixels of a square picture. Turn it 90 degrees clockwise, so the left column becomes the top row, read from bottom to top. You must change the grid you were given: no second grid, not even temporarily.

| Grid | After |
|---|---|
| `[[1, 2, 3], [4, 5, 6], [7, 8, 9]]` | `[[7, 4, 1], [8, 5, 2], [9, 6, 3]]` |
| `[[1, 2], [3, 4]]` | `[[3, 1], [4, 2]]` |
| `[[42]]` | `[[42]]` — one cell turns into itself |

Constraints that matter: n is between 1 and 20, values from −1,000 to 1,000. "In place" means O(1) extra memory: a temporary for one value is fine, a copy of a row or of the grid isn't. Every cell moves, so O(n²) time is the floor.

::: Starter code and tests
In an Xcode test target:

```swift
import Testing

struct RotateImageTests {

    @Test(arguments: [
        ([[1, 2, 3], [4, 5, 6], [7, 8, 9]], [[7, 4, 1], [8, 5, 2], [9, 6, 3]]),
        ([[1, 2], [3, 4]], [[3, 1], [4, 2]]),
        ([[42]], [[42]]),
    ])
    func turnsTheSquareGridAQuarterClockwise(input: [[Int]], expected: [[Int]]) {
        var matrix = input
        rotate(&matrix)
        #expect(matrix == expected)
    }

    // MARK: - Privates
    private func rotate(_ matrix: inout [[Int]]) {
    }
}
```

In a playground:

```swift
func rotate(_ matrix: inout [[Int]]) {
    // your solution
}

let cases: [([[Int]], [[Int]])] = [
    ([[1, 2, 3], [4, 5, 6], [7, 8, 9]], [[7, 4, 1], [8, 5, 2], [9, 6, 3]]),
    ([[1, 2], [3, 4]], [[3, 1], [4, 2]]),
    ([[42]], [[42]]),
]
for (input, expected) in cases {
    var matrix = input
    rotate(&matrix)
    print(matrix == expected ? "PASS" : "FAIL", input, "→", matrix, "expected", expected)
}
```

The 1 × 1 case already passes with the empty placeholder, so this starter shows two failures, not three.
:::

::: Pattern and cue
**Transpose, then reverse each row.** The cue is *"rotate by 90 degrees"* plus *"in place"*. A quarter turn is the composition of two moves that are each easy to do in place: mirror across the main diagonal (the cell at row r, column c trades with the one at row c, column r), then mirror left-right.
:::

::: Approach
Where does a cell go when the picture turns clockwise? The cell at row r, column c ends up at row c, counted from the top, and column n − 1 − r. Swapping row and column is exactly what a transpose does: it flips the grid across the line from the top-left to the bottom-right corner. Swapping each cell with its mirror on the other side of that line, visiting only the cells above the line, gives the transpose without touching anything twice. That leaves every value in the right row but with its column reversed, so reverse each row.

Time O(n²): the transpose touches each pair once and the reversals touch each cell once. Space O(1): one temporary value.
:::

::: Swift solution
```swift
func rotate(_ matrix: inout [[Int]]) {
    let size = matrix.count
    // 1. Transpose: swap each cell above the diagonal with its mirror below it.
    for row in 0..<size {
        for column in (row + 1)..<size {
            let saved = matrix[row][column]
            matrix[row][column] = matrix[column][row]
            matrix[column][row] = saved
        }
    }
    // 2. Reverse every row.
    for row in 0..<size {
        matrix[row].reverse()
    }
}
```

The inner loop starts at `row + 1`. Starting it at 0 swaps every pair twice, which undoes the transpose and leaves the grid merely mirrored. On the last row the range is `size..<size`, empty, which is fine — a half-open range may be empty; it just can't run backwards.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, four more (an empty grid, a 4 × 4 grid, all values equal, negatives on the diagonals), and 3,000 random square grids up to 9 × 9 checked against a brute force that builds a new grid with `result[c][n - 1 - r] = matrix[r][c]` — plus a check that four rotations give back the original.
:::

::: Walk it through
**`[[1, 2, 3], [4, 5, 6], [7, 8, 9]]`**

| Step | Grid |
|---|---|
| start | `[[1, 2, 3], [4, 5, 6], [7, 8, 9]]` |
| swap (0, 1) with (1, 0) | `[[1, 4, 3], [2, 5, 6], [7, 8, 9]]` |
| swap (0, 2) with (2, 0) | `[[1, 4, 7], [2, 5, 6], [3, 8, 9]]` |
| swap (1, 2) with (2, 1) | `[[1, 4, 7], [2, 5, 8], [3, 6, 9]]` — transposed |
| reverse each row | `[[7, 4, 1], [8, 5, 2], [9, 6, 3]]` |

The diagonal cells 1, 5 and 9 never move in the transpose; the reversal moves the 1 and 9 but keeps the 5, the centre of the picture.

**`[[42]]`** — the transpose loop runs for row 0 with the empty range `1..<1`, and reversing a one-element row changes nothing. The answer is the input.
:::

::: The Swift trap
**`swap(&matrix[row][column], &matrix[column][row])` does not compile.** It is the line everyone types, and Swift rejects it: *"overlapping accesses to 'matrix', but modification requires exclusive access"*. Both arguments are writes into the same variable, `matrix`, at the same time, which Swift's exclusive-access rule forbids even though the two cells are different. Swap through a local, as above. `swapAt(_:_:)` is the library's answer only when both cells sit in the same array — `matrix[row].swapAt(i, j)` is fine, which is why the reversal step could also be written as a two-pointer swap loop on each row.
:::

::: What they ask next
- **"Anticlockwise?"** → Transpose, then reverse the order of the rows (`matrix.reverse()`) instead of each row. Or reverse each row first, then transpose.
- **"Without the transpose trick?"** → Rotate ring by ring: for each position along a ring's top side, move four values in a cycle — left into top, bottom into left, right into bottom, the saved top into right. Same O(n²), one temporary.
- **"What if the grid isn't square?"** → It can't be done in place in a `[[Int]]`: the result has n rows of m. Build a new grid with `result[c][rows - 1 - r] = matrix[r][c]`.
:::
