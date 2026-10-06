---
title: 33 · Linked List Cycle
summary: Decide whether following the links of a list from its first node ever leads back to a node already visited.
group: Linked list
minutes: 15
sources:
- LeetCode 141 · Linked List Cycle | https://leetcode.com/problems/linked-list-cycle/
- Swift standard library · ObjectIdentifier | https://developer.apple.com/documentation/swift/objectidentifier
---

*Easy · G*

You get the first node of a singly linked list. Normally the last node links to nothing, but in some lists the last node links back to an earlier node, so following the links goes round forever. Return whether the list has such a loop. You only get the first node: where the loop starts, if there is one, is not given to you.

| Values | Last node links to | Answer |
|---|---|---|
| `3 → 8 → 1 → 6` | the node at index 1 (the 8) | `true` |
| `5 → 5` | the node at index 0 | `true` |
| `2` | nothing | `false` |

Constraints that matter: up to 10,000 nodes, and values repeat, so a value tells you nothing about which node you're on. The target is O(n) time with O(1) extra memory.

The tests describe a list as its values plus the index the last node links back to, with −1 for no loop, and build it inside the test.

::: Starter code and tests
In an Xcode test target:

```swift
import Testing

struct LinkedListCycleTests {

    @Test(arguments: [
        ([3, 8, 1, 6], 1, true),
        ([5, 5], 0, true),
        ([2], -1, false),
    ])
    func reportsWhetherTheLastNodeLinksBack(list: [Int], cyclePosition: Int, expected: Bool) {
        let head = makeList(list)
        let tail = linkTail(of: head, to: cyclePosition)
        #expect(hasCycle(head) == expected)
        tail?.next = nil    // break the loop so ARC can free the nodes
    }

    // MARK: - Privates
    private func hasCycle(_ head: ListNode?) -> Bool {
        false
    }
}

private final class ListNode {
    var value: Int
    var next: ListNode?
    init(_ value: Int, _ next: ListNode? = nil) { self.value = value; self.next = next }
}

private func makeList(_ values: [Int]) -> ListNode? {
    var head: ListNode?
    for value in values.reversed() { head = ListNode(value, head) }
    return head
}

/// Links the last node to the node at `position` (−1: no loop) and returns the last node.
private func linkTail(of head: ListNode?, to position: Int) -> ListNode? {
    guard position >= 0 else { return nil }
    var nodes: [ListNode] = []
    var node = head
    while let current = node { nodes.append(current); node = current.next }
    nodes.last?.next = nodes[position]
    return nodes.last
}
```

In a playground:

```swift
final class ListNode {
    var value: Int
    var next: ListNode?
    init(_ value: Int, _ next: ListNode? = nil) { self.value = value; self.next = next }
}

func makeList(_ values: [Int]) -> ListNode? {
    var head: ListNode?
    for value in values.reversed() { head = ListNode(value, head) }
    return head
}

/// Links the last node to the node at `position` (−1: no loop) and returns the last node.
func linkTail(of head: ListNode?, to position: Int) -> ListNode? {
    guard position >= 0 else { return nil }
    var nodes: [ListNode] = []
    var node = head
    while let current = node { nodes.append(current); node = current.next }
    nodes.last?.next = nodes[position]
    return nodes.last
}

func hasCycle(_ head: ListNode?) -> Bool {
    false // your solution
}

let cases: [([Int], Int, Bool)] = [
    ([3, 8, 1, 6], 1, true),
    ([5, 5], 0, true),
    ([2], -1, false),
]
for (list, cyclePosition, expected) in cases {
    let head = makeList(list)
    let tail = linkTail(of: head, to: cyclePosition)
    let got = hasCycle(head)
    tail?.next = nil
    print(got == expected ? "PASS" : "FAIL", list, cyclePosition, "→", got, "expected", expected)
}
```
:::

::: Pattern and cue
**Fast and slow pointers (Floyd's cycle detection).** The cue is *"cycle"* or *"loops back"* in a linked list, plus *"constant memory"*. Two walkers at different speeds: on a straight line the fast one reaches the end; on a loop it catches the slow one from behind.
:::

::: Approach
Send two walkers from the first node. The slow one moves one node per step, the fast one two. If the list has an end, the fast walker reaches it and you answer no. If the list loops, both walkers end up going round the loop, and each step the fast one gains exactly one node on the slow one, so the gap closes one at a time and they must land on the same node — they can't jump over each other. Landing on the same node means yes.

Time O(n): the fast walker reaches the end in n/2 steps, or, once both are in the loop, catches up within one lap. Space O(1): two references.
:::

::: Swift solution
```swift
func hasCycle(_ head: ListNode?) -> Bool {
    var slow = head
    var fast = head
    while let next = fast?.next {
        slow = slow?.next
        fast = next.next
        if slow === fast { return true }
    }
    return false
}
```

`while let next = fast?.next` stops as soon as the fast walker is either on the last node or past it, so `next.next` is always safe. `===` asks "the same node", which is what the question is about.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, five more (empty list, a single node linking to itself, two nodes with no loop, a loop back to the first of 10,000 nodes, a loop at the last node), and 2,000 random lists with a random loop position or none, checked against a `Set<ObjectIdentifier>` walk.
:::

::: Walk it through
**`3 → 8 → 1 → 6`, the 6 links back to the 8**

| Step | Slow on | Fast on | Same node? |
|---|---|---|---|
| start | 3 | 3 | — |
| 1 | 8 | 1 | no |
| 2 | 1 | 8 (6 → back to 8) | no |
| 3 | 6 | 6 | yes → `true` |

**`2`, no loop** — `fast?.next` is nothing on the first check, so the loop never runs: `false`.
:::

::: The Swift trap
**`==` doesn't compile on nodes, and a looped list leaks.** `ListNode` isn't `Equatable`, so `slow == fast` is a compile error; the identity operator `===` is the one you want, since two nodes can hold the same value. The hash-set answer has the same snag: `Set<ListNode>` needs `Hashable`, so store `ObjectIdentifier(node)` instead. And a list that loops is a strong reference cycle: ARC will never free it, in a test or in an app. That's why the test sets `tail?.next = nil` after the check.
:::

::: What they ask next
- **"Return the node where the loop starts."** → After the walkers meet, start one again from the head; move both one step at a time; they meet at the loop's first node.
- **"How long is the loop?"** → After they meet, hold one still and count steps until the other comes back to it.
- **"Without the pointer trick?"** → Walk once, putting each `ObjectIdentifier(node)` in a set; a repeat means a loop. O(n) memory instead of O(1).
:::
