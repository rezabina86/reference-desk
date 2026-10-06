---
title: 44 · Validate Binary Search Tree
summary: Decide whether a binary tree keeps the search-tree ordering at every node, not just between parents and children.
group: Trees
minutes: 25
sources:
- LeetCode 98 · Validate Binary Search Tree | https://leetcode.com/problems/validate-binary-search-tree/
---

*Medium · G*

You get the root of a binary tree. Return `true` if it is a valid binary search tree: for **every** node, all values anywhere in its left branch are strictly smaller than it, and all values anywhere in its right branch are strictly larger. Checking each node only against its own two children isn't enough. Equal values are not allowed on either side.

| Tree | Answer |
|---|---|
| `[5, 3, 8]` | `true` |
| `[10, 5, 15, nil, nil, 6, 20]` | `false` — 6 is a fine left child of 15, but it's in 10's right branch and smaller than 10 |
| `[4, 2, 6, 1, 3, 5, 7]` | `true` |

Constraints that matter: up to 10,000 nodes, values anywhere in the 32-bit range — including its smallest and largest values. Every node must be checked, so O(n) is the target.

::: Starter code and tests
In an Xcode test target:

```swift
import Testing

struct ValidateBinarySearchTreeTests {

    @Test(arguments: [
        ([5, 3, 8], true),
        ([10, 5, 15, nil, nil, 6, 20], false),
        ([4, 2, 6, 1, 3, 5, 7], true),
    ] as [([Int?], Bool)])
    func checksTheOrderingAgainstEveryAncestor(levelOrder: [Int?], expected: Bool) {
        #expect(isValidBST(makeTree(levelOrder)) == expected)
    }

    // MARK: - Privates
    private func isValidBST(_ root: TreeNode?) -> Bool {
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

func isValidBST(_ root: TreeNode?) -> Bool {
    false // your solution
}

let cases: [([Int?], Bool)] = [
    ([5, 3, 8], true),
    ([10, 5, 15, nil, nil, 6, 20], false),
    ([4, 2, 6, 1, 3, 5, 7], true),
]
for (levelOrder, expected) in cases {
    let got = isValidBST(makeTree(levelOrder))
    print(got == expected ? "PASS" : "FAIL", levelOrder, "→", got, "expected", expected)
}
```
:::

::: Pattern and cue
**Depth-first, passing a range down.** The cue is *"all values in the left branch"*: a rule about a node and **everything** below it, not its children. Each ancestor narrows what's allowed, so carry the allowed range down with you.
:::

::: Approach
The root may hold any value. When you step to a node's left child, everything from there down must stay below that node, so the upper limit becomes the node's value; stepping right, the lower limit becomes the node's value. The other limit is inherited unchanged from above. At each node, check its value lies strictly between the current limits; if any node falls outside, the tree is not a valid search tree.

Time O(n): each node is checked once. Space O(h) for the recursion.
:::

::: Swift solution
```swift
func isValidBST(_ root: TreeNode?) -> Bool {
    func check(_ node: TreeNode?, above low: Int?, below high: Int?) -> Bool {
        guard let node else { return true }
        if let low, node.value <= low { return false }
        if let high, node.value >= high { return false }
        return check(node.left, above: low, below: node.value)
            && check(node.right, above: node.value, below: high)
    }
    return check(root, above: nil, below: nil)
}
```

`nil` means "no limit on this side yet", so no value is ever too small for the root — including `Int.min`. The `<=` and `>=` reject duplicates.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, seven more (an empty tree, a single node, a duplicate on the left `[3, 3]`, a duplicate on the right `[3, nil, 3]`, a lone `Int.min`, a lone `Int.max`, `[Int.min, nil, Int.max]`), and 3,000 random trees — half built as valid BSTs, half random — checked against "the in-order walk is strictly increasing".
:::

::: Walk it through
**`[10, 5, 15, nil, nil, 6, 20]`**

| Node | Allowed range | Inside? |
|---|---|---|
| 10 | (none, none) | yes |
| 5 | (none, 10) | yes; its children are empty |
| 15 | (10, none) | yes |
| 6 | (10, 15) | **no**: 6 ≤ 10 |

Answer `false`. Checking only parents against children would pass this tree: 6 < 15 is fine locally. The range carries 10's limit down two levels.

**`[5, 3, 8]`** — 3 must be below 5, it is; 8 must be above 5, it is. Answer `true`.
:::

::: The Swift trap
**`Int.min` and `Int.max` as "no limit" work by accident here, and break at the edge.** The common version starts with `check(root, low: Int.min, high: Int.max)`. In Swift that happens to pass LeetCode, because Swift's `Int` is 64-bit and the values are 32-bit, so no node can equal the sentinels. But the code now says something false — a tree holding `Int.min` would be rejected, since `Int.min <= Int.min` — and the "fix" of widening to `Int.min - 1` doesn't exist: Swift traps on overflow instead of wrapping. Optional bounds say exactly what you mean, and `if let low, node.value <= low` makes them as short as the sentinel version.
:::

::: What they ask next
- **"Do it with an in-order walk instead."** → An in-order walk of a valid BST is strictly increasing: walk it (iteratively, with a stack) keeping the previous value as an `Int?`, and fail as soon as a value isn't larger than the previous one.
- **"Duplicates are allowed in the right branch."** → A value may now equal a lower limit: fail on `node.value < low` instead of `<=`, and keep `node.value >= high` as a failure, since the left branch must stay strictly smaller.
- **"Two nodes of a valid BST were swapped; fix it."** → In-order, the sequence has one or two places where it goes down; the first larger value and the last smaller value are the swapped pair. Swap their values back.
:::
