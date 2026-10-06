---
title: Trees — the idea
summary: How to walk a tree depth-first and level by level, what a binary search tree promises, and where Swift's recursion runs out of stack.
group: Trees
minutes: 10
sources:
- Swift Programming Language · Classes and Structures (reference types) | https://docs.swift.org/swift-book/documentation/the-swift-programming-language/classesandstructures/
- Swift Programming Language · Automatic Reference Counting | https://docs.swift.org/swift-book/documentation/the-swift-programming-language/automaticreferencecounting/
---

A binary tree is a set of nodes where each node holds a value and points to at most two children, a left one and a right one. One node, the root, has no parent; every other node has exactly one. Almost every tree problem in an interview is a walk over those nodes, done in one of two orders, plus one small decision made at each node.

## When to reach for it

- The input *is* a tree: "given the root of a binary tree".
- Words about shape: **depth**, **height**, **level**, **leaf**, **path from the root**.
- Words about family: **ancestor**, **descendant**, **subtree**, **parent**.
- **"Binary search tree"** or **BST**: an ordering promise you are expected to use.
- "Level by level", "row by row", "closest to the root first" — that is breadth-first.
- Turning a tree into something flat (a list, a string) and back.

## The idea in plain words

Think of a family tree drawn on paper. You can read it two ways.

**Depth-first** is how you'd trace one family line: go down to a grandchild, then a great-grandchild, all the way to someone with no children, then back up one generation and try the next child. You finish a whole branch before you start the next one. A computer remembers "where to come back to" on a stack — either the one the language keeps for function calls (recursion), or an array you manage yourself.

**Breadth-first** is how you'd read the chart row by row: first the grandparents, then all their children, then all the grandchildren. You need a waiting line — a queue — of people you've seen but not yet read out.

The small decision at each node is usually one of two kinds. Either you **pass something down** ("everything below me must be larger than 10"), or you **hand something back up** ("my branch is 4 levels deep"). Most tree solutions are three lines: handle the empty tree, ask both children, combine their answers.

A **binary search tree** adds one promise: for every node, everything in its left branch is smaller and everything in its right branch is larger. Read it left-branch, node, right-branch (an *in-order* walk) and the values come out sorted. And to find a value you only ever need to go one way at each node, like a guessing game of "higher or lower".

## The template in Swift

```swift
final class TreeNode {
    var value: Int
    var left: TreeNode?
    var right: TreeNode?
    init(_ value: Int, _ left: TreeNode? = nil, _ right: TreeNode? = nil) {
        self.value = value; self.left = left; self.right = right
    }
}

// Depth-first, recursive, handing a value back up: the number of levels.
func height(_ node: TreeNode?) -> Int {
    guard let node else { return 0 }                         // the empty tree
    return 1 + max(height(node.left), height(node.right))    // ask both children, combine
}

// Depth-first, iterative: your own stack instead of the call stack (pre-order).
func preorder(_ root: TreeNode?) -> [Int] {
    var result: [Int] = []
    var stack: [TreeNode] = []
    if let root { stack.append(root) }
    while let node = stack.popLast() {                       // popLast is O(1)
        result.append(node.value)
        if let right = node.right { stack.append(right) }    // pushed first, so visited last
        if let left = node.left { stack.append(left) }
    }
    return result
}

// Depth-first, in-order (left, node, right): sorted output on a BST.
func inorder(_ root: TreeNode?) -> [Int] {
    var result: [Int] = []
    var stack: [TreeNode] = []
    var node = root
    while node != nil || !stack.isEmpty {
        while let current = node { stack.append(current); node = current.left }  // run down-left
        let current = stack.removeLast()
        result.append(current.value)
        node = current.right
    }
    return result
}

// Breadth-first: a queue as an array plus a read position, never removeFirst().
func breadthFirst(_ root: TreeNode?) -> [Int] {
    guard let root else { return [] }
    var queue = [root]
    var head = 0                                             // the next node to take out
    while head < queue.count {
        let node = queue[head]
        head += 1
        if let left = node.left { queue.append(left) }
        if let right = node.right { queue.append(right) }
    }
    return queue.map(\.value)                                // the queue *is* the visit order
}

// BST lookup: one direction per node, no recursion needed.
func search(_ root: TreeNode?, _ target: Int) -> TreeNode? {
    var node = root
    while let current = node {
        if target == current.value { return current }
        node = target < current.value ? current.left : current.right
    }
    return nil
}
```

