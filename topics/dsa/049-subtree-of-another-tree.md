---
title: 41 · Subtree of Another Tree
summary: Decide whether a small binary tree appears inside a bigger one as a complete branch, every descendant included.
group: Trees
minutes: 25
sources:
- LeetCode 572 · Subtree of Another Tree | https://leetcode.com/problems/subtree-of-another-tree/
---

*Easy · G*

You get two binary trees, a big one and a small one. Return `true` if some node of the big tree, together with **everything below it**, is exactly the small tree: same shape, same values. Matching only the top part isn't enough — if that node has an extra child or grandchild, it doesn't count. The big tree also counts as a subtree of itself.

| Big tree | Small tree | Answer |
|---|---|---|
| `[3, 4, 5, 1, 2]` | `[4, 1, 2]` | `true` — the branch under 4 |
| `[3, 4, 5, 1, 2, nil, nil, 0]` | `[4, 1, 2]` | `false` — the branch under 4 has an extra 0 below the 1 |
| `[1, 1]` | `[1]` | `true` — the lower 1 is a leaf; the root 1 is not |

Constraints that matter: up to 2,000 nodes in the big tree and 1,000 in the small one, both non-empty. Comparing at every node is O(n·m); that's the expected answer, with O(n + m) as the follow-up.

::: Starter code and tests
In an Xcode test target:

```swift
import Testing

struct SubtreeOfAnotherTreeTests {

    @Test(arguments: [
        ([3, 4, 5, 1, 2], [4, 1, 2], true),
        ([3, 4, 5, 1, 2, nil, nil, 0], [4, 1, 2], false),
        ([1, 1], [1], true),
    ] as [([Int?], [Int?], Bool)])
    func findsTheSmallTreeAsACompleteBranch(big: [Int?], small: [Int?], expected: Bool) {
        #expect(isSubtree(makeTree(big), makeTree(small)) == expected)
    }

    // MARK: - Privates
    private func isSubtree(_ root: TreeNode?, _ subRoot: TreeNode?) -> Bool {
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

func isSubtree(_ root: TreeNode?, _ subRoot: TreeNode?) -> Bool {
    false // your solution
}

let cases: [([Int?], [Int?], Bool)] = [
    ([3, 4, 5, 1, 2], [4, 1, 2], true),
    ([3, 4, 5, 1, 2, nil, nil, 0], [4, 1, 2], false),
    ([1, 1], [1], true),
]
for (big, small, expected) in cases {
    let got = isSubtree(makeTree(big), makeTree(small))
    print(got == expected ? "PASS" : "FAIL", big, small, "→", got, "expected", expected)
}
```
:::

::: Pattern and cue
**Depth-first, with a second depth-first check at each node.** The cue is *"a subtree … with everything below it"*: at every node of the big tree, ask problem 40's question — is the tree starting here the same tree as the small one?
:::

::: Approach
Walk every node of the big tree. At each one, compare the branch hanging from it with the small tree, position by position, the way you'd check two trees are identical. If any comparison succeeds, the answer is yes. If you run out of nodes, the answer is no. The comparison itself stops at the first difference, so most nodes are rejected after one or two steps.

Time O(n·m) in the worst case — n nodes in the big tree, each compared against up to m nodes of the small one — though typical trees fail fast. Space O(h) for the two nested recursions.
:::

::: Swift solution
```swift
func isSubtree(_ root: TreeNode?, _ subRoot: TreeNode?) -> Bool {
    guard let root else { return subRoot == nil }
    return isSameTree(root, subRoot)
        || isSubtree(root.left, subRoot)
        || isSubtree(root.right, subRoot)
}

func isSameTree(_ p: TreeNode?, _ q: TreeNode?) -> Bool {
    switch (p, q) {
    case (nil, nil):
        return true
    case let (p?, q?):
        return p.value == q.value
            && isSameTree(p.left, q.left)
            && isSameTree(p.right, q.right)
    default:
        return false
    }
}
```

`isSameTree` demands the shapes match all the way down, which is what makes the extra 0 in the second example a mismatch. `||` stops at the first branch that matches.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, five more (a tree is a subtree of itself, `[12]` against `[2]`, the match at the deepest leaf, the right values in the wrong shape, a big tree full of near-misses), the serialisation version from the follow-ups on all of them, and 3,000 random pairs checked against comparing the small tree's level-order listing with that of every node in the big one.
:::

::: Walk it through
**`[3, 4, 5, 1, 2]` and `[4, 1, 2]`**

| Node of big tree | `isSameTree` with `[4, 1, 2]` | Result |
|---|---|---|
| 3 | 3 ≠ 4 | no, try its branches |
| 4 | 4 = 4, then (1, 1) leaves match, then (2, 2) leaves match | yes |

Answer `true`; the walk never visits 5.

**`[1, 1]` and `[1]`** — at the root: 1 = 1, but the big tree's root has a left child 1 where the small tree has `nil`, so they differ. At the lower 1: both are leaves with value 1, the same tree. Answer `true`.
:::

::: The Swift trap
**The O(n + m) string trick matches `12` against `2`.** The usual follow-up is: write both trees as strings in pre-order, then ask whether the small string appears inside the big one — and Swift makes that one line, `bigString.contains(smallString)`. But without a separator *in front of* each value, the big tree `[12]` writes as `"12,#,#"` and the small tree `[2]` as `"2,#,#"`, and `contains` finds the second inside the first: `true`, wrongly. Write a separator before every value as well as after (`",12,#,#"` doesn't contain `",2,#,#"`), and always write the `#` for a missing child, or different shapes can produce the same string. Also say what `contains` costs: it's a plain search, O(n·m) in the worst case; O(n + m) needs a linear-time matcher such as KMP on top.
:::

::: What they ask next
- **"Make it O(n + m)."** → Serialise both trees in pre-order with markers for missing children and a separator before each value, then search with KMP (or compare tree hashes computed bottom-up).
- **"What if the small tree is empty?"** → An empty tree counts as a subtree of anything, and this solution already agrees: the walk reaches a missing child, where the `guard` returns `subRoot == nil`, which is `true`. Say that out loud rather than adding a special case.
- **"Count how many times it appears."** → Same walk, but add one for every node where `isSameTree` succeeds instead of stopping at the first.
:::
