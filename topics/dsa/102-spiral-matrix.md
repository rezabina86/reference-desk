---
title: 85 · Spiral Matrix
summary: Read every value of a rectangular grid in the order you meet them walking clockwise around its edge and then inward, ring by ring.
group: Matrix
minutes: 25
sources:
- LeetCode 54 · Spiral Matrix | https://leetcode.com/problems/spiral-matrix/
- Swift standard library · stride(from:through:by:) | https://developer.apple.com/documentation/swift/stride(from:through:by:)
---

*Medium · G*

You get a grid of integers with m rows and n columns — not necessarily square. Start at the top-left corner and walk clockwise: right along the top row, down the right edge, left along the bottom row, up the left edge. When you get back near the start, step inside and walk the next ring the same way, until every cell has been visited once. Return the values in the order you visited them.

| Grid | Answer |
|---|---|
| `[[1, 2, 3], [4, 5, 6], [7, 8, 9]]` | `[1, 2, 3, 6, 9, 8, 7, 4, 5]` |
| `[[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]]` | `[1, 2, 3, 4, 8, 12, 11, 10, 9, 5, 6, 7]` — the last ring is one row |
| `[[1], [2], [3]]` | `[1, 2, 3]` — a single column |

Constraints that matter: between 1 and 10 rows and columns, values from −100 to 100. The grid is small; the difficulty is entirely in not visiting a cell twice on the last ring. O(m × n) time is the target, and the output array aside, O(1) space.

::: Starter code and tests
In an Xcode test target:

```swift
import Testing

struct SpiralMatrixTests {

    @Test(arguments: [
        ([[1, 2, 3], [4, 5, 6], [7, 8, 9]], [1, 2, 3, 6, 9, 8, 7, 4, 5]),
        ([[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]], [1, 2, 3, 4, 8, 12, 11, 10, 9, 5, 6, 7]),
        ([[1], [2], [3]], [1, 2, 3]),
    ])
    func readsTheGridClockwiseFromTheOutsideIn(matrix: [[Int]], expected: [Int]) {
        #expect(spiralOrder(matrix) == expected)
    }

    // MARK: - Privates
    private func spiralOrder(_ matrix: [[Int]]) -> [Int] {
        []
    }
}
```

In a playground:

```swift
func spiralOrder(_ matrix: [[Int]]) -> [Int] {
    [] // your solution
}

let cases: [([[Int]], [Int])] = [
    ([[1, 2, 3], [4, 5, 6], [7, 8, 9]], [1, 2, 3, 6, 9, 8, 7, 4, 5]),
    ([[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]], [1, 2, 3, 4, 8, 12, 11, 10, 9, 5, 6, 7]),
    ([[1], [2], [3]], [1, 2, 3]),
]
for (matrix, expected) in cases {
    let got = spiralOrder(matrix)
    print(got == expected ? "PASS" : "FAIL", matrix, "→", got, "expected", expected)
}
```
:::

::: Pattern and cue
**Four shrinking boundaries.** The cue is *"clockwise"* / *"spiral"* — reading the grid ring by ring. Keep the top row, bottom row, left column and right column that are still unread; each side you walk moves one of them inward by one.
:::

::: Approach
Hold four numbers: the first unread row from the top, the last unread row at the bottom, and the same for columns on the left and right. Read the top row from left to right, then push the top boundary down. Read the right column from top to bottom, then pull the right boundary in. Now check that a bottom row is still unread — on a thin grid it may already be gone — and if so read it from right to left and lift the bottom boundary. Likewise check that a left column remains before reading it upwards and moving the left boundary right. Repeat while the boundaries haven't crossed.

Time O(m × n): every cell is appended exactly once. Space O(1) beyond the answer: four integers.
:::

