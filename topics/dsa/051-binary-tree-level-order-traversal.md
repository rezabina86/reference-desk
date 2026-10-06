---
title: 43 · Binary Tree Level Order Traversal
summary: List a binary tree's values row by row, top to bottom and left to right, one list per row.
group: Trees
minutes: 25
sources:
- LeetCode 102 · Binary Tree Level Order Traversal | https://leetcode.com/problems/binary-tree-level-order-traversal/
- Swift standard library · Array.removeFirst() | https://developer.apple.com/documentation/swift/array/removefirst()
---

*Medium · G*

You get the root of a binary tree. Return its values grouped by level: a list for the root, then a list for the root's children, then one for the grandchildren, and so on. Inside each list, values go from left to right. An empty tree gives an empty result.

| Tree | Answer |
|---|---|
| `[1, 2, 3, 4, nil, nil, 5]` | `[[1], [2, 3], [4, 5]]` — 4 is under 2, 5 is under 3 |
| `[7, nil, 8, nil, 9]` | `[[7], [8], [9]]` — a chain: one value per level |
| `[]` | `[]` |

Constraints that matter: up to 2,000 nodes. Every node appears in the output, so O(n) is the target.

::: Starter code and tests
In an Xcode test target:

```swift
import Testing

struct BinaryTreeLevelOrderTraversalTests {

    @Test(arguments: [
        ([1, 2, 3, 4, nil, nil, 5], [[1], [2, 3], [4, 5]]),
        ([7, nil, 8, nil, 9], [[7], [8], [9]]),
        ([], []),
    ] as [([Int?], [[Int]])])
    func groupsTheValuesRowByRow(input: [Int?], expected: [[Int]]) {
        #expect(levelOrder(makeTree(input)) == expected)
    }

    // MARK: - Privates
    private func levelOrder(_ root: TreeNode?) -> [[Int]] {
        []
    }
}

private final class TreeNode {
    var value: Int
    var left: TreeNode?
    var right: TreeNode?
    init(_ value: Int, _ left: TreeNode? = nil, _ right: TreeNode? = nil) {
        self.value = value; self.left = left; self.right = right
    }
}

/// Builds a tree from level order, nil for a missing child: [3, 9, 20, nil, nil, 15, 7]
private func makeTree(_ levelOrder: [Int?]) -> TreeNode? {
    guard let first = levelOrder.first, let rootValue = first else { return nil }
    let root = TreeNode(rootValue)
    var queue = [root]
    var index = 1
    var head = 0
    while head < queue.count, index < levelOrder.count {
        let node = queue[head]; head += 1
        if let value = levelOrder[index] { node.left = TreeNode(value); queue.append(node.left!) }
        index += 1
        if index < levelOrder.count, let value = levelOrder[index] { node.right = TreeNode(value); queue.append(node.right!) }
        index += 1
    }
    return root
}
```

In a playground:

```swift
final class TreeNode {
    var value: Int
    var left: TreeNode?
    var right: TreeNode?
    init(_ value: Int, _ left: TreeNode? = nil, _ right: TreeNode? = nil) {
        self.value = value; self.left = left; self.right = right
    }
}

/// Builds a tree from level order, nil for a missing child: [3, 9, 20, nil, nil, 15, 7]
func makeTree(_ levelOrder: [Int?]) -> TreeNode? {
    guard let first = levelOrder.first, let rootValue = first else { return nil }
    let root = TreeNode(rootValue)
    var queue = [root]
    var index = 1
    var head = 0
    while head < queue.count, index < levelOrder.count {
        let node = queue[head]; head += 1
        if let value = levelOrder[index] { node.left = TreeNode(value); queue.append(node.left!) }
        index += 1
        if index < levelOrder.count, let value = levelOrder[index] { node.right = TreeNode(value); queue.append(node.right!) }
        index += 1
    }
    return root
}

func levelOrder(_ root: TreeNode?) -> [[Int]] {
    [] // your solution
}

let cases: [([Int?], [[Int]])] = [
    ([1, 2, 3, 4, nil, nil, 5], [[1], [2, 3], [4, 5]]),
    ([7, nil, 8, nil, 9], [[7], [8], [9]]),
    ([], []),
]
for (input, expected) in cases {
    let got = levelOrder(makeTree(input))
    print(got == expected ? "PASS" : "FAIL", input, "→", got, "expected", expected)
}
```
:::

::: Pattern and cue
**Breadth-first, one level at a time.** The cue is *"level by level"* / *"row by row"*: nodes closest to the root first. Depth-first would reach a grandchild before the root's second child; breadth-first visits in exactly the order the output wants.
:::

::: Approach
Start with a row holding just the root. Write down the row's values, left to right. Then build the next row: go through the current row in order and collect each node's left child, then its right child, skipping the missing ones. Replace the current row with the new one and repeat until a row comes out empty.

Time O(n): each node is put into a row once and read once. Space O(w), the widest row, which can be about n/2 on a full tree (the output itself is O(n) on top).
:::

::: Swift solution
```swift
func levelOrder(_ root: TreeNode?) -> [[Int]] {
    guard let root else { return [] }
    var result: [[Int]] = []
    var level = [root]
    while !level.isEmpty {
        result.append(level.map(\.value))
        var next: [TreeNode] = []
        for node in level {
            if let left = node.left { next.append(left) }
            if let right = node.right { next.append(right) }
        }
        level = next
    }
    return result
}
```

Keeping each row in its own array means the row boundaries come for free: there is no counting of "how many nodes belong to this level", and nothing is ever removed from the front of an array.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, four more (a single node, a full tree of four levels, a left-only chain, a tree whose last row has gaps), and 3,000 random trees checked against a depth-first version that appends each value to the list for its depth.
:::

::: Walk it through
**`[1, 2, 3, 4, nil, nil, 5]`** — 1 has children 2 and 3; 2 has a left child 4; 3 has a right child 5.

| Row | Written down | Next row built from it |
|---|---|---|
| `[1]` | `[1]` | 2, 3 |
| `[2, 3]` | `[2, 3]` | 2's left 4; 3's right 5 |
| `[4, 5]` | `[4, 5]` | none |
| `[]` | — | stop |

Answer `[[1], [2, 3], [4, 5]]`.

**`[]`** — the `guard` returns `[]` before the loop. It also unwraps the root, so every row is an array of real nodes: with the optional root, `[root]` would be a `[TreeNode?]` and an empty tree would begin with a row holding one `nil`.
:::

::: The Swift trap
**A textbook queue with `removeFirst()` is quietly O(n²).** The version from other languages keeps one queue and does `let node = queue.removeFirst()`. In Swift that compiles and passes, but `Array.removeFirst()` shifts every remaining element down by one, O(n) each time, so a wide tree costs O(n²). The standard library has no `Deque` (it's in swift-collections, which a shared interview editor won't have). Either keep separate row arrays, as above, or keep one array and a `head` index that moves forward instead of removing anything. If you do use one queue, take `let count = queue.count - head` at the start of each level to know where the row ends.
:::

::: What they ask next
- **"Zigzag: left to right, then right to left, alternating."** → Same rows; reverse every second row's values before appending them (`level.map(\.value).reversed()`). The walking order doesn't change.
- **"Only the rightmost value of each level: the view from the right side."** → Same rows, append `level.last!.value` instead of the whole row.
- **"Bottom-up order."** → Build it top-down as above and reverse the outer array once at the end: O(n), not an insert at index 0 per row.
:::
