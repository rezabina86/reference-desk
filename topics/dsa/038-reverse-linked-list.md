---
title: 31 · Reverse Linked List
summary: Turn a chain of nodes around so the last node comes first, by changing the links rather than the values.
group: Linked list
minutes: 15
sources:
- LeetCode 206 · Reverse Linked List | https://leetcode.com/problems/reverse-linked-list/
---

*Easy · G*

You get the first node of a singly linked list: each node holds a number and a link to the next node, and the last node links to nothing. Reverse the list by changing the links, so the old last node becomes the first, and return the new first node. The values stay in their nodes; only the arrows turn around. An empty list stays empty.

| List | Answer |
|---|---|
| `3 → 1 → 4 → 1 → 5` | `5 → 1 → 4 → 1 → 3` |
| `7` | `7` |
| empty | empty |

Constraints that matter: up to 5,000 nodes. The target is one pass, O(n) time, with O(1) extra memory — no copying the values into an array.

::: Starter code and tests
In an Xcode test target:

```swift
import Testing

struct ReverseLinkedListTests {

    @Test(arguments: [
        ([3, 1, 4, 1, 5], [5, 1, 4, 1, 3]),
        ([7], [7]),
        ([], []),
    ])
    func returnsTheNodesInTheOppositeOrder(list: [Int], expected: [Int]) {
        #expect(values(of: reverseList(makeList(list))) == expected)
    }

    // MARK: - Privates
    private func reverseList(_ head: ListNode?) -> ListNode? {
        nil
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

private func values(of head: ListNode?) -> [Int] {
    var result: [Int] = []
    var node = head
    while let current = node { result.append(current.value); node = current.next }
    return result
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

func values(of head: ListNode?) -> [Int] {
    var result: [Int] = []
    var node = head
    while let current = node { result.append(current.value); node = current.next }
    return result
}

func reverseList(_ head: ListNode?) -> ListNode? {
    nil // your solution
}

let cases: [([Int], [Int])] = [
    ([3, 1, 4, 1, 5], [5, 1, 4, 1, 3]),
    ([7], [7]),
    ([], []),
]
for (list, expected) in cases {
    let got = values(of: reverseList(makeList(list)))
    print(got == expected ? "PASS" : "FAIL", list, "→", got, "expected", expected)
}
```
:::

::: Pattern and cue
**Pointer rewiring with three references.** The cue is *"reverse the list"* together with *"linked list"*: the nodes don't move, every arrow flips, and the only danger is losing the part of the list you haven't reached yet.
:::

::: Approach
Walk the list from the front, carrying two things: the node you're standing on, and the node you just left (nothing, at the start). At each node, first remember the node after it, because you're about to cut that link. Then point the current node back at the one you just left. Step forward: the current node becomes "the one you just left", and the remembered node becomes the current one. When you step off the end, the last node you left is the new first node.

Time O(n): each node is visited once. Space O(1): three references, whatever the length.
:::

::: Swift solution
```swift
func reverseList(_ head: ListNode?) -> ListNode? {
    var previous: ListNode? = nil
    var current = head
    while let node = current {
        let next = node.next        // save the rest before cutting it off
        node.next = previous
        previous = node
        current = next
    }
    return previous
}
```

The order inside the loop is the whole problem: `let next = node.next` has to come before `node.next = previous`, or the rest of the list is gone. `ListNode` is the class from the starter code.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, four more (two nodes, repeated values, negative values, a 5,000-node list), reversing twice gives back the original, the recursive version from The Swift trap on the same examples and a 2,000-node list, and 2,000 random lists checked against `Array.reversed()`.
:::

::: Walk it through
**`3 → 1 → 4 → 1 → 5`**

| Step | Node | Saved next | Link set to | Previous after | Reversed so far |
|---|---|---|---|---|---|
| 1 | 3 | 1 | nothing | 3 | `3` |
| 2 | 1 | 4 | 3 | 1 | `1 → 3` |
| 3 | 4 | 1 | 1 | 4 | `4 → 1 → 3` |
| 4 | 1 | 5 | 4 | 1 | `1 → 4 → 1 → 3` |
| 5 | 5 | nothing | 1 | 5 | `5 → 1 → 4 → 1 → 3` |

Current is now nothing, so the loop ends and `previous`, the node 5, is returned.

**Empty list** — `current` starts as `nil`, the loop never runs, and `previous` is still `nil`: an empty list comes back empty with no special case.
:::

::: The Swift trap
**The recursive version is shorter and has a hard ceiling.** This one is the usual answer to "now do it recursively":

```swift
func reverseRecursively(_ head: ListNode?) -> ListNode? {
    guard let head, let next = head.next else { return head }
    let newHead = reverseRecursively(next)
    next.next = head
    head.next = nil
    return newHead
}
```

It uses one stack frame per node, and Swift doesn't promise tail-call elimination (this call isn't in tail position anyway). Measured on Swift 6.4 in a debug build: on the 8 MB main thread it crashed between 30,000 and 40,000 nodes, but on a background thread's 512 KB stack — which is where Swift Testing runs your tests, and where GCD runs your work — it crashed below 3,000 nodes, inside this problem's own 5,000-node limit. A release build lasted to 5,000 and crashed by 6,000. There is no error to catch: the process dies. Write it when asked, say the limit out loud, and ship the loop.
:::

::: What they ask next
- **"Now recursively."** → Reverse the rest first, then make the node after you point back at you and cut your own link; O(n) stack, as above.
- **"Reverse only the part from position left to position right."** → Dummy head, walk to the node before `left`, reverse `right − left + 1` nodes with the same loop, then reconnect both cut ends.
- **"Reverse in groups of k, leaving a short tail as it is."** → Count k nodes ahead; if there are k, reverse that group with the same loop and link the previous group's tail to it; repeat.
:::