## Variations

1. **Hand a value up (post-order).** Ask both children, then decide: depth, same-tree, lowest common ancestor, the maximum path sum. The trick in the harder ones is that what you *return* to your parent differs from what you *record* as the answer.
2. **Pass a constraint down (pre-order).** Carry bounds or a running total into the children: validating a BST with a low and a high bound.
3. **Level by level (breadth-first).** Process the queue one whole level at a time to group nodes by depth.
4. **Use the BST ordering.** Walk one side only (lowest common ancestor in a BST), or walk in order and stop early (k-th smallest).
5. **Flatten and rebuild.** Turn a tree into a sequence and back: building from pre-order plus in-order, serialising to a string.

## Complexity

Every walk above touches each node once: **O(n) time**. The extra space is whatever holds the "come back to" list. For depth-first that is the height h of the tree — **O(h)**, which is O(log n) when the tree is balanced and O(n) when it degenerates into a chain. For breadth-first it is the widest level, up to about n/2 nodes on the bottom row of a full tree. A BST lookup is O(h): fast on a balanced tree, no better than a list on a chain.

## Swift traps

- **Recursion runs out of stack sooner than you think, and freeing a tree recurses too.** Swift does not turn tail calls into loops, so every recursive call takes a stack frame. Swift Testing runs tests on secondary threads with a 512 KB stack: in a debug build on Swift 6.4, the recursive `height` above crashed on a chain only 3,000 nodes deep (2,000 was fine). And ARC frees a tree by releasing the root, which releases its child, which releases its child — the same chain of nested calls — so merely *dropping* a 3,000-deep chain in a test crashed the same way, even with no recursion of yours. On the main thread (8 MB) a debug build managed 10,000 and crashed by 50,000. LeetCode allows up to 10⁴ or 10⁵ nodes, so say out loud: "recursive is O(h) stack; on a degenerate tree I'd switch to an explicit stack."
- **There is no `Deque` in the standard library.** `Array.removeFirst()` shifts every remaining element, O(n), which turns a BFS into O(n²). Use an array with a `head` index (above), or swap whole level arrays. `swift-collections` has a `Deque`, but it won't exist in a shared interview editor.
- **`TreeNode` is a class.** Two trees with the same values are different objects, so `==` doesn't compile unless you add `Equatable`, and `===` asks "same object", not "same values". And changing a node changes it for every variable that refers to it: a function that "returns an inverted tree" usually has rewired the caller's tree as well.
- **Optionals everywhere.** `guard let node else { return … }` at the top of a recursive function is the empty-tree case; `while let current = node` is the idiomatic way to walk down one side.

## The problems in this topic

- [38 · Invert Binary Tree](#/dsa/invert-binary-tree) — Easy
- [39 · Maximum Depth of Binary Tree](#/dsa/maximum-depth-of-binary-tree) — Easy
- [40 · Same Tree](#/dsa/same-tree) — Easy
- [41 · Subtree of Another Tree](#/dsa/subtree-of-another-tree) — Easy
- [42 · Lowest Common Ancestor of a Binary Search Tree](#/dsa/lowest-common-ancestor-of-a-binary-search-tree) — Medium
- [43 · Binary Tree Level Order Traversal](#/dsa/binary-tree-level-order-traversal) — Medium
- [44 · Validate Binary Search Tree](#/dsa/validate-binary-search-tree) — Medium
- [45 · Kth Smallest Element in a BST](#/dsa/kth-smallest-element-in-a-bst) — Medium
- [46 · Lowest Common Ancestor of a Binary Tree](#/dsa/lowest-common-ancestor-of-a-binary-tree) — Medium
- [47 · Construct Binary Tree from Preorder and Inorder Traversal](#/dsa/construct-binary-tree-from-preorder-and-inorder-traversal) — Medium
- [48 · Binary Tree Maximum Path Sum](#/dsa/binary-tree-maximum-path-sum) — Hard, optional
- [49 · Serialize and Deserialize Binary Tree](#/dsa/serialize-and-deserialize-binary-tree) — Hard, optional
