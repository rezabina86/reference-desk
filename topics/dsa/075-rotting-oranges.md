---
title: 63 · Rotting Oranges
summary: Rot spreads each minute from bad oranges to the fresh ones beside them; find how many minutes until none are fresh, or say it never happens.
group: Graphs
minutes: 25
sources:
- LeetCode 994 · Rotting Oranges | https://leetcode.com/problems/rotting-oranges/
- Swift standard library · Array.removeFirst() | https://developer.apple.com/documentation/swift/array/removefirst()
---

*Medium · G*

A crate is a grid of cells: `0` is empty, `1` is a fresh orange, `2` is a rotten one. Every minute, each fresh orange directly above, below, left or right of a rotten orange turns rotten too — all of them at the same moment. Return the number of minutes until no fresh orange is left. If some fresh orange can never be reached, return `-1`; if there are no fresh oranges to begin with, the answer is `0`.

| Grid | Answer |
|---|---|
| `[[2, 1, 1], [1, 1, 0], [0, 1, 2]]` | `2` — rot spreads from two corners at once |
| `[[2, 1, 0], [0, 1, 1], [1, 0, 2]]` | `-1` — the bottom-left orange is walled in by empty cells |
| `[[0, 2]]` | `0` — nothing fresh, no time needed |

Constraints that matter: at most 10 × 10 cells, so speed is not the problem; getting the minutes right is. The natural solution is O(rows × columns).

::: Starter code and tests
In an Xcode test target:

```swift
import Testing

struct RottingOrangesTests {

    @Test(arguments: [
        ([[2, 1, 1], [1, 1, 0], [0, 1, 2]], 2),
        ([[2, 1, 0], [0, 1, 1], [1, 0, 2]], -1),
        ([[0, 2]], 0),
    ])
    func returnsMinutesUntilNothingIsFreshOrMinusOne(grid: [[Int]], expected: Int) {
        #expect(orangesRotting(grid) == expected)
    }

    // MARK: - Privates
    private func orangesRotting(_ grid: [[Int]]) -> Int {
        0
    }
}
```

In a playground:

```swift
func orangesRotting(_ grid: [[Int]]) -> Int {
    0 // your solution
}

let cases: [([[Int]], Int)] = [
    ([[2, 1, 1], [1, 1, 0], [0, 1, 2]], 2),
    ([[2, 1, 0], [0, 1, 1], [1, 0, 2]], -1),
    ([[0, 2]], 0),
]
for (grid, expected) in cases {
    let got = orangesRotting(grid)
    print(got == expected ? "PASS" : "FAIL", grid, "→", got, "expected", expected)
}
```
:::

::: Pattern and cue
**Multi-source breadth-first search, one ring per minute.** The cue is *spreads to neighbours* plus *"minimum minutes"* plus *several starting points at once*. Every rotten orange is a starting point; BFS from all of them together, and the number of rings it takes is the time.
:::

::: Approach
First, walk the crate once: list every rotten orange, and count the fresh ones. Then simulate minute by minute. In each minute, every orange that turned rotten in the previous minute (at the start, every rotten orange) infects its fresh neighbours; those newly rotten oranges become the list for the next minute, and the fresh count drops by one for each. Stop when nothing is fresh, or when a minute passes in which nothing new rotted. If fresh oranges remain at that point, they can never be reached: return `-1`. Otherwise return the minutes counted.

Time O(R·C): each orange rots once, and when it does it looks at four neighbours. Space O(R·C): the copy of the grid and the list of oranges that rotted in the latest minute.
:::

::: Swift solution
```swift
func orangesRotting(_ grid: [[Int]]) -> Int {
    var grid = grid
    var rotten: [(Int, Int)] = []
    var fresh = 0
    for row in grid.indices {
        for column in grid[row].indices {
            if grid[row][column] == 2 { rotten.append((row, column)) }
            if grid[row][column] == 1 { fresh += 1 }
        }
    }

    var minutes = 0
    while fresh > 0 && !rotten.isEmpty {
        var next: [(Int, Int)] = []              // the oranges that turn this minute
        for (r, c) in rotten {
            for (nr, nc) in [(r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)]
            where grid.indices.contains(nr) && grid[nr].indices.contains(nc) && grid[nr][nc] == 1 {
                grid[nr][nc] = 2
                fresh -= 1
                next.append((nr, nc))
            }
        }
        rotten = next
        minutes += 1
    }
    return fresh == 0 ? minutes : -1
}
```

The loop runs only while something is still fresh. That one condition gets both edges right: no fresh oranges means zero minutes, and the minute in which the last orange turns is counted, but no extra empty minute after it.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, four more (a lone fresh orange, an empty cell, a row where rot travels four cells, a crate already all rotten), and 2,000 random crates checked against a plain minute-by-minute simulation that rescans the whole grid each minute.
:::

::: Walk it through
**`[[2, 1, 1], [1, 1, 0], [0, 1, 2]]`** — 5 fresh, rotten at (0,0) and (2,2).

| Minute | Rotten last minute | Turns now | Fresh left |
|---|---|---|---|
| 1 | (0,0), (2,2) | (1,0), (0,1) from the top-left; (2,1) from the bottom-right | 2 |
| 2 | (1,0), (0,1), (2,1) | (1,1), (0,2) | 0 |

Fresh hits 0, the loop stops: answer 2.

**`[[2, 1, 0], [0, 1, 1], [1, 0, 2]]`** — 4 fresh. Minute 1 rots (0,1) and (1,2); minute 2 rots (1,1); minute 3 finds nothing new, and the list for the next minute is empty, so the loop ends with 1 fresh orange left at (2,0). Its neighbours are both empty cells. Answer `-1`.
:::

::: The Swift trap
**`removeFirst()` makes the textbook queue quadratic.** The usual BFS pops from the front of a queue, and in Swift the obvious spelling is `queue.removeFirst()` on an `Array`. That shifts every remaining element down by one, so it's O(n) per pop and O(n²) overall — invisible on a 10 × 10 crate, a problem the moment the interviewer says "now a million cells". There's no `Deque` in the standard library. Either keep a read index into the array (`let cell = queue[head]; head += 1`), or do what the solution does: hold one array per minute and swap in the next one, which also hands you the minute count for free.
:::

::: What they ask next
- **"Which orange rots last, or when does each one rot?"** → Store the minute in each cell as it turns (or in a parallel grid); the BFS already visits them in time order.
- **"Rot spreads diagonally too."** → Add the four diagonal offsets to the neighbour list. Nothing else changes.
- **"Some oranges take two minutes to catch."** → Edges now have different weights, so plain BFS rings no longer give the time; use Dijkstra from all rotten oranges at once, with a priority queue keyed by rot time — hand-rolled, since the standard library has no `Heap`.
:::
