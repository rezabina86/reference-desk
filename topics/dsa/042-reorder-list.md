---
title: 35 · Reorder List
summary: Rearrange a linked list in place so that it alternates first, last, second, second-to-last, and so on toward the middle.
group: Linked list
minutes: 25
sources:
- LeetCode 143 · Reorder List | https://leetcode.com/problems/reorder-list/
---

*Medium · G*

You get the first node of a singly linked list. Rearrange its nodes in place so the order becomes: the first node, then the last, then the second, then the second-to-last, and so on, until the two ends meet in the middle. Change only the links, not the values, and return nothing: the caller still holds the first node, which stays first.

| List | After reordering |
|---|---|
| `10 → 20 → 30 → 40 → 50` | `10 → 50 → 20 → 40 → 30` |
| `1 → 2 → 3 → 4` | `1 → 4 → 2 → 3` |
| `8` | `8` |

Constraints that matter: up to 50,000 nodes. You can't walk backwards in a singly linked list, so "the last node" is the hard part. Copying the nodes into an array works in O(n) memory; the target is O(n) time with O(1) extra memory.

::: Starter code and tests
In an Xcode test target:

```swift
import Testing

struct ReorderListTests {

    @Test(arguments: [
        ([10, 20, 30, 40, 50], [10, 50, 20, 40, 30]),
        ([1, 2, 3, 4], [1, 4, 2, 3]),
        ([8], [8]),
    ])
    func alternatesNodesFromTheFrontAndTheBack(list: [Int], expected: [Int]) {
        let head = makeList(list)
        reorderList(head)
        #expect(values(of: head) == expected)
    }

    // MARK: - Privates
    private func reorderList(_ head: ListNode?) {
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

func reorderList(_ head: ListNode?) {
    // your solution
}

let cases: [([Int], [Int])] = [
    ([10, 20, 30, 40, 50], [10, 50, 20, 40, 30]),
    ([1, 2, 3, 4], [1, 4, 2, 3]),
    ([8], [8]),
]
for (list, expected) in cases {
    let head = makeList(list)
    reorderList(head)
    let got = values(of: head)
    print(got == expected ? "PASS" : "FAIL", list, "→", got, "expected", expected)
}
```
:::

::: Pattern and cue
**Three list moves in a row: find the middle with fast and slow pointers, reverse the second half, weave the halves together.** The cue is *"in place"* plus an order that takes from **both ends**: in a list you can only walk forwards, so turn the back half around until its end is at its front.
:::

::: Approach
First, find the middle: one walker moves one node at a time, another two at a time; when the fast one can't go on, the slow one is at the end of the first half. Cut the list there into two halves. Second, reverse the second half, so the old last node is now its first. Third, weave: take one node from the front half, then one from the reversed back half, and repeat until the back half is used up. The front half is the same length as the back half or one node longer, so its last node ends up last.

Time O(n): each step is one pass over at most the whole list. Space O(1): a handful of references, no copies.
:::

::: Swift solution
```swift
func reorderList(_ head: ListNode?) {
    guard let head else { return }

    // 1. Middle: slow stops on the last node of the first half.
    var slow = head
    var fast = head
    while let step = fast.next, let jump = step.next, let middle = slow.next {
        slow = middle
        fast = jump
    }

    // 2. Cut after the first half, then reverse the second half.
    var second = slow.next
    slow.next = nil
    var previous: ListNode? = nil
    while let node = second {
        let next = node.next
        node.next = previous
        previous = node
        second = next
    }

    // 3. Weave: one from the front, one from the reversed back.
    var front: ListNode? = head
    var back = previous
    while let f = front, let b = back {
        let frontNext = f.next
        let backNext = b.next
        f.next = b
        b.next = frontNext
        front = frontNext
        back = backNext
    }
}
```

`slow.next = nil` is the line that keeps this correct: without it the first half's last node still points into the second half, and the weave builds a loop.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, five more (empty, two nodes, three nodes, six nodes, repeated values), a check that the same node objects are reused, and 2,000 random lists checked against interleaving an array from both ends.
:::

::: Walk it through
**`10 → 20 → 30 → 40 → 50`**

1. Middle: slow and fast start on 10. Fast jumps to 30 while slow steps to 20; fast jumps to 50 while slow steps to 30; 50 has no next, so stop. First half `10 → 20 → 30`.
2. Cut after 30, reverse `40 → 50` into `50 → 40`.
3. Weave:

| Step | Front | Back | Links made | List so far |
|---|---|---|---|---|
| 1 | 10 | 50 | 10 → 50 → 20 | `10 → 50 → 20 → 30` |
| 2 | 20 | 40 | 20 → 40 → 30 | `10 → 50 → 20 → 40 → 30` |
| 3 | 30 | nothing | stop | `10 → 50 → 20 → 40 → 30` |

**`8`** — fast has no next, so slow stays on 8; the second half is empty, reversing it gives nothing, and the weave stops at once. The list is unchanged.
:::

::: The Swift trap
**Forgetting the cut builds a loop that ARC never frees.** Leave out `slow.next = nil` on `1 → 2 → 3 → 4` and the node 2 still points at 3 when the weave starts. The last weave step links 2 → 3 and then sets 3's next to 2's old next — which is 3 itself — so the list ends `1 → 4 → 2 → 3 → 3 → 3 …`. In a test, `values(of:)` never returns: it hangs instead of failing. In an app, the loop is a strong reference cycle and every node leaks. Also note the signature: `head` is not `inout`. The function changes the nodes behind the reference, which is allowed because `ListNode` is a class; the caller's variable still points at the same first node.
:::

::: What they ask next
- **"Simpler, if memory is allowed?"** → Put the nodes in an array, then link them with two indices from both ends moving inwards; O(n) extra memory, easy to get right.
- **"Is a linked list a palindrome, in O(1) memory?"** → The same first two steps: find the middle, reverse the second half, then compare the halves node by node (and reverse it back if the caller cares).
- **"Which middle does your loop find for an even length?"** → The end of the first half (2 in `1 → 2 → 3 → 4`), because it stops when fast can't make a full jump; that keeps the front half at least as long as the back.
:::
