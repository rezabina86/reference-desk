---
title: 62 · Clone Graph
summary: Given one node of a web of objects that point at each other, build a completely separate copy of the whole web with the same shape.
group: Graphs
minutes: 25
sources:
- LeetCode 133 · Clone Graph | https://leetcode.com/problems/clone-graph/
- Swift standard library · ObjectIdentifier | https://developer.apple.com/documentation/swift/objectidentifier
---

*Medium · G*

You get one node of a connected, undirected graph. Each node is an object holding a number and a list of its neighbours, and the links run both ways: if A lists B, B lists A. Return the matching node of a **deep copy** — brand-new node objects with the same numbers, wired to each other exactly like the originals, and with no link pointing back into the original graph. An empty graph is given as `nil`, and its copy is `nil`.

The graph is written as an adjacency list: entry *i* holds the neighbours of the node numbered *i* + 1, and the node you are handed is node 1.

| Graph | Answer |
|---|---|
| `[[2, 3], [1, 3], [1, 2, 4], [3]]` — a triangle 1–2–3 with 4 hanging off 3 | a copy with the same list, sharing no node with the original |
| `[[]]` — one node, no neighbours | a single new node numbered 1 |
| `[]` — empty | `nil` |

Constraints that matter: up to 100 nodes, numbered 1 to n with no repeats; no node links to itself and no link appears twice. The graph has cycles — the triangle above is one — so a copy that follows links blindly never stops. Target O(V + E).

::: Starter code and tests
In an Xcode test target:

```swift
import Testing

struct CloneGraphTests {

    @Test(arguments: [
        [[2, 3], [1, 3], [1, 2, 4], [3]],
        [[]],
        [],
    ])
    func copiesEveryNodeAndLinkIntoFreshObjects(adjacencyList: [[Int]]) {
        let originals = makeGraph(adjacencyList)
        let copy = cloneGraph(originals.first)

        #expect(adjacency(of: copy) == adjacencyList)
        let originalIDs = Set(originals.map(ObjectIdentifier.init))
        #expect(nodes(reachableFrom: copy).allSatisfy { !originalIDs.contains(ObjectIdentifier($0)) })
        if adjacencyList.isEmpty { #expect(copy == nil) }
    }

    // MARK: - Privates
    private func cloneGraph(_ node: GraphNode?) -> GraphNode? {
        nil
    }
}

private final class GraphNode {
    var value: Int
    var neighbors: [GraphNode] = []
    init(_ value: Int) { self.value = value }
}

/// Builds nodes 1...n from an adjacency list; entry i lists the neighbours of node i + 1.
private func makeGraph(_ adjacencyList: [[Int]]) -> [GraphNode] {
    let nodes = adjacencyList.indices.map { GraphNode($0 + 1) }
    for (index, neighbors) in adjacencyList.enumerated() {
        nodes[index].neighbors = neighbors.map { nodes[$0 - 1] }
    }
    return nodes
}

/// Every node reachable from `start`, each once.
private func nodes(reachableFrom start: GraphNode?) -> [GraphNode] {
    guard let start else { return [] }
    var seen: Set<ObjectIdentifier> = [ObjectIdentifier(start)]
    var queue = [start]
    var head = 0
    while head < queue.count {
        let node = queue[head]; head += 1
        for neighbor in node.neighbors where seen.insert(ObjectIdentifier(neighbor)).inserted {
            queue.append(neighbor)
        }
    }
    return queue
}

/// The adjacency list of the graph reachable from `start`, ordered by node number.
private func adjacency(of start: GraphNode?) -> [[Int]] {
    nodes(reachableFrom: start).sorted { $0.value < $1.value }.map { $0.neighbors.map(\.value) }
}
```

In a playground:

```swift
final class GraphNode {
    var value: Int
    var neighbors: [GraphNode] = []
    init(_ value: Int) { self.value = value }
}

func makeGraph(_ adjacencyList: [[Int]]) -> [GraphNode] {
    let nodes = adjacencyList.indices.map { GraphNode($0 + 1) }
    for (index, neighbors) in adjacencyList.enumerated() {
        nodes[index].neighbors = neighbors.map { nodes[$0 - 1] }
    }
    return nodes
}

func nodes(reachableFrom start: GraphNode?) -> [GraphNode] {
    guard let start else { return [] }
    var seen: Set<ObjectIdentifier> = [ObjectIdentifier(start)]
    var queue = [start]
    var head = 0
    while head < queue.count {
        let node = queue[head]; head += 1
        for neighbor in node.neighbors where seen.insert(ObjectIdentifier(neighbor)).inserted {
            queue.append(neighbor)
        }
    }
    return queue
}

func adjacency(of start: GraphNode?) -> [[Int]] {
    nodes(reachableFrom: start).sorted { $0.value < $1.value }.map { $0.neighbors.map(\.value) }
}

func cloneGraph(_ node: GraphNode?) -> GraphNode? {
    nil // your solution
}

let cases: [[[Int]]] = [
    [[2, 3], [1, 3], [1, 2, 4], [3]],
    [[]],
    [],
]
for adjacencyList in cases {
    let originals = makeGraph(adjacencyList)
    let copy = cloneGraph(originals.first)
    let originalIDs = Set(originals.map(ObjectIdentifier.init))
    let sameShape = adjacency(of: copy) == adjacencyList
    let allFresh = nodes(reachableFrom: copy).allSatisfy { !originalIDs.contains(ObjectIdentifier($0)) }
    let nilWhenEmpty = !adjacencyList.isEmpty || copy == nil
    let pass = sameShape && allFresh && nilWhenEmpty
    print(pass ? "PASS" : "FAIL", adjacencyList, "→", adjacency(of: copy), "fresh nodes:", allFresh)
}
```