::: Swift solution
```swift
func spiralOrder(_ matrix: [[Int]]) -> [Int] {
    guard let columnCount = matrix.first?.count, columnCount > 0 else { return [] }
    var top = 0
    var bottom = matrix.count - 1
    var left = 0
    var right = columnCount - 1
    var result: [Int] = []
    result.reserveCapacity(matrix.count * columnCount)

    while top <= bottom && left <= right {
        for column in stride(from: left, through: right, by: 1) {     // top row, left to right
            result.append(matrix[top][column])
        }
        top += 1
        for row in stride(from: top, through: bottom, by: 1) {        // right column, downwards
            result.append(matrix[row][right])
        }
        right -= 1
        if top <= bottom {                                            // a bottom row is still unread
            for column in stride(from: right, through: left, by: -1) {
                result.append(matrix[bottom][column])
            }
            bottom -= 1
        }
        if left <= right {                                            // a left column is still unread
            for row in stride(from: bottom, through: top, by: -1) {
                result.append(matrix[row][left])
            }
            left += 1
        }
    }
    return result
}
```

The two `if`s are the whole problem. After the top row and right column are read, a one-row ring has no separate bottom row, and a one-column ring has no separate left column; without the checks, those cells are read a second time on the way back.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, six more (an empty grid, one empty row, `[[7]]`, a single row, a 4 × 2 grid, a 2 × 3 grid), and 3,000 random grids up to 8 × 8 checked against a brute force that walks with a direction and a visited grid, turning right whenever the next cell is off the edge or already seen.
:::

::: Walk it through
**`[[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]]`** — top 0, bottom 2, left 0, right 3

| Side | Reads | Boundaries after (top, bottom, left, right) |
|---|---|---|
| top row 0, columns 0→3 | 1, 2, 3, 4 | 1, 2, 0, 3 |
| right column 3, rows 1→2 | 8, 12 | 1, 2, 0, 2 |
| bottom row 2, columns 2→0 | 11, 10, 9 | 1, 1, 0, 2 |
| left column 0, rows 1→1 | 5 | 1, 1, 1, 2 |
| top row 1, columns 1→2 | 6, 7 | 2, 1, 1, 2 |
| right column 2, rows 2→1 | nothing — the range is empty | 2, 1, 1, 1 |
| bottom row | skipped: top 2 > bottom 1 | |
| left column 1, rows 1→2 going up | nothing — the range is empty | 2, 1, 2, 1 |

The boundaries have crossed: `[1, 2, 3, 4, 8, 12, 11, 10, 9, 5, 6, 7]`.

**`[[1], [2], [3]]`** — the top row reads 1, the right column reads 2 and 3, and `right` drops to −1. The bottom-row check passes (top 1 ≤ bottom 2) but its range from −1 down to 0 is empty; `bottom` becomes 1. The left-column check fails (left 0 > right −1). Without it, the walk would read row 1 of column 0 — the 2 — a second time.
:::

::: The Swift trap
**Swift has no countdown `for` loop, and the ranges that look like one crash.** `for column in right...left` traps immediately — a closed range must not run backwards. `for column in (left...right).reversed()` reads correctly until the boundaries cross, and then traps on `left...right` itself: on `[[1], [2], [3]]`, the bottom-row loop is reached with left 0 and right −1, and `0...(-1)` is a fatal "Range requires lowerBound <= upperBound". The same happens on the right column, `top...bottom`, for a single-row grid. `stride(from:through:by:)` with a step of −1 is Swift's countdown, and when the start is already past the end it simply produces nothing.
:::

::: What they ask next
- **"Generate the spiral instead: fill an n × n grid with 1 to n²."** → The same four boundaries and the same four sides, writing a counter instead of reading.
- **"Do it with a direction instead of boundaries."** → Keep a direction index into right, down, left, up and a visited grid (or overwrite visited cells with a sentinel); turn whenever the next cell is off the grid or seen. O(m × n) extra space unless you may overwrite the input.
- **"Anticlockwise, or from the centre outwards?"** → Anticlockwise walks the sides in the other order: down the left column first, then the bottom row, up the right column, back along the top. From the centre outwards: reverse the clockwise answer — you get the outward walk, turning anticlockwise, ending at the top-left corner.
:::
