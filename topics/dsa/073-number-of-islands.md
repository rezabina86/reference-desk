---
title: 61 · Number of Islands
summary: Count the separate patches of land on a map of land and water cells, where land touches land only up, down, left and right.
group: Graphs
minutes: 25
sources:
- LeetCode 200 · Number of Islands | https://leetcode.com/problems/number-of-islands/
- Swift standard library · Array.popLast() | https://developer.apple.com/documentation/swift/array/poplast()
---

*Medium · G*

You get a map drawn as a grid of characters: `"1"` is land, `"0"` is water. Two land cells belong to the same island when they sit next to each other horizontally or vertically — touching only at a corner doesn't count. Everything outside the grid is water. Return how many islands there are.

| Grid (one string per row) | Answer |
|---|---|
| `"1100"`, `"0101"`, `"0011"` | `2` — the top-left three cells, and the bottom-right three |
| `"101"`, `"010"`, `"101"` | `5` — corners don't join, so every land cell is alone |
| `"000"` | `0` — no land at all |

Constraints that matter: up to 300 × 300 cells. Each cell should be looked at a constant number of times, so the target is O(rows × columns).

::: Starter code and tests
In an Xcode test target:

```swift
import Testing

struct NumberOfIslandsTests {

    @Test(arguments: [
        (["1100", "0101", "0011"], 2),
        (["101", "010", "101"], 5),
        (["000"], 0),
    ])
    func countsPatchesOfLandJoinedSideBySide(rows: [String], expected: Int) {
        let grid = rows.map { Array($0) }
        #expect(numIslands(grid) == expected)
    }

    // MARK: - Privates
    private func numIslands(_ grid: [[Character]]) -> Int {
        0
    }
}
```

In a playground:

```swift
func numIslands(_ grid: [[Character]]) -> Int {
    0 // your solution
}

let cases: [([String], Int)] = [
    (["1100", "0101", "0011"], 2),
    (["101", "010", "101"], 5),
    (["000"], 0),
]
for (rows, expected) in cases {
    let got = numIslands(rows.map { Array($0) })
    print(got == expected ? "PASS" : "FAIL", rows, "→", got, "expected", expected)
}
```

The rows are passed as strings and turned into `[[Character]]` inside, so the cases stay readable.
:::

::: Pattern and cue
**Graph traversal on a grid: count connected components.** The cue is a *grid* plus cells that *join their neighbours* plus *"how many separate"* groups. Each land cell is a node, each side-by-side pair of land cells is an edge, and an island is a connected component.
:::

::: Approach
Scan the map row by row. Whenever you step on a land cell you haven't dealt with yet, you've found a new island: add one to the count, then flood the whole island, turning every land cell you can reach into water so it's never counted again. The flood works like spilling paint — from a cell, spread to each of its four neighbours that is still land, and from those to theirs, until nothing new is reached. When the scan finishes, the count is the answer.

Time O(R·C): the scan visits every cell once, and each land cell is sunk once and checks its four neighbours. Space O(R·C): a copy of the grid to overwrite, plus the flood's stack, which can hold most of the grid when it is all land.
:::

::: Swift solution
```swift
func numIslands(_ grid: [[Character]]) -> Int {
    var grid = grid                              // a local copy we may overwrite
    let rows = grid.count
    let columns = grid.first?.count ?? 0
    var islands = 0

    for row in 0..<rows {
        for column in 0..<columns where grid[row][column] == "1" {
            islands += 1
            grid[row][column] = "0"              // sink it the moment it is found
            var stack = [(row, column)]
            while let (r, c) = stack.popLast() {
                for (nr, nc) in [(r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)]
                where nr >= 0 && nr < rows && nc >= 0 && nc < columns && grid[nr][nc] == "1" {
                    grid[nr][nc] = "0"
                    stack.append((nr, nc))
                }
            }
        }
    }
    return islands
}
```

A cell is sunk when it's **pushed**, not when it's popped. Sink it on pop instead and the same cell can be pushed by two neighbours before either pops it — still correct, but the stack grows with duplicates.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, four more (an empty grid, a single land cell, a ring of land around a lake, a diagonal pair), a 400 × 400 all-land grid that would overflow a recursive version, and 2,000 random grids checked against a union-find count.
:::

::: Walk it through
**`"1100"`, `"0101"`, `"0011"`**

| Scan reaches | What happens | Islands |
|---|---|---|
| (0,0) land | new island; flood sinks (0,0), (0,1), then (1,1) below it | 1 |
| (0,1), (1,1) | already water now — skipped | 1 |
| (1,3) land | new island; flood sinks (1,3), (2,3), then (2,2) beside it | 2 |
| everything else | water | 2 |

Answer 2. The flood from (0,1) reaches (1,1) because they share a side; (1,1) and (2,2) only share a corner, so the second island stays separate.

**`"101"`, `"010"`, `"101"`** — every land cell's four neighbours are water, so each flood sinks just the one cell. Five floods, answer 5.
:::

::: The Swift trap
**The recursive flood fill is shorter and it crashes.** The textbook version is a nested `func sink(_ r: Int, _ c: Int)` that calls itself on the four neighbours. On a 300 × 300 map of land — inside LeetCode's limits — that recursion goes up to 90,000 calls deep. Swift doesn't promise tail calls, and threads other than the main thread get small stacks: on Swift 6.4 the recursive version crashed the test process with a stack overflow on exactly that input, in both debug and release builds. The explicit `stack` array above lives on the heap and has no such limit. If you write the recursive one in an interview, name the risk.
:::

::: What they ask next
- **"Don't modify the input."** → Keep a separate `[[Bool]]` visited grid the same size, and check it instead of sinking cells. Same time, O(R·C) extra space.
- **"Return the size of the biggest island."** → Count cells during each flood and keep the maximum; the walk is identical.
- **"Land arrives one cell at a time; report the count after each."** → Union-find: each new land cell starts as its own island and merges with land neighbours, each merge lowering the count by one. Nearly O(1) per cell.
:::
