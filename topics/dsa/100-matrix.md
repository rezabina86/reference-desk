---
title: Matrix — the idea
summary: Treat a grid of numbers as rows of rows, walk it by row and column, and change it in place without a second copy.
group: Matrix
minutes: 8
sources:
- Swift standard library · stride(from:through:by:) | https://developer.apple.com/documentation/swift/stride(from:through:by:)
- The Swift Programming Language · Memory Safety (exclusive access) | https://docs.swift.org/swift-book/documentation/the-swift-programming-language/memorysafety/
---

A matrix question hands you a grid — a spreadsheet of numbers — and asks you to read it in an unusual order or to change it without making a copy. None of these problems needs a clever data structure. They need careful bookkeeping: which row, which column, where the edges are, and what you are allowed to overwrite.

## When to reach for it

- *"m × n matrix"*, *"grid"*, *"image"*, *"board"*
- *"in place"*, *"without allocating another matrix"*, *"O(1) extra space"*
- *"clockwise"*, *"spiral"*, *"layer by layer"*, *"outer ring"*
- *"rotate by 90 degrees"*, *"flip"*, *"mirror"*, *"transpose"*
- *"the whole row and column"* of some cell

## The idea in plain words

Picture a cinema seating plan. Every seat has a row number, counted from the front, and a seat number within the row, counted from the left. In code that is `matrix[row][column]`: the first index picks a row, going **down**; the second picks a position in it, going **right**. Row 0 is the top, column 0 is the left edge.

Three tricks cover the problems in this topic:

- **Four boundaries.** To walk the outer ring of seats, keep four numbers — the top row, the bottom row, the left column and the right column still unvisited. Walk one side, then move that boundary one step inward. When the boundaries cross, you are done.
- **Transpose, then reverse.** Turning a square picture a quarter clockwise sounds like geometry. It is two simple moves: swap the picture across its top-left-to-bottom-right diagonal (rows become columns), then reverse each row.
- **Use the grid as its own notepad.** When you must remember "this row needs clearing" but may not use extra memory, write the note into the grid itself — in the first row and first column — after saving what was there.

## The template in Swift

```swift
/// Rows first, then columns. Never touch grid[0] before checking the grid has a row.
func dimensions(of grid: [[Int]]) -> (rows: Int, columns: Int) {
    (grid.count, grid.first?.count ?? 0)
}

/// 1. Visit every cell: the row loop outside, the column loop inside.
func sumOfCells(_ grid: [[Int]]) -> Int {
    var total = 0
    for row in grid.indices {
        for column in grid[row].indices {
            total += grid[row][column]
        }
    }
    return total
}

/// 2. The neighbours that exist: up, down, left, right, minus the ones off the edge.
func neighbours(row: Int, column: Int, rows: Int, columns: Int) -> [(row: Int, column: Int)] {
    let candidates = [(row - 1, column), (row + 1, column), (row, column - 1), (row, column + 1)]
    return candidates
        .filter { $0.0 >= 0 && $0.0 < rows && $0.1 >= 0 && $0.1 < columns }
        .map { (row: $0.0, column: $0.1) }
}

/// 3. Transpose a square grid in place: swap each cell above the diagonal with its mirror.
func transpose(_ grid: inout [[Int]]) {
    for row in grid.indices {
        for column in (row + 1)..<grid.count {
            let saved = grid[row][column]
            grid[row][column] = grid[column][row]
            grid[column][row] = saved
        }
    }
}

/// 4. Mirror left-right in place: reverse each row.
func mirror(_ grid: inout [[Int]]) {
    for row in grid.indices {
        grid[row].reverse()
    }
}

/// 5. Four boundaries that shrink inwards, one ring at a time.
func ringSizes(rows: Int, columns: Int) -> [Int] {
    var top = 0, bottom = rows - 1, left = 0, right = columns - 1
    var sizes: [Int] = []
    while top <= bottom && left <= right {
        let height = bottom - top + 1
        let width = right - left + 1
        // a ring of one row or one column has no second side to walk back along
        sizes.append(height == 1 || width == 1 ? height * width : 2 * (height + width) - 4)
        top += 1; bottom -= 1; left += 1; right -= 1
    }
    return sizes
}
```

An in-place function takes `inout [[Int]]` and the caller passes `&grid`. In a test, copy the input into a `var`, call the function, and compare the `var` with the expected grid.

## Variations

1. **Mark in place.** Decide something about every row and column first, then apply it. The extra memory is the first row and first column of the grid, plus two flags saying whether those two lines held a zero of their own to begin with.
2. **Boundary walk.** Four shrinking boundaries read the grid ring by ring. The care is in the last ring, which can be a single row or a single column.
3. **Transpose plus reverse.** Quarter turns and mirror images are compositions of a transpose and a row or column reversal: clockwise is transpose then reverse each row; anticlockwise is transpose then reverse the order of the rows.
4. **The grid as a graph.** Cells are nodes, neighbours are edges — "islands", "spreading", "shortest path in a maze". That shape belongs to the graphs topic; the `neighbours` helper above is where it starts.

## Complexity

Every useful pass touches each cell a constant number of times: O(rows × columns) time. Doing it in place costs O(1) extra space — a handful of indices and flags. Any approach that copies the grid, or records "rows to clear" in a set, is O(rows + columns) or O(rows × columns) space; say which one you're spending.

## Swift traps

- **There is no 2-D array type.** `[[Int]]` is an array of separate row arrays, so rows can have different lengths and `grid[0]` crashes on an empty grid. Guard with `grid.first?.count`.
- **Building a grid is safe in Swift.** `Array(repeating: Array(repeating: 0, count: columns), count: rows)` gives independent rows, because arrays are values. (Python's `[[0] * n] * m` famously shares one row; Swift's doesn't.)
- **A row taken out is a copy.** `var row = grid[2]` and `for var row in grid` both give you copies; writing to them changes nothing in `grid`, and the compiler doesn't warn. Write through the grid: `grid[r][c] = 0`.
- **A closed range that runs backwards crashes.** `top...bottom` traps the moment `top > bottom`, which is exactly what happens on the last ring of a boundary walk. `stride(from:through:by:)` returns nothing instead, and is the only countdown loop Swift has.
- **`swap(&grid[a][b], &grid[b][a])` doesn't compile** — two simultaneous writes to `grid` break the exclusive-access rule. Swap through a temporary, or use `grid[row].swapAt(i, j)` when both cells are in the same row.

## The problems in this topic

- [84 · Set Matrix Zeroes](#/dsa/set-matrix-zeroes) — Medium
- [85 · Spiral Matrix](#/dsa/spiral-matrix) — Medium
- [86 · Rotate Image](#/dsa/rotate-image) — Medium
