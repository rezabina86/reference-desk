---
title: 38 · Invert Binary Tree
summary: Turn a binary tree into its mirror image, so every left branch becomes a right branch and the other way round.
group: Trees
minutes: 20
sources:
- LeetCode 226 · Invert Binary Tree | https://leetcode.com/problems/invert-binary-tree/
---

*Easy · G*

You get the root of a binary tree. Flip it left to right, as if you held it up to a mirror: at **every** node, the left child and the right child trade places — not only at the root. Return the root of the flipped tree. An empty tree stays empty.

Trees are written in level order, row by row from the left, with `nil` for a missing child.

| Tree | Answer |
|---|---|
| `[5, 3, 8, 1, 4]` | `[5, 8, 3, nil, nil, 4, 1]` |
| `[2, 1]` | `[2, nil, 1]` — the lone left child moves to the right |
| `[]` | `[]` |

Constraints that matter: up to 100 nodes, values from −100 to 100. Every node has to move, so O(n) is the target; the point is to write it cleanly.

::: Starter code and tests
In an Xcode test target:

```swift
import Testing

struct InvertBinaryTreeTests {

    @Test(arguments: [
        ([5, 3, 8, 1, 4], [5, 8, 3, nil, nil, 4, 1]),
        ([2, 1], [2, nil, 1]),
        ([], []),
    ] as [([Int?], [Int?])])
    func swapsTheChildrenOfEveryNode(levelOrder: [Int?], expected: [Int?]) {
        #expect(levelOrderValues(invertTree(makeTree(levelOrder))) == expected)
    }

    // MARK: - Privates
    private func invertTree(_ root: TreeNode?) -> TreeNode? {
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

/// Level order with nil for missing children, trailing nils removed
private func levelOrderValues(_ root: TreeNode?) -> [Int?] {
    var result: [Int?] = []
    var queue: [TreeNode?] = [root]
    var head = 0
    while head < queue.count {
        let node = queue[head]; head += 1
        result.append(node?.value)
        if let node { queue.append(node.left); queue.append(node.right) }
    }
    while result.last == .some(nil) { result.removeLast() }
    return result
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

/// Level order with nil for missing children, trailing nils removed
func levelOrderValues(_ root: TreeNode?) -> [Int?] {
    var result: [Int?] = []
    var queue: [TreeNode?] = [root]
    var head = 0
    while head < queue.count {
        let node = queue[head]; head += 1
        result.append(node?.value)
        if let node { queue.append(node.left); queue.append(node.right) }
    }
    while result.last == .some(nil) { result.removeLast() }
    return result
}

func invertTree(_ root: TreeNode?) -> TreeNode? {
    nil // your solution
}

let cases: [([Int?], [Int?])] = [
    ([5, 3, 8, 1, 4], [5, 8, 3, nil, nil, 4, 1]),
    ([2, 1], [2, nil, 1]),
    ([], []),
]
for (levelOrder, expected) in cases {
    let got = levelOrderValues(invertTree(makeTree(levelOrder)))
    print(got == expected ? "PASS" : "FAIL", levelOrder, "→", got, "expected", expected)
}
```
:::

::: Pattern and cue
**Depth-first walk, changing each node.** The cue is *"every node"* plus a rule that is the same at each node and doesn't depend on anything above it. Fix the root, and the job that remains is the same job on two smaller trees.
:::

::: Approach
If the tree is empty, there is nothing to flip. Otherwise, flip the right branch, flip the left branch, and hang them back on the node the other way round: the flipped right branch becomes the left child, the flipped left branch becomes the right child. Each branch flips itself by the same rule, all the way down to the leaves.

Time O(n): each node is visited once and does a constant amount of work. Space O(h) for the recursion, where h is the height of the tree — O(log n) when balanced, O(n) for a chain.
:::

::: Swift solution
```swift
func invertTree(_ root: TreeNode?) -> TreeNode? {
    guard let root else { return nil }
    (root.left, root.right) = (invertTree(root.right), invertTree(root.left))
    return root
}
```

The tuple assignment computes both flipped branches before it writes either child, so neither line can read a child the other has already overwritten.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, four more (a single node, a left-only chain of four, a full tree of three levels, inverting twice gives the original back), and 2,000 random trees checked against a builder that makes a brand-new mirrored copy.
:::

::: Walk it through
**`[5, 3, 8, 1, 4]`** — 5 has children 3 and 8; 3 has children 1 and 4.

| Call | Flips | Result hung back |
|---|---|---|
| `invertTree(8)` | a leaf: both children nil | 8 |
| `invertTree(4)`, `invertTree(1)` | leaves | 4, 1 |
| `invertTree(3)` | left ← flipped 4, right ← flipped 1 | 3 with children 4, 1 |
| `invertTree(5)` | left ← flipped 8, right ← flipped 3 | 5 with children 8, 3 |

Read row by row: `[5, 8, 3, nil, nil, 4, 1]` — 8 has no children, then 3's children 4 and 1.

**`[2, 1]`** — 2 has only a left child. Its right side is `nil`, which flips to `nil`; so the left child becomes `nil` and the right child becomes 1: `[2, nil, 1]`.
:::

::: The Swift trap
**Two lines instead of one tuple, and the tree loses a branch.** The natural first attempt is

```swift
root.left = invertTree(root.right)
root.right = invertTree(root.left)   // reads the left you just replaced
```

The second line reads `root.left` after the first line overwrote it, so both children end up as the flipped right branch and the original left branch is gone. The tuple form `(root.left, root.right) = (…, …)` evaluates the whole right-hand side first. Second half of the trap: `TreeNode` is a class, so the function rewires the tree it was given. After `let flipped = invertTree(original)`, `original` and `flipped` are the same object; if the interviewer wants the input left alone, build new nodes instead: `TreeNode(root.value, mirror(root.right), mirror(root.left))`.
:::

::: What they ask next
- **"Do it without recursion."** → Breadth-first with an index-based queue (or a stack): take a node out, swap its two children, put the non-nil children in. Same O(n), no call-stack depth.
- **"Check whether a tree is its own mirror."** → Walk two pointers at once, the left one going left while the right one goes right: values equal, then compare `a.left` with `b.right` and `a.right` with `b.left`.
- **"Leave the original untouched."** → Return new nodes: `TreeNode(root.value, invert(root.right), invert(root.left))`. O(n) extra memory for the copy.
:::
