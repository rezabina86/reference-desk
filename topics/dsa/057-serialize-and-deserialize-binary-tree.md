---
title: 49 · Serialize and Deserialize Binary Tree
summary: Turn a binary tree into a single string and back again, so that the rebuilt tree is identical to the original.
group: Trees
minutes: 30
sources:
- LeetCode 297 · Serialize and Deserialize Binary Tree | https://leetcode.com/problems/serialize-and-deserialize-binary-tree/
- Swift standard library · split(separator:maxSplits:omittingEmptySubsequences:) | https://developer.apple.com/documentation/swift/collection/split(separator:maxsplits:omittingemptysubsequences:)
---

*Hard · optional · G*

**Optional.** Above the bar most German loops set; do it if the topic's mediums went well.

Write two functions. The first takes the root of a binary tree and returns a string. The second takes such a string and returns a tree. Turning any tree into a string and back must give a tree with exactly the same shape and values. The format is yours to choose; the only requirement is the round trip. Values can be negative and repeated, and the tree can be empty.

| Tree | After a round trip |
|---|---|
| `[1, 2, 3, nil, nil, 4, 5]` | `[1, 2, 3, nil, nil, 4, 5]` |
| `[-7, nil, 12]` | `[-7, nil, 12]` — negative and two-digit values, one missing child |
| `[]` | `[]` |

Constraints that matter: up to 10,000 nodes, values from −1,000 to 1,000. Both directions should be O(n).

::: Starter code and tests
In an Xcode test target:

```swift
import Testing

struct SerializeAndDeserializeBinaryTreeTests {

    @Test(arguments: [
        [1, 2, 3, nil, nil, 4, 5],
        [-7, nil, 12],
        [],
    ] as [[Int?]])
    func roundTripGivesBackTheSameTree(levelOrder: [Int?]) {
        let codec = Codec()
        let copy = codec.deserialize(codec.serialize(makeTree(levelOrder)))
        #expect(levelOrderValues(copy) == levelOrder)
    }

    // MARK: - Privates
    private struct Codec {
        func serialize(_ root: TreeNode?) -> String {
            ""
        }

        func deserialize(_ data: String) -> TreeNode? {
            nil
        }
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

struct Codec {
    func serialize(_ root: TreeNode?) -> String {
        "" // your solution
    }

    func deserialize(_ data: String) -> TreeNode? {
        nil // your solution
    }
}

let cases: [[Int?]] = [
    [1, 2, 3, nil, nil, 4, 5],
    [-7, nil, 12],
    [],
]
let codec = Codec()
for levelOrder in cases {
    let text = codec.serialize(makeTree(levelOrder))
    let got = levelOrderValues(codec.deserialize(text))
    print(got == levelOrder ? "PASS" : "FAIL", levelOrder, "→", text, "→", got)
}
```
:::

::: Pattern and cue
**Pre-order walk with markers for missing children.** The cue is *"turn it into a string and back"*. A single listing of values can't rebuild a tree (problem 47 needed two), but a pre-order listing that also writes down every **empty** spot can: when you read it back, the markers tell you exactly where each branch ends.
:::

::: Approach
To write the tree: visit it in pre-order — the node, then its left branch, then its right branch — and write each value, writing a `#` wherever a child is missing. Separate the pieces with commas. To read it back: split the string at the commas and keep a cursor. Read the next piece: if it's `#`, this spot is empty. Otherwise make a node with that value, then build its left branch by reading on, then its right branch the same way — the same order the pieces were written in.

Time O(n) each way: every node and every empty spot (there are n + 1 of those) is written and read once. Space O(n) for the string and the pieces, plus O(h) for the recursion.
:::

::: Swift solution
```swift
struct Codec {
    func serialize(_ root: TreeNode?) -> String {
        var pieces: [String] = []
        func write(_ node: TreeNode?) {
            guard let node else { pieces.append("#"); return }
            pieces.append(String(node.value))
            write(node.left)
            write(node.right)
        }
        write(root)
        return pieces.joined(separator: ",")
    }

    func deserialize(_ data: String) -> TreeNode? {
        let pieces = data.split(separator: ",")
        var index = 0
        func read() -> TreeNode? {
            let piece = pieces[index]
            index += 1
            guard let value = Int(piece) else { return nil }   // "#" is not a number
            let node = TreeNode(value)
            node.left = read()
            node.right = read()
            return node
        }
        return read()
    }
}
```

`Int(piece)` parses the `Substring` directly, negatives included, and returns `nil` for `#` — so one `guard` both reads the value and spots the marker.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, five more (a single node, a left-only chain, a right-only chain, repeated values, the exact string written for `[1, 2, 3, nil, nil, 4, 5]`), and 3,000 random trees with values from −1,000 to 1,000 checked for an identical level order after the round trip.
:::

::: Walk it through
**`[1, 2, 3, nil, nil, 4, 5]`** — 1 has children 2 and 3; 3 has children 4 and 5.

Writing, in pre-order: 1, then 2 with its two empty spots, then 3, then 4 with two empty spots, then 5 with two:

`1,2,#,#,3,4,#,#,5,#,#`

Reading it back:

| Piece | Action |
|---|---|
| 1 | new node 1; read its left |
| 2 | new node 2; read its left |
| # | 2's left is empty; read 2's right |
| # | 2's right is empty; 2 is done, back to 1's right |
| 3 | new node 3; read its left |
| 4, #, # | 3's left is 4, a leaf |
| 5, #, # | 3's right is 5, a leaf |

**`[]`** — writing an empty tree produces `#`. Reading `#`: `Int("#")` is `nil`, so `read()` returns `nil`, the empty tree.
:::

::: The Swift trap
**`split` drops empty pieces, so an empty field can't be your "missing" marker.** A natural format writes nothing for a missing child: `"1,,2"`. But `split(separator:)` defaults to `omittingEmptySubsequences: true`, so `"1,,2".split(separator: ",")` is `["1", "2"]` — the gap that meant "no child here" is gone, and the rebuilt tree is a different shape with no error. Use a visible marker like `#`, as above, or pass `omittingEmptySubsequences: false` and say why. Related: `Int(piece)` works on the `Substring` pieces without converting each one to a `String` first; converting is an extra copy per piece.
:::

::: What they ask next
- **"Make the string shorter."** → Drop the trailing `#` markers, or write level order and stop at the last real node; or write each value as fixed-width bytes instead of decimal text with commas.
- **"It's a binary search tree — can you skip the markers?"** → Yes: pre-order alone determines a BST, because each value's position is forced by the ordering. Rebuild by passing a (low, high) range down, as in validating a BST.
- **"Avoid recursion for a 10,000-deep tree."** → Write and read in level order with an index-based queue instead: write each queued node's two children (or `#`), and read them back two pieces per node.
:::
