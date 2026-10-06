---
title: 48 · Binary Tree Maximum Path Sum
summary: Find the largest total you can collect along any path between two nodes of a binary tree whose values may be negative.
group: Trees
minutes: 30
sources:
- LeetCode 124 · Binary Tree Maximum Path Sum | https://leetcode.com/problems/binary-tree-maximum-path-sum/
- Swift Programming Language · Overflow operators | https://docs.swift.org/swift-book/documentation/the-swift-programming-language/advancedoperators/#Overflow-Operators
---

*Hard · optional · G*

**Optional.** Above the bar most German loops set; do it if the topic's mediums went well.

You get the root of a binary tree whose values can be negative. A path is a chain of nodes where each step goes between a parent and its child, with no node used twice. It can start and end anywhere — it doesn't have to touch the root or a leaf — and it can go up through a node and back down the other side, but never turn twice. A path has at least one node. Return the largest sum of values along any path.

| Tree | Answer |
|---|---|
| `[-5, 4, -2, nil, nil, 8, 9]` | `15` — the path 8 → −2 → 9, leaving out the root |
| `[2, -1, 3]` | `5` — 2 → 3; going through −1 only lowers it |
| `[-3]` | `-3` — a path needs at least one node, even a negative one |

Constraints that matter: up to 30,000 nodes, values from −1,000 to 1,000, at least one node. Trying every pair of end points is O(n²); the target is one pass, O(n).

::: Starter code and tests
In an Xcode test target:

```swift
import Testing

struct BinaryTreeMaximumPathSumTests {

    @Test(arguments: [
        ([-5, 4, -2, nil, nil, 8, 9], 15),
        ([2, -1, 3], 5),
        ([-3], -3),
    ] as [([Int?], Int)])
    func findsTheLargestSumAlongAnyPath(levelOrder: [Int?], expected: Int) {
        #expect(maxPathSum(makeTree(levelOrder)) == expected)
    }

    // MARK: - Privates
    private func maxPathSum(_ root: TreeNode?) -> Int {
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

func maxPathSum(_ root: TreeNode?) -> Int {
    0 // your solution
}

let cases: [([Int?], Int)] = [
    ([-5, 4, -2, nil, nil, 8, 9], 15),
    ([2, -1, 3], 5),
    ([-3], -3),
]
for (levelOrder, expected) in cases {
    let got = maxPathSum(makeTree(levelOrder))
    print(got == expected ? "PASS" : "FAIL", levelOrder, "→", got, "expected", expected)
}
```
:::

::: Pattern and cue
**Depth-first, where what you return differs from what you record.** The cue is *"any path … between any two nodes"* in a tree. Every path has one highest node where it bends; at that node it's left arm + node + right arm. But a parent can only use **one** arm of its child, so each node hands up a single straight arm while separately recording the bent path as a candidate answer.
:::

::: Approach
For each node, work out the best straight path that starts at this node and goes down — the most this node can offer its parent. That's the node's value plus the better of its two children's straight paths, but a child whose best is negative is worth skipping, so count it as 0. While you're at the node, also consider the path that bends here: left offer + value + right offer, again ignoring negative offers. Compare that with the best seen so far. Then hand only the straight path up to the parent, since a path through the parent can continue down one side, not both.

Time O(n): each node is visited once. Space O(h) for the recursion.
:::

::: Swift solution
```swift
func maxPathSum(_ root: TreeNode?) -> Int {
    var best = Int.min

    // The best sum of a path that starts at `node` and goes straight down.
    func gain(_ node: TreeNode?) -> Int {
        guard let node else { return 0 }
        let left = max(0, gain(node.left))         // a negative arm is left out
        let right = max(0, gain(node.right))
        best = max(best, node.value + left + right) // the path that bends here
        return node.value + max(left, right)        // the parent may use one arm only
    }

    _ = gain(root)
    return best
}
```

The last two lines are the whole problem: `best` sees both arms, the return value only one. The nested function captures `best` and updates it as the walk goes.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, five more (all values negative, a single positive node, a chain where the best path skips both ends, a path that bends at a deep node, a tree of all zeros), and 3,000 random trees of up to 12 nodes checked against summing the path between every pair of nodes.
:::

::: Walk it through
**`[-5, 4, -2, nil, nil, 8, 9]`** — −5 has children 4 and −2; −2 has children 8 and 9.

| Node | Left arm | Right arm | Bent path here | Best after | Returns up |
|---|---|---|---|---|---|
| 4 | 0 | 0 | 4 | 4 | 4 |
| 8 | 0 | 0 | 8 | 8 | 8 |
| 9 | 0 | 0 | 9 | 9 | 9 |
| −2 | 8 | 9 | −2 + 8 + 9 = 15 | 15 | −2 + 9 = 7 |
| −5 | 4 | 7 | −5 + 4 + 7 = 6 | 15 | 2 |

Answer 15. The root offers a path of 6, but the path bending at −2 is better and was recorded on the way.

**`[-3]`** — both arms are 0, so the bent path is −3 and `best` goes from `Int.min` to −3. Starting `best` at 0 instead would answer 0 — a sum no path has.
:::

::: The Swift trap
**A sentinel of `Int.min` in the wrong place crashes the program.** `best = Int.min` is safe: it's only ever compared. But a variant that returns `Int.min` for a missing child — "so a missing side is never chosen" — then computes `node.value + left`, and for a negative node value that's `Int.min` plus a negative number. C would wrap around to a huge positive number and give a wrong answer; Swift **traps** on the overflow and the test run crashes. Return 0 for a missing child and clamp arms with `max(0, …)`, as above, and nothing ever gets near the edge. (`&+` would wrap instead of trapping, which only swaps the crash for a wrong answer.)
:::

::: What they ask next
- **"Return the path itself, not just the sum."** → Return the arm's node list along with its gain, and when a bent path beats `best`, store left arm reversed + node + right arm.
- **"Paths must go downward only, from an ancestor to a descendant."** → Then no path bends: record `node.value + max(left, right)` (with arms clamped at 0) as the candidate instead of both arms.
- **"Avoid recursion for a very deep tree."** → Visit nodes in post-order with an explicit stack, keeping each node's gain in a dictionary keyed by `ObjectIdentifier(node)` until its parent reads it.
:::