Each test builds the original graph from the list, clones node 1, then checks two things: the copy reads back as the same adjacency list, and none of its nodes is `===` to an original. Returning the original node itself fails the second check.
:::

::: Pattern and cue
**Graph traversal with an original-to-copy map.** The cue is *nodes pointing at neighbours* plus *"deep copy"* in a structure that can loop back on itself. Any walk works (BFS here); what makes it correct is a map from each original node to its copy, which is at once the visited set and the way to find a neighbour's copy when wiring links.
:::

::: Approach
Make a copy of the starting node and note in a map "this original → this copy". Then walk the original graph from the start, one node at a time. For each node you take off the queue, look at its neighbours: if a neighbour has no copy yet, make one, record it in the map, and queue the neighbour to be processed later. Either way, add the neighbour's copy to the current node's copy's neighbour list. Because a copy is made only once per original, cycles end the walk naturally — the second time you meet a node, it's already in the map.

Time O(V + E): each node is queued once and each link is followed once from each end. Space O(V): the map and the queue each hold at most one entry per node.
:::

::: Swift solution
```swift
final class GraphNode {
    var value: Int
    var neighbors: [GraphNode] = []
    init(_ value: Int) { self.value = value }
}

func cloneGraph(_ node: GraphNode?) -> GraphNode? {
    guard let node else { return nil }
    var copies: [ObjectIdentifier: GraphNode] = [ObjectIdentifier(node): GraphNode(node.value)]
    var queue = [node]
    var head = 0

    while head < queue.count {
        let original = queue[head]; head += 1
        let copy = copies[ObjectIdentifier(original)]!
        for neighbor in original.neighbors {
            let key = ObjectIdentifier(neighbor)
            if copies[key] == nil {              // first sighting: make its copy, visit it later
                copies[key] = GraphNode(neighbor.value)
                queue.append(neighbor)
            }
            copy.neighbors.append(copies[key]!)
        }
    }
    return copies[ObjectIdentifier(node)]
}
```

The copy is created when a node is first **seen**, not when it's processed. That is what lets a link to a not-yet-processed node be wired immediately — its copy already exists, empty, and gets its own neighbours when its turn comes.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, three more (two nodes linked to each other, a four-node ring, a star with one centre), and 500 random connected graphs; every case checks the copy's adjacency list and that no copied node is identical to an original.
:::

::: Walk it through
**`[[2, 3], [1, 3], [1, 2, 4], [3]]`** — primes mark copies.

| Process | Its neighbours | New copies made | Copy's neighbours | Queue after |
|---|---|---|---|---|
| start | — | 1′ | — | 1 |
| 1 | 2, 3 | 2′, 3′ | 1′ → 2′, 3′ | 2, 3 |
| 2 | 1, 3 | none | 2′ → 1′, 3′ | 3 |
| 3 | 1, 2, 4 | 4′ | 3′ → 1′, 2′, 4′ | 4 |
| 4 | 3 | none | 4′ → 3′ | empty |

Return 1′. The triangle 1–2–3 is a cycle, but the walk stops because by the time 3 lists 1 and 2, both already have copies.

**`[]`** — there is no node, so `guard let` returns `nil` straight away. **`[[]]`** — the start node has no neighbours; the loop runs once and returns a lone 1′.
:::

::: The Swift trap
**A class isn't `Hashable`, and the obvious fix keys by the wrong thing.** `[GraphNode: GraphNode]` doesn't compile. The tempting repair is `[Int: GraphNode]` keyed by `node.value`, which works here only because the statement promises unique numbers; give two nodes the same number and the copy silently merges them. Making `GraphNode` `Hashable` by its value has the same flaw. `ObjectIdentifier(node)` keys by **identity** — this exact object — which is what "have I copied this node already" really asks. Related: the copy is full of reference cycles (A holds B, B holds A), so it never deallocates; fine for the exercise, worth one sentence if they ask about memory.
:::

::: What they ask next
- **"Do it with DFS."** → Same map; a recursive `clone(node)` returns the map entry if present, otherwise creates the copy, stores it **before** recursing into the neighbours, then fills them in. Storing first is what stops infinite recursion.
- **"The graph might not be connected; you get all the nodes."** → Loop over every node and start a walk from each one that has no copy yet, sharing one map.
- **"Copy a linked list whose nodes also have a random pointer."** → The same original-to-copy map, walking `next`; or the O(1)-space trick of weaving each copy right after its original, then unweaving.
:::
