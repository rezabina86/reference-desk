---
title: Graphs — the idea
summary: How to see a grid, a web of references or a list of dependencies as nodes and edges, and the three walks that answer almost every question about them.
group: Graphs
minutes: 10
sources:
- Wikipedia · Breadth-first search | https://en.wikipedia.org/wiki/Breadth-first_search
- Wikipedia · Topological sorting (Kahn's algorithm) | https://en.wikipedia.org/wiki/Topological_sorting#Kahn's_algorithm
- Swift standard library · Array.popLast() | https://developer.apple.com/documentation/swift/array/poplast()
- swift-collections · Deque | https://swiftpackageindex.com/apple/swift-collections/documentation/dequemodule/deque
---

A graph is things (**nodes**) and connections between them (**edges**). Most interview graphs don't announce themselves: they arrive as a grid of characters, a list of pairs, or objects pointing at other objects. The first step is always the same — name the nodes, name the edges — and then one of three walks does the work.

## When to reach for it

- A **grid** where cells touch their neighbours: *"islands"*, *"regions"*, *"flood"*, *"spreads to adjacent cells"*.
- *"Connected"*, *"reachable"*, *"can water / fire / a signal get from here to there"*.
- *"Minimum number of steps / minutes / moves"* in an unweighted world — that's breadth-first search.
- Objects that **reference each other**, possibly in a cycle: *"copy"*, *"clone"*, *"neighbours"*.
- **Dependencies**: *"must come before"*, *"prerequisite"*, *"build order"*, *"is there a cycle"* — that's a topological sort.

## The idea in plain words

Think of a city's metro map. Stations are nodes, the lines between them are edges. Two questions cover most of what you'd ask: *can I get from here to there?* and *what is the fewest number of stops?*

To answer the first, you walk: from your station, visit a neighbour, then one of its neighbours, and so on, crossing off each station as you visit it so you never go round in circles. That crossing off is the **visited set**, and forgetting it is the classic way to loop forever.

To answer the second, you spread out in rings, like a stone dropped in a pond: first every station one stop away, then every station two stops away. The first time a ring touches your destination, the ring number is the fewest stops. That ring-by-ring walk is **breadth-first search (BFS)**; the go-deep-first walk is **depth-first search (DFS)**.

The third walk is for dependencies. Picture building a house: walls need a foundation, the roof needs walls. You repeatedly do whatever has nothing left to wait for, and each finished job may free up others. If at some point jobs remain but every one of them is waiting on another, they're waiting on each other in a circle — a **cycle**, and nothing can finish. That's **Kahn's algorithm** for topological sort.

## The template in Swift

```swift
// Edges arrive as pairs; turn them into an adjacency list: neighbours[node] = [nodes it connects to].
func makeAdjacency(nodeCount: Int, edges: [[Int]], directed: Bool) -> [[Int]] {
    var neighbours = Array(repeating: [Int](), count: nodeCount)
    for edge in edges {
        neighbours[edge[0]].append(edge[1])
        if !directed { neighbours[edge[1]].append(edge[0]) }
    }
    return neighbours
}

// BFS: distance in steps from `start` to every node (-1 = unreachable).
// The queue is an array plus a read index: removeFirst() would make it O(n²).
func distances(from start: Int, in neighbours: [[Int]]) -> [Int] {
    var distance = Array(repeating: -1, count: neighbours.count)
    distance[start] = 0
    var queue = [start]
    var head = 0
    while head < queue.count {
        let node = queue[head]; head += 1
        for next in neighbours[node] where distance[next] == -1 {   // -1 doubles as "not visited"
            distance[next] = distance[node] + 1
            queue.append(next)
        }
    }
    return distance
}

// DFS with an explicit stack: everything reachable from `start`. No recursion, so no stack overflow.
func reachable(from start: Int, in neighbours: [[Int]]) -> Set<Int> {
    var visited: Set<Int> = [start]
    var stack = [start]
    while let node = stack.popLast() {
        for next in neighbours[node] where visited.insert(next).inserted {
            stack.append(next)
        }
    }
    return visited
}

// A grid is a graph: each cell is a node, its four neighbours are its edges.
func gridNeighbours(row: Int, column: Int, rows: Int, columns: Int) -> [(Int, Int)] {
    [(row - 1, column), (row + 1, column), (row, column - 1), (row, column + 1)]
        .filter { $0.0 >= 0 && $0.0 < rows && $0.1 >= 0 && $0.1 < columns }
}

// Kahn's algorithm: an order in which every node comes after the nodes it depends on,
// or nil if there is a cycle. `edges` are [before, after] pairs.
func topologicalOrder(nodeCount: Int, edges: [[Int]]) -> [Int]? {
    var after = Array(repeating: [Int](), count: nodeCount)
    var waitingOn = Array(repeating: 0, count: nodeCount)
    for edge in edges {
        after[edge[0]].append(edge[1])
        waitingOn[edge[1]] += 1
    }
    var order = (0..<nodeCount).filter { waitingOn[$0] == 0 }   // nothing to wait for
    var head = 0
    while head < order.count {
        let node = order[head]; head += 1
        for next in after[node] {
            waitingOn[next] -= 1
            if waitingOn[next] == 0 { order.append(next) }       // its last blocker just finished
        }
    }
    return order.count == nodeCount ? order : nil                // leftovers sit on a cycle
}
```

## Variations

- **Count the pieces.** Scan every node; each time you meet one not yet visited, that's a new component — walk it entirely, marking it, and add one. Number of Islands.
- **Spread from many places at once (multi-source BFS).** Put every starting node in the queue before the first step, then go ring by ring; the number of rings is the time. Rotting Oranges.
- **Walk backwards from the goal.** When the question is "which cells can reach the edge", start at the edge and walk the reversed rule — one walk instead of one per cell. Pacific Atlantic Water Flow.
- **Copy while walking.** Keep a map from each original node to its copy; it is both the visited set and the way to wire the copied edges. Clone Graph.
- **Order by dependencies.** Kahn's algorithm, or DFS with three states (not seen, in progress, done) where meeting an in-progress node means a cycle. Course Schedule.

## Complexity

Every walk visits each node once and looks along each edge once (twice for an undirected edge, once from each end): **O(V + E) time**, where V is the number of nodes and E the number of edges. For a grid of R rows and C columns, V = R·C and E is about 4·R·C, so **O(R·C)**. Space is **O(V)** for the visited set and the queue or stack; the adjacency list itself is O(V + E).

## Swift traps

- **No `Deque` in the standard library.** `Array.removeFirst()` shifts every element, so a BFS that uses it is O(n²). Use an array with a `head` index (shown above), or two arrays swapped per ring. `Deque` exists in swift-collections, but you won't have it in a shared editor.
- **Recursion depth.** A recursive DFS on a 300×300 grid of land goes 90,000 calls deep. Swift has no tail-call guarantee, and threads other than the main one get small stacks: on Swift 6.4 a recursive flood fill of a 300×300 all-land grid crashed inside a test. Say it out loud, then use an explicit stack.
- **A tuple isn't `Hashable`.** `Set<(Int, Int)>` doesn't compile. For a grid, use a `[[Bool]]` the size of the grid (faster anyway), or encode a cell as `row * columns + column`.
- **Classes aren't `Hashable` by default.** To keep a visited set of objects, key by `ObjectIdentifier(node)`; it compares identity, which is exactly what "have I seen this node" means.
- **Arrays are values.** A helper that takes `visited: [Bool]` as a plain parameter mutates a copy, and the caller never sees the marks. Pass it `inout`, or write the helper as a nested function that captures the `var`.

## The problems in this topic

- [61 · Number of Islands](#/dsa/number-of-islands) — Medium
- [62 · Clone Graph](#/dsa/clone-graph) — Medium
- [63 · Rotting Oranges](#/dsa/rotting-oranges) — Medium
- [64 · Pacific Atlantic Water Flow](#/dsa/pacific-atlantic-water-flow) — Medium
- [65 · Course Schedule](#/dsa/course-schedule) — Medium
