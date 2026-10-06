---
title: 46 · Lowest Common Ancestor of a Binary Tree
summary: In a binary tree with no ordering, find the deepest node that has both of two given nodes somewhere below it or is one of them.
group: Trees
minutes: 25
sources:
- LeetCode 236 · Lowest Common Ancestor of a Binary Tree | https://leetcode.com/problems/lowest-common-ancestor-of-a-binary-tree/
- Swift Programming Language · Identity operators | https://docs.swift.org/swift-book/documentation/the-swift-programming-language/classesandstructures/#Identity-Operators
---

*Medium · G · Z — Delivery Hero asked this one by name*

You get the root of a binary tree — no ordering this time, values can sit anywhere — and two values, p and q, that are both in the tree. Find their lowest common ancestor: the deepest node that has both p and q in its branch. A node counts as its own ancestor, so if p is above q, the answer is p. Return that node. All values are different.

All three examples use the tree `[8, 3, 5, 1, 9, 2, 6, nil, nil, 4, 7]`: 8 at the root, 3 and 5 below it, 1 and 9 under 3, 2 and 6 under 5, and 4 and 7 under 9.

| p | q | Answer |
|---|---|---|
| 3 | 5 | `8` — one on each side of the root |
| 3 | 7 | `3` — 7 is inside 3's branch |
| 4 | 7 | `9` |

Constraints that matter: up to 100,000 nodes, p ≠ q, both present. Without an ordering you can't steer, so O(n) — look at every node once — is the target.

::: Starter code and tests
In an Xcode test target:

```swift
import Testing

struct LowestCommonAncestorOfABinaryTreeTests {

    @Test(arguments: [
        ([8, 3, 5, 1, 9, 2, 6, nil, nil, 4, 7], 3, 5, 8),
        ([8, 3, 5, 1, 9, 2, 6, nil, nil, 4, 7], 3, 7, 3),
        ([8, 3, 5, 1, 9, 2, 6, nil, nil, 4, 7], 4, 7, 9),
    ] as [([Int?], Int, Int, Int)])
    func findsTheDeepestNodeAboveBothValues(levelOrder: [Int?], p: Int, q: Int, expected: Int) {
        #expect(lowestCommonAncestor(makeTree(levelOrder), p, q)?.value == expected)
    }

    // MARK: - Privates
    private func lowestCommonAncestor(_ root: TreeNode?, _ p: Int, _ q: Int) -> TreeNode? {
        nil
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

func lowestCommonAncestor(_ root: TreeNode?, _ p: Int, _ q: Int) -> TreeNode? {
    nil // your solution
}

let tree: [Int?] = [8, 3, 5, 1, 9, 2, 6, nil, nil, 4, 7]
let cases: [(Int, Int, Int)] = [
    (3, 5, 8),
    (3, 7, 3),
    (4, 7, 9),
]
for (p, q, expected) in cases {
    let got = lowestCommonAncestor(makeTree(tree), p, q)?.value
    print(got == expected ? "PASS" : "FAIL", p, q, "→", got.map(String.init) ?? "nil", "expected", expected)
}
```

LeetCode passes p and q as nodes; here they are values, which identifies them just as well when all values differ, and the function returns the ancestor node.
:::

::: Pattern and cue
**Depth-first, handing a found node back up.** The cue is *"ancestor"* in a tree with no ordering. Each branch reports what it found below it; the first node to hear back from **both** sides is where the two paths meet.
:::

::: Approach
Ask each node: "is p or q in your branch?" An empty spot answers no. A node that is p or q answers with itself — whatever is below it doesn't matter, since it's already an ancestor of the other one or the other one is elsewhere. Any other node asks its left branch and its right branch. If both come back with something, p is on one side and q on the other, so this node is the meeting point: answer with yourself. If only one side found something, pass that answer up unchanged. The root's answer is the lowest common ancestor.

Time O(n): each node is visited at most once. Space O(h) for the recursion.
:::

::: Swift solution
```swift
func lowestCommonAncestor(_ root: TreeNode?, _ p: Int, _ q: Int) -> TreeNode? {
    guard let root else { return nil }
    if root.value == p || root.value == q { return root }
    let left = lowestCommonAncestor(root.left, p, q)
    let right = lowestCommonAncestor(root.right, p, q)
    if left != nil && right != nil { return root }     // p on one side, q on the other
    return left ?? right                               // pass up whatever was found, if anything
}
```

`left ?? right` covers three cases in one expression: only the left found something, only the right did, or neither did (`nil`).

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, five more (the root as one of the two, a parent and its direct child, two leaves at different depths, values passed in either order, a two-node tree), the parent-map version from the follow-ups on all of them, and 3,000 random trees with random pairs checked against the last common node of the two root-to-value paths.
:::

::: Walk it through
**p = 4, q = 7** — 8 has children 3 and 5; 3 has children 1 and 9; 9 has children 4 and 7.

| Node | Left reports | Right reports | Returns |
|---|---|---|---|
| 1 | nil | nil | nil |
| 4 | — | — | 4 (it is p) |
| 7 | — | — | 7 (it is q) |
| 9 | 4 | 7 | **9**, both sides found something |
| 3 | nil (from 1) | 9 | 9 |
| 5's branch | nil | nil | nil |
| 8 | 9 | nil | 9 |

Answer 9.

**p = 3, q = 7** — the walk reaches 3, which is p, and returns 3 without looking below it. The right side of 8 finds nothing, so 3 is passed up. That's correct because q is guaranteed to be somewhere: if it's not on the other side, it must be under 3.
:::

::: The Swift trap
**With LeetCode's signature, compare nodes with `===`, not `==`.** On LeetCode the function receives `p: TreeNode?` and `q: TreeNode?`. Writing `if root == p` doesn't compile, because `TreeNode` isn't `Equatable`. The fix is identity: `if root === p || root === q { return root }` — the same object, which is exactly what "this node is p" means. Don't add an `Equatable` conformance comparing values: it compiles, and it silently gives wrong answers on a tree where two nodes share a value. In the value-based version above, the statement's "all values are different" is what makes `root.value == p` safe; say that assumption out loud.
:::

::: What they ask next
- **"What if p or q might not be in the tree?"** → The early return at p or q no longer proves anything. Count how many of the two you actually found in the walk (don't stop at p or q, keep searching below), and return the node only if the count reaches 2.
- **"The tree is 100,000 nodes deep; avoid recursion."** → Walk the tree with an explicit stack, recording each node's parent in a dictionary until both p and q are recorded. Put all of p's ancestors (following parents) in a set, then follow q's parents until you hit one in the set.
- **"Each node has a parent pointer and you're given the two nodes, not the root."** → It's the intersection of two linked lists: step both upward, and when one reaches the top, restart it at the other's start node; they meet at the ancestor.
:::
