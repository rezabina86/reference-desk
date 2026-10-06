---
title: 39 · Maximum Depth of Binary Tree
summary: Count how many levels a binary tree has, from the root down to its deepest leaf.
group: Trees
minutes: 20
sources:
- LeetCode 104 · Maximum Depth of Binary Tree | https://leetcode.com/problems/maximum-depth-of-binary-tree/
---

*Easy · G*

You get the root of a binary tree. Return its depth: the number of nodes on the longest path from the root down to a leaf, counting both ends. A tree with only a root has depth 1; an empty tree has depth 0.

| Tree | Answer |
|---|---|
| `[8, 4, 9, nil, nil, 6, 12, nil, 7]` | `4` — the path 8 → 9 → 6 → 7 |
| `[1, nil, 2, nil, 3]` | `3` — a chain leaning right |
| `[]` | `0` |

Constraints that matter: up to 10,000 nodes, so the tree can be a chain 10,000 deep. Every node may be the deepest, so O(n) time is the target; the interesting part is the space.

::: Starter code and tests
In an Xcode test target:

```swift
import Testing

struct MaximumDepthOfBinaryTreeTests {

    @Test(arguments: [
        ([8, 4, 9, nil, nil, 6, 12, nil, 7], 4),
        ([1, nil, 2, nil, 3], 3),
        ([], 0),
    ] as [([Int?], Int)])
    func countsTheLevelsOnTheLongestRootToLeafPath(levelOrder: [Int?], expected: Int) {
        #expect(maxDepth(makeTree(levelOrder)) == expected)
    }

    // MARK: - Privates
    private func maxDepth(_ root: TreeNode?) -> Int {
        0
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

func maxDepth(_ root: TreeNode?) -> Int {
    0 // your solution
}

let cases: [([Int?], Int)] = [
    ([8, 4, 9, nil, nil, 6, 12, nil, 7], 4),
    ([1, nil, 2, nil, 3], 3),
    ([], 0),
]
for (levelOrder, expected) in cases {
    let got = maxDepth(makeTree(levelOrder))
    print(got == expected ? "PASS" : "FAIL", levelOrder, "→", got, "expected", expected)
}
```
:::

::: Pattern and cue
**Depth-first, handing a value back up.** The cue is *"depth"* of the whole tree: a node's answer is fully decided by its children's answers. Ask the left branch how deep it is, ask the right branch, take the larger and add one for yourself.
:::

::: Approach
An empty tree is 0 levels deep. For any other tree, the deepest path starts at the root and then continues down whichever branch is deeper, so the depth is one (the root) plus the larger of the two branch depths. Each branch works out its own depth the same way, down to the empty spaces below the leaves, which report 0.

Time O(n): every node is asked once. Space O(h), the height, for the chain of calls waiting on their children: O(log n) on a balanced tree, O(n) on a chain.
:::

::: Swift solution
```swift
func maxDepth(_ root: TreeNode?) -> Int {
    guard let root else { return 0 }
    return 1 + max(maxDepth(root.left), maxDepth(root.right))
}
```

The `guard let` is the whole base case: a missing child reports 0, so a leaf reports 1 + max(0, 0) = 1 without a special case.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, four more (a single node, a left-leaning chain of 1,000, a full tree of four levels, a lopsided tree where the deep side is on the left), the breadth-first version from the trap below on the same inputs, and 2,000 random trees checked against the longest root-to-node path found by listing every path.
:::

::: Walk it through
**`[8, 4, 9, nil, nil, 6, 12, nil, 7]`** — 8 has children 4 and 9; 9 has children 6 and 12; 6 has a right child 7.

| Node | Left depth | Right depth | Returns |
|---|---|---|---|
| 4 | 0 | 0 | 1 |
| 7 | 0 | 0 | 1 |
| 6 | 0 | 1 | 2 |
| 12 | 0 | 0 | 1 |
| 9 | 2 | 1 | 3 |
| 8 | 1 | 3 | 4 |

Answer 4.

**`[]`** — the root is `nil`, the `guard` returns 0 straight away.
:::

::: The Swift trap
**A deep enough chain crashes the test, not the algorithm.** Swift doesn't turn recursion into a loop, and Swift Testing runs each test on a secondary thread with a 512 KB stack. In a debug build on Swift 6.4, this recursive `maxDepth` crashed on a chain only 3,000 nodes deep — well inside the 10,000 the constraints allow. Worse, simply *releasing* such a chain crashed the same way: ARC frees a node, which frees its child, which frees its child, one nested call per level. If the interviewer mentions a degenerate tree, switch to a loop:

```swift
func maxDepthIterative(_ root: TreeNode?) -> Int {
    guard let root else { return 0 }
    var level = [root]
    var depth = 0
    while !level.isEmpty {
        depth += 1
        var next: [TreeNode] = []
        for node in level {
            if let left = node.left { next.append(left) }
            if let right = node.right { next.append(right) }
        }
        level = next
    }
    return depth
}
```

Breadth-first, one level at a time, no recursion: the depth is just the number of levels.
:::

::: What they ask next
- **"Minimum depth: the shortest path to a leaf."** → Not just `min` instead of `max`: a node with one child is not a leaf, so a missing side must be ignored, not counted as 0. Breadth-first is simpler: return the level of the first leaf you meet.
- **"Is the tree balanced (sides differ by at most 1 everywhere)?"** → Same post-order walk, but return −1 as soon as any node's sides differ by more than 1, and pass the −1 straight up.
- **"Diameter: the longest path between any two nodes."** → At each node, left depth + right depth is a candidate; record the best while still returning the depth. The same shape as problem 48.
:::
