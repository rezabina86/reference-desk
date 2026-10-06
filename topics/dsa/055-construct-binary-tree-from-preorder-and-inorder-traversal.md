---
title: 47 · Construct Binary Tree from Preorder and Inorder Traversal
summary: Rebuild a binary tree from two listings of its values, one written root-first and one written left-to-right.
group: Trees
minutes: 25
sources:
- LeetCode 105 · Construct Binary Tree from Preorder and Inorder Traversal | https://leetcode.com/problems/construct-binary-tree-from-preorder-and-inorder-traversal/
- Swift standard library · ArraySlice | https://developer.apple.com/documentation/swift/arrayslice
---

*Medium · G*

You get two lists of the same tree's values. The first is **pre-order**: each node is written before its left branch, which comes before its right branch. The second is **in-order**: each node's left branch is written first, then the node, then its right branch. Rebuild the tree and return its root. All values are different, which is what makes the answer unique.

| Pre-order | In-order | Answer (level order) |
|---|---|---|
| `[4, 2, 1, 3, 6]` | `[1, 2, 3, 4, 6]` | `[4, 2, 6, 1, 3]` |
| `[1, 2, 3]` | `[3, 2, 1]` | `[1, 2, nil, 3]` — every node hangs to the left |
| `[1]` | `[1]` | `[1]` |

Constraints that matter: up to 3,000 nodes, values all different. Searching the in-order list for each root makes it O(n²); the target is O(n).

::: Starter code and tests
In an Xcode test target:

```swift
import Testing

struct ConstructBinaryTreeFromPreorderAndInorderTraversalTests {

    @Test(arguments: [
        ([4, 2, 1, 3, 6], [1, 2, 3, 4, 6], [4, 2, 6, 1, 3]),
        ([1, 2, 3], [3, 2, 1], [1, 2, nil, 3]),
        ([1], [1], [1]),
    ] as [([Int], [Int], [Int?])])
    func rebuildsTheTreeBothListingsDescribe(preorder: [Int], inorder: [Int], expected: [Int?]) {
        #expect(levelOrderValues(buildTree(preorder, inorder)) == expected)
    }

    // MARK: - Privates
    private func buildTree(_ preorder: [Int], _ inorder: [Int]) -> TreeNode? {
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

func buildTree(_ preorder: [Int], _ inorder: [Int]) -> TreeNode? {
    nil // your solution
}

let cases: [([Int], [Int], [Int?])] = [
    ([4, 2, 1, 3, 6], [1, 2, 3, 4, 6], [4, 2, 6, 1, 3]),
    ([1, 2, 3], [3, 2, 1], [1, 2, nil, 3]),
    ([1], [1], [1]),
]
for (preorder, inorder, expected) in cases {
    let got = levelOrderValues(buildTree(preorder, inorder))
    print(got == expected ? "PASS" : "FAIL", preorder, inorder, "→", got, "expected", expected)
}
```
:::

::: Pattern and cue
**Divide and conquer on two traversals.** The cue is *"pre-order and in-order"* together. Pre-order tells you **who** the root is (always first); in-order tells you **what's on each side** of it (everything before the root is the left branch, everything after is the right). Split, and each side is the same problem, smaller.
:::

::: Approach
The first pre-order value is the root. Find that value in the in-order list: everything to its left belongs to the left branch, everything to its right to the right branch, and the counts tell you how many nodes each branch has. In pre-order, the root is followed by the whole left branch and then the whole right branch, so if you keep a cursor that moves through pre-order one value at a time — building the left branch fully before the right — the cursor always points at the next branch's root. To avoid searching the in-order list each time, first record each value's position in it in a dictionary.

Time O(n): the dictionary is built once, and each node is created once with an O(1) lookup. Space O(n) for the dictionary, plus O(h) for the recursion.
:::

::: Swift solution
```swift
func buildTree(_ preorder: [Int], _ inorder: [Int]) -> TreeNode? {
    var positionInInorder: [Int: Int] = [:]
    for (position, value) in inorder.enumerated() { positionInInorder[value] = position }
    var next = 0                                     // the pre-order cursor

    // Builds the branch whose values fill inorder[low..<high].
    func build(_ low: Int, _ high: Int) -> TreeNode? {
        guard low < high else { return nil }
        let value = preorder[next]
        next += 1
        let root = TreeNode(value)
        let middle = positionInInorder[value]!
        root.left = build(low, middle)               // left first: pre-order lists it first
        root.right = build(middle + 1, high)
        return root
    }
    return build(0, inorder.count)
}
```

The order of the two recursive calls is load-bearing: the shared cursor `next` is consumed by the left branch before the right one, exactly as pre-order lists them.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, four more (empty lists, a right-leaning chain, a full tree of three levels, negative values), and 3,000 random trees with distinct values: list them both ways, rebuild, and compare the level order with the original.
:::

::: Walk it through
**Pre-order `[4, 2, 1, 3, 6]`, in-order `[1, 2, 3, 4, 6]`** — positions in in-order: 1→0, 2→1, 3→2, 4→3, 6→4.

| Call `build(low, high)` | Root (cursor) | Its in-order position | Left gets | Right gets |
|---|---|---|---|---|
| (0, 5) | 4 | 3 | (0, 3) | (4, 5) |
| (0, 3) | 2 | 1 | (0, 1) | (2, 3) |
| (0, 1) | 1 | 0 | (0, 0) → nil | (1, 1) → nil |
| (2, 3) | 3 | 2 | nil | nil |
| (4, 5) | 6 | 4 | nil | nil |

4 has children 2 and 6, and 2 has children 1 and 3: level order `[4, 2, 6, 1, 3]`.

**`[1, 2, 3]` with `[3, 2, 1]`** — 1 is at in-order position 2, so everything (3, 2) is on its left and nothing on its right. Then 2 is at position 1, with 3 on its left. A left-leaning chain: `[1, 2, nil, 3]`.
:::

::: The Swift trap
**Recursing on slices crashes on the second level.** The textbook version passes sub-arrays: `build(Array(preorder[1...k]), Array(inorder[..<k]))`, which copies O(n) per call, so people "optimise" by passing the `ArraySlice` itself. But a slice keeps the original array's indices: `inorder[3...]` starts at index 3, not 0. Code that reads `slice[0]` or uses `firstIndex(of:)` as a count traps with an out-of-range index, or silently reads the wrong element, one level down. Either convert with `Array(slice)` (and accept the copies), or do what the solution does: keep the original arrays and pass index bounds.
:::

::: What they ask next
- **"In-order and post-order instead."** → Post-order lists the root **last**, so run the cursor from the end backwards, and build the **right** branch before the left.
- **"Why do the values have to be different?"** → With duplicates, the root's value can appear more than once in the in-order list, so you can't tell where the left branch ends; several trees fit.
- **"Can pre-order and post-order rebuild it?"** → Not uniquely: a node with one child gives the same two listings whether the child is left or right. It works only for full trees, where every node has 0 or 2 children.
:::
