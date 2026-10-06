---
title: 42 · Lowest Common Ancestor of a Binary Search Tree
summary: In a binary search tree, find the deepest node that has both of two given values somewhere below it or is one of them.
group: Trees
minutes: 25
sources:
- LeetCode 235 · Lowest Common Ancestor of a Binary Search Tree | https://leetcode.com/problems/lowest-common-ancestor-of-a-binary-search-tree/
---

*Medium · G*

You get a binary search tree — every node's left branch holds smaller values, its right branch larger ones — and two values, p and q, that are both in the tree. Find their lowest common ancestor: the deepest node that has both p and q in its branch. A node counts as its own ancestor, so if p sits above q, the answer is p itself. Return that node. All values are different.

All three examples use the tree `[20, 10, 30, 5, 15, 25, 40, nil, nil, 12, 18]`: 20 at the root, 10 and 30 below it, then 5 and 15 under 10, 25 and 40 under 30, and 12 and 18 under 15.

| p | q | Answer |
|---|---|---|
| 10 | 30 | `20` — they split at the root |
| 12 | 18 | `15` |
| 10 | 18 | `10` — 10 is above 18, so it is the ancestor |

Constraints that matter: up to 100,000 nodes, p ≠ q, both present. Searching the whole tree is O(n); the ordering lets you do it in O(h), the height, with O(1) extra space.

::: Starter code and tests
In an Xcode test target:

```swift
import Testing

struct LowestCommonAncestorOfABinarySearchTreeTests {

    @Test(arguments: [
        ([20, 10, 30, 5, 15, 25, 40, nil, nil, 12, 18], 10, 30, 20),
        ([20, 10, 30, 5, 15, 25, 40, nil, nil, 12, 18], 12, 18, 15),
        ([20, 10, 30, 5, 15, 25, 40, nil, nil, 12, 18], 10, 18, 10),
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

let tree: [Int?] = [20, 10, 30, 5, 15, 25, 40, nil, nil, 12, 18]
let cases: [(Int, Int, Int)] = [
    (10, 30, 20),
    (12, 18, 15),
    (10, 18, 10),
]
for (p, q, expected) in cases {
    let got = lowestCommonAncestor(makeTree(tree), p, q)?.value
    print(got == expected ? "PASS" : "FAIL", p, q, "→", got.map(String.init) ?? "nil", "expected", expected)
}
```

LeetCode passes p and q as nodes; here they are values, which is the same thing in a tree whose values are all different, and the function returns the ancestor node.
:::

::: Pattern and cue
**Walk down a BST, one direction per node.** The cue is *"binary search tree"* in a question about where two values sit. At each node the ordering tells you which side each value is on — so you never search, you steer.
:::

::: Approach
Start at the root. If both values are smaller than the current node, both live in its left branch, so their common ancestor is down there too: go left. If both are larger, go right. Otherwise they are on different sides — or one of them *is* this node — and this is the first node where their paths from the root part ways: it's the answer.

Time O(h), the height of the tree: one step down per level, O(log n) when balanced and O(n) on a chain. Space O(1): just the current node.
:::

::: Swift solution
```swift
func lowestCommonAncestor(_ root: TreeNode?, _ p: Int, _ q: Int) -> TreeNode? {
    var node = root
    while let current = node {
        if p < current.value && q < current.value {
            node = current.left
        } else if p > current.value && q > current.value {
            node = current.right
        } else {
            return current                  // they split here, or one of them is here
        }
    }
    return nil
}
```

The `else` covers three cases with one line: p left and q right, the reverse, and either value equal to the current node.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, five more (the root as one of the two, two leaves on opposite sides of the root, parent and child, values passed in either order, a two-node tree), and 3,000 random BSTs with random pairs checked against the last common node of the two root-to-value paths.
:::

::: Walk it through
**p = 12, q = 18**

| Node | 12 vs node | 18 vs node | Move |
|---|---|---|---|
| 20 | smaller | smaller | left |
| 10 | larger | larger | right |
| 15 | smaller | larger | split: return 15 |

**p = 10, q = 18** — at 20 both are smaller: go left. At 10, p equals the node, so neither "both smaller" nor "both larger" holds: return 10. The walk never needs to find 18; the ordering already guarantees it's below.
:::

::: The Swift trap
**The recursive version is O(h) stack, not O(1).** It's natural to write this as `return lowestCommonAncestor(root.left, p, q)` and call it tail recursion. Swift doesn't promise tail-call elimination, and in a debug build it doesn't do it, so every step down costs a stack frame — and a test thread has only 512 KB of stack. On a BST built from sorted input — a chain, which the constraints allow up to 100,000 deep — that crashes; in a debug build on Swift 6.4, the recursive version already crashed a test on a 2,000-node chain. The `while let` loop above is the version to write; say why: "the recursion is tail-shaped, but Swift won't turn it into a loop for me".
:::

::: What they ask next
- **"Same question, but an ordinary binary tree with no ordering."** → You can't steer any more: search both branches and see where p and q turn up. That's problem 46, O(n).
- **"What if p or q might not be in the tree?"** → The walk would return a node anyway; verify both values with two BST lookups (O(h) each) before trusting it.
- **"Find the distance between p and q."** → Find the ancestor, then the depth of p below it plus the depth of q below it, each by a BST walk from the ancestor.
:::
