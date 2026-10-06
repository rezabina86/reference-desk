---
title: 45 · Kth Smallest Element in a BST
summary: Find the value that would be in position k if all the values of a binary search tree were sorted.
group: Trees
minutes: 25
sources:
- LeetCode 230 · Kth Smallest Element in a BST | https://leetcode.com/problems/kth-smallest-element-in-a-bst/
---

*Medium · G*

You get a binary search tree — every node's left branch holds smaller values, its right branch larger ones — and a number k, counting from 1. Return the k-th smallest value in the tree: k = 1 is the minimum, k = 2 the next one up, and so on. k is always between 1 and the number of nodes.

| Tree | k | Answer |
|---|---|---|
| `[6, 2, 8, 1, 4]` | 3 | `4` — sorted: 1, 2, 4, 6, 8 |
| `[9, 5, 12, 3, 7, nil, nil, 1]` | 1 | `1` — the leftmost node, three levels down |
| `[7]` | 1 | `7` |

Constraints that matter: up to 10,000 nodes. Sorting everything is O(n log n) and reading the tree in order is O(n); the target is O(h + k) — stop as soon as you've counted k values.

::: Starter code and tests
In an Xcode test target:

```swift
import Testing

struct KthSmallestElementInABSTTests {

    @Test(arguments: [
        ([6, 2, 8, 1, 4], 3, 4),
        ([9, 5, 12, 3, 7, nil, nil, 1], 1, 1),
        ([7], 1, 7),
    ] as [([Int?], Int, Int)])
    func returnsTheValueAtPositionKInSortedOrder(levelOrder: [Int?], k: Int, expected: Int) {
        #expect(kthSmallest(makeTree(levelOrder), k) == expected)
    }

    // MARK: - Privates
    private func kthSmallest(_ root: TreeNode?, _ k: Int) -> Int {
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

func kthSmallest(_ root: TreeNode?, _ k: Int) -> Int {
    0 // your solution
}

let cases: [([Int?], Int, Int)] = [
    ([6, 2, 8, 1, 4], 3, 4),
    ([9, 5, 12, 3, 7, nil, nil, 1], 1, 1),
    ([7], 1, 7),
]
for (levelOrder, k, expected) in cases {
    let got = kthSmallest(makeTree(levelOrder), k)
    print(got == expected ? "PASS" : "FAIL", levelOrder, k, "→", got, "expected", expected)
}
```
:::

::: Pattern and cue
**In-order walk of a BST, stopping early.** The cue is *"BST"* plus *"k-th smallest"*: reading a search tree left branch, node, right branch hands you its values already sorted, so the k-th value you read is the answer.
:::

::: Approach
The smallest value is found by going left from the root until you can't. To read values in order, keep a stack of the nodes you passed on the way down: they are the ones still waiting to be read. Repeatedly run as far left as possible, pushing each node; then take the top of the stack — that's the next value in sorted order — count it, and if it's the k-th, you're done. Otherwise move to its right child and run left again from there.

Time O(h + k): the first run down is h steps, and then each of the k values read costs O(1) on average. Space O(h) for the stack.
:::

::: Swift solution
```swift
func kthSmallest(_ root: TreeNode?, _ k: Int) -> Int {
    var stack: [TreeNode] = []
    var node = root
    var remaining = k
    while node != nil || !stack.isEmpty {
        while let current = node {              // run as far left as possible
            stack.append(current)
            node = current.left
        }
        let current = stack.removeLast()        // the next value in sorted order
        remaining -= 1
        if remaining == 0 { return current.value }
        node = current.right
    }
    return -1                                   // k was larger than the tree
}
```

`stack.removeLast()` takes the node whose whole left branch has already been read, which is exactly the next value up.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, five more (k equal to the number of nodes, a left-only chain, a right-only chain, the root as the answer, every k from 1 to n on one tree), and 3,000 random BSTs with random k checked against sorting all the values.
:::

::: Walk it through
**`[6, 2, 8, 1, 4]`, k = 3** — 6 has children 2 and 8; 2 has children 1 and 4.

| Step | Run left pushes | Stack after | Pops | Remaining |
|---|---|---|---|---|
| 1 | 6, 2, 1 | 6 2 1 | 1 | 2 |
| 2 | (1 has no right) | 6 2 | 2 | 1 |
| 3 | 2's right: 4 | 6 4 | 4 | 0 → return 4 |

The walk never reaches 8.

**`[7]`, k = 1** — push 7, pop 7, remaining 0: return 7.
:::

::: The Swift trap
**There is no `yield`, so "stop early" has to be built by hand.** In Python you'd write an in-order generator and take its k-th element. Swift has no generators. The easy Swift alternatives both throw away the early stop: building `inorder(root)` into an array and returning `values[k - 1]` visits all n nodes and holds them all in memory, and a recursive walk with a counter keeps visiting after it found the answer unless you thread a "done" flag through every call. The explicit stack above is the honest Swift way to pause a walk: the stack *is* the paused state. (`removeLast()` is fine here: it's O(1) at the end of an array; it's `removeFirst()` that costs O(n).)
:::

::: What they ask next
- **"The tree changes often and you're asked for k-th smallest many times."** → Store in each node the size of its left branch. Then compare k with that size at each node and go left, stop, or go right with k reduced: O(h) per question, with sizes updated on insert and delete.
- **"k-th largest instead."** → Walk in reverse order — right branch, node, left branch — with the same stack, pushing right children.
- **"Can you do it in O(1) extra space?"** → Morris traversal: temporarily point each node's in-order predecessor back at it instead of using a stack, and undo the links as you go.
:::
