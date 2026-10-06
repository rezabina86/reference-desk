---
title: 64 · Pacific Atlantic Water Flow
summary: On a height map bordered by two oceans, find every cell from which rain could run downhill into both of them.
group: Graphs
minutes: 25
sources:
- LeetCode 417 · Pacific Atlantic Water Flow | https://leetcode.com/problems/pacific-atlantic-water-flow/
- Swift standard library · Hashable | https://developer.apple.com/documentation/swift/hashable
---

*Medium · G*

You get a rectangular island as a grid of heights. The Pacific washes the top and left edges; the Atlantic washes the bottom and right edges. Rain on a cell can run to a side-by-side neighbour whose height is **the same or lower**, and from there onwards; a cell on an edge drains straight into the ocean on that edge. Return the coordinates `[row, column]` of every cell whose water can reach **both** oceans, in any order.

| Heights | Answer |
|---|---|
| `[[1, 2], [2, 1]]` | `[[0, 1], [1, 0]]` — each 2 sits on both a Pacific edge and an Atlantic edge |
| `[[1, 2, 3], [8, 9, 4], [7, 6, 5]]` | every cell except `[0, 0]` and `[0, 1]` |
| `[[5]]` | `[[0, 0]]` — a single cell touches all four edges |

Constraints that matter: up to 200 × 200 cells, heights from 0 to 100,000. Running a separate search from every cell is O((R·C)²) — 1.6 billion steps at the limit. The target is O(R·C).

::: Starter code and tests
In an Xcode test target:

```swift
import Testing

struct PacificAtlanticWaterFlowTests {

    @Test(arguments: [
        ([[1, 2], [2, 1]], [[0, 1], [1, 0]]),
        ([[1, 2, 3], [8, 9, 4], [7, 6, 5]], [[0, 2], [1, 0], [1, 1], [1, 2], [2, 0], [2, 1], [2, 2]]),
        ([[5]], [[0, 0]]),
    ])
    func findsCellsThatDrainIntoBothOceans(heights: [[Int]], expected: [[Int]]) {
        let cells = pacificAtlantic(heights).sorted { $0.lexicographicallyPrecedes($1) }
        #expect(cells == expected)
    }

    // MARK: - Privates
    private func pacificAtlantic(_ heights: [[Int]]) -> [[Int]] {
        []
    }
}
```

In a playground:

```swift
func pacificAtlantic(_ heights: [[Int]]) -> [[Int]] {
    [] // your solution
}

let cases: [([[Int]], [[Int]])] = [
    ([[1, 2], [2, 1]], [[0, 1], [1, 0]]),
    ([[1, 2, 3], [8, 9, 4], [7, 6, 5]], [[0, 2], [1, 0], [1, 1], [1, 2], [2, 0], [2, 1], [2, 2]]),
    ([[5]], [[0, 0]]),
]
for (heights, expected) in cases {
    let got = pacificAtlantic(heights).sorted { $0.lexicographicallyPrecedes($1) }
    print(got == expected ? "PASS" : "FAIL", heights, "→", got, "expected", expected)
}
```

Any order is accepted, so the result is sorted (row first, then column) before it's compared.
:::

::: Pattern and cue
**Graph traversal run backwards from the targets.** The cue is *"every cell that can reach"* a fixed set of places — here, the two coastlines. Instead of asking each cell where its water goes, start at the coast and climb: walk to neighbours that are **the same or higher**. Every cell the climb reaches can drain to that coast. Do it once per ocean and keep the cells both climbs reached.
:::

::: Approach
Water runs downhill, so reverse the question: from the ocean, which cells could water have come from? Start a walk from every cell on the Pacific's two edges. From any cell you're standing on, you may step to a neighbour that is at least as high, because water on that neighbour could flow down to you. Mark everything you reach. Do the same for the Atlantic from its two edges, with a separate set of marks. The cells marked twice are the answer.

Time O(R·C): each of the two walks marks each cell at most once and checks four neighbours per cell. Space O(R·C): two grids of marks, plus the walk's stack.
:::

::: Swift solution
```swift
func pacificAtlantic(_ heights: [[Int]]) -> [[Int]] {
    let rows = heights.count
    let columns = heights.first?.count ?? 0

    // Walk uphill from the given border cells; every cell reached can drain to that ocean.
    func reachable(from starts: [(Int, Int)]) -> [[Bool]] {
        var seen = Array(repeating: Array(repeating: false, count: columns), count: rows)
        var stack = starts
        for (r, c) in starts { seen[r][c] = true }
        while let (r, c) = stack.popLast() {
            for (nr, nc) in [(r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)]
            where nr >= 0 && nr < rows && nc >= 0 && nc < columns
                && !seen[nr][nc] && heights[nr][nc] >= heights[r][c] {
                seen[nr][nc] = true
                stack.append((nr, nc))
            }
        }
        return seen
    }

    let pacific = reachable(from: (0..<rows).map { ($0, 0) } + (0..<columns).map { (0, $0) })
    let atlantic = reachable(from: (0..<rows).map { ($0, columns - 1) } + (0..<columns).map { (rows - 1, $0) })

    var result: [[Int]] = []
    for r in 0..<rows {
        for c in 0..<columns where pacific[r][c] && atlantic[r][c] {
            result.append([r, c])
        }
    }
    return result
}
```

The one comparison that matters is `heights[nr][nc] >= heights[r][c]`: the neighbour must be at least as high as where you stand, because you are retracing water's path in reverse. Write `>` and flat plateaus stop the climb.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, two more (a flat 2 × 2 plateau, where every cell qualifies, and a single row), and 1,500 random height maps checked against a brute force that runs a downhill search from every cell.
:::

::: Walk it through
**`[[1, 2, 3], [8, 9, 4], [7, 6, 5]]`** — the heights spiral up from the top-left corner to the 9 in the middle.

| Climb | Starts on | Climbs to | Cells reached |
|---|---|---|---|
| Pacific (top, left) | 1, 2, 3 along the top; 1, 8, 7 down the left | 3 → 4 → 5 → 6 → 9, and 8 → 9 | all 9 cells |
| Atlantic (bottom, right) | 3, 4, 5 down the right; 7, 6, 5 along the bottom | 4 → 9, 7 → 8 → 9 | every cell except 1 and 2 |

The 1 and the 2 in the top row are only reachable by climbing *down*, so the Atlantic climb never marks them: water on them can only run into the Pacific. Answer: the other seven cells.

**`[[5]]`** — the single cell is a starting point of both climbs, so it is marked twice straight away. Answer `[[0, 0]]`.
:::

::: The Swift trap
**`Set<(Int, Int)>` doesn't compile.** Tuples aren't `Hashable` in Swift, so the visited set most languages reach for — a set of coordinate pairs — is a compile error. Three ways out: a `[[Bool]]` grid the size of the map (used here, and faster than hashing), a set of encoded integers `row * columns + column`, or a tiny `struct Cell: Hashable { let row: Int; let column: Int }`. Note the result type too: the expected output is `[[Int]]`, not an array of tuples, partly for the same reason — `[[Int]]` is `Equatable` and `Hashable`, a tuple array isn't.
:::

::: What they ask next
- **"Why not search from each cell?"** → One search per cell, each up to O(R·C), is O((R·C)²). Starting from the coast reuses all the work: two searches total.
- **"BFS or DFS?"** → Either; we only need *which* cells are reached, not in how many steps. The explicit stack is DFS and avoids recursion depth on a 200 × 200 map.
- **"Three oceans, or the answer is cells reaching at least one."** → One climb per ocean, then combine the marks with AND for "all", OR for "any".
:::
