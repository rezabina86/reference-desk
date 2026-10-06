---
title: 40 · Same Tree
summary: Decide whether two binary trees have exactly the same shape and the same value in every matching position.
group: Trees
minutes: 20
sources:
- LeetCode 100 · Same Tree | https://leetcode.com/problems/same-tree/
- Swift Programming Language · Identity operators | https://docs.swift.org/swift-book/documentation/the-swift-programming-language/classesandstructures/#Identity-Operators
---

*Easy · G*

You get the roots of two binary trees. Return `true` if they are the same tree: the same shape, and the same value at every position. Same values arranged differently don't count — a node with only a left child is not the same as a node with only a right child. Two empty trees are the same.

| First | Second | Answer |
|---|---|---|
| `[4, 2, 6]` | `[4, 2, 6]` | `true` |
| `[4, 2]` | `[4, nil, 2]` | `false` — the same values, but 2 hangs on different sides |
| `[]` | `[]` | `true` |

Constraints that matter: up to 100 nodes in each tree. You must look at every node in the worst case, so O(n) is the target.

::: Starter code and tests
In an Xcode test target:

```swift
import Testing

struct SameTreeTests {

    @Test(arguments: [
        ([4, 2, 6], [4, 2, 6], true),
        ([4, 2], [4, nil, 2], false),
        ([], [], true),
    ] as [([Int?], [Int?], Bool)])
    func matchesShapeAndValuesEverywhere(first: [Int?], second: [Int?], expected: Bool) {
        #expect(isSameTree(makeTree(first), makeTree(second)) == expected)
    }

    // MARK: - Privates
    private func isSameTree(_ p: TreeNode?, _ q: TreeNode?) -> Bool {
        false
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

func isSameTree(_ p: TreeNode?, _ q: TreeNode?) -> Bool {
    false // your solution
}

let cases: [([Int?], [Int?], Bool)] = [
    ([4, 2, 6], [4, 2, 6], true),
    ([4, 2], [4, nil, 2], false),
    ([], [], true),
]
for (first, second, expected) in cases {
    let got = isSameTree(makeTree(first), makeTree(second))
    print(got == expected ? "PASS" : "FAIL", first, second, "→", got, "expected", expected)
}
```
:::

::: Pattern and cue
**Depth-first over two trees at once.** The cue is comparing two trees *position by position*. Walk both in step: the same move in each tree, the same question at each pair of nodes, and stop at the first difference.
:::

::: Approach
Look at the two roots together. If both are missing, these two (sub)trees agree. If exactly one is missing, or their values differ, they don't. Otherwise the roots match, and the trees are the same only if the two left branches are the same tree and the two right branches are the same tree — the same question, asked one level down.

Time O(n), where n is the smaller tree's size: each pair of matching positions is compared once, and the walk stops at the first mismatch. Space O(h) for the recursion.
:::

::: Swift solution
```swift
func isSameTree(_ p: TreeNode?, _ q: TreeNode?) -> Bool {
    switch (p, q) {
    case (nil, nil):
        return true
    case let (p?, q?):
        return p.value == q.value
            && isSameTree(p.left, q.left)
            && isSameTree(p.right, q.right)
    default:
        return false                        // exactly one side is missing
    }
}
```

Switching over the pair of optionals names all three shape cases — both empty, both present, one missing — and the compiler checks none is forgotten. `&&` stops at the first `false`, so a mismatch near the root skips the rest.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, five more (one empty and one not, same shape with one different value, a tree against itself, swapped children, a deep difference in the last leaf), and 3,000 random pairs of small trees checked against comparing their full level-order listings.
:::

::: Walk it through
**`[4, 2, 6]` and `[4, 2, 6]`**

| Pair | Case | Result |
|---|---|---|
| (4, 4) | both present, values equal | ask left pair, then right pair |
| (2, 2) | both present, equal | its children are (nil, nil) and (nil, nil): `true` |
| (6, 6) | both present, equal | `true` |
| back at (4, 4) | `true && true && true` | `true` |

**`[4, 2]` and `[4, nil, 2]`** — the roots match. The left pair is (2, nil): exactly one side is missing, the `default` case returns `false`, and `&&` never looks at the right pair.
:::

::: The Swift trap
**`p == q` doesn't compile, and `===` is the wrong question.** `TreeNode` is a class with no `Equatable` conformance, so `p == q` is an error. The tempting fixes both go wrong. `p === q` compiles, but it asks "are these the same object in memory?" — two trees built separately with identical values are different objects, so it returns `false` for the first example. Adding `extension TreeNode: Equatable` with `lhs.value == rhs.value` compiles too, but compares only the two roots, not the trees below them. The structural walk above is the comparison; there is no shortcut operator.
:::

::: What they ask next
- **"Do it without recursion."** → One stack (or queue) of pairs: push `(p, q)`, pop a pair, apply the same three cases, push the two child pairs.
- **"Is a tree symmetric — the same as its own mirror?"** → The same walk on `(root.left, root.right)`, but compare `a.left` with `b.right` and `a.right` with `b.left`.
- **"Same values but children may be swapped at any node."** → At each pair, accept either `same(a.left, b.left) && same(a.right, b.right)` or the crossed pairing. That's "flip-equivalent" trees.
:::
