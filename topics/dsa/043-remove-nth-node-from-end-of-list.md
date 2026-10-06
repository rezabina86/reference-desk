---
title: 36 · Remove Nth Node From End of List
summary: Delete the node that sits a given number of places from the end of a linked list, walking the list only once.
group: Linked list
minutes: 25
sources:
- LeetCode 19 · Remove Nth Node From End of List | https://leetcode.com/problems/remove-nth-node-from-end-of-list/
---

*Medium · G*

You get the first node of a singly linked list and a number n. Remove the node that is n places from the end — n = 1 is the last node — and return the first node of the result. n is always between 1 and the length of the list, so the node always exists; it may be the first node, in which case the list's first node changes.

| List | n | Answer |
|---|---|---|
| `6 → 7 → 8 → 9 → 10` | 2 | `6 → 7 → 8 → 10` |
| `4` | 1 | empty |
| `1 → 2` | 2 | `2` — the first node is the one removed |

Constraints that matter: up to 30 nodes on LeetCode, but the real constraint is the follow-up: **one pass**. Counting the length first and then walking again is O(n) too, and is the answer to improve on.

::: Starter code and tests
In an Xcode test target:

```swift
import Testing

struct RemoveNthNodeFromEndOfListTests {

    @Test(arguments: [
        ([6, 7, 8, 9, 10], 2, [6, 7, 8, 10]),
        ([4], 1, []),
        ([1, 2], 2, [2]),
    ])
    func removesTheNodeNPlacesFromTheEnd(list: [Int], n: Int, expected: [Int]) {
        #expect(values(of: removeNthFromEnd(makeList(list), n)) == expected)
    }

    // MARK: - Privates
    private func removeNthFromEnd(_ head: ListNode?, _ n: Int) -> ListNode? {
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

func removeNthFromEnd(_ head: ListNode?, _ n: Int) -> ListNode? {
    nil // your solution
}

let cases: [([Int], Int, [Int])] = [
    ([6, 7, 8, 9, 10], 2, [6, 7, 8, 10]),
    ([4], 1, []),
    ([1, 2], 2, [2]),
]
for (list, n, expected) in cases {
    let got = values(of: removeNthFromEnd(makeList(list), n))
    print(got == expected ? "PASS" : "FAIL", list, n, "→", got, "expected", expected)
}
```
:::

::: Pattern and cue
**Two pointers with a fixed gap, behind a dummy head.** The cue is *"from the end"* plus *"one pass"*: you can't count backwards in a singly linked list, but if a leading pointer starts n + 1 nodes ahead, then when it falls off the end, the trailing pointer is right before the node to remove. The dummy head covers the case where that node is the first one.
:::

::: Approach
Put a placeholder node in front of the list, so even the first real node has a node before it. Start two pointers on the placeholder. Move the leading one n + 1 nodes forward. Then move both one node at a time until the leading one has gone past the last node. The gap between them never changes, so the trailing pointer now stands on the node just before the one to remove. Link it past that node, and return whatever comes after the placeholder.

Time O(L), where L is the length: the leading pointer walks the list once. Space O(1): one placeholder node and two references.
:::

::: Swift solution
```swift
func removeNthFromEnd(_ head: ListNode?, _ n: Int) -> ListNode? {
    let dummy = ListNode(0, head)
    var lead: ListNode? = dummy
    var trail = dummy

    for _ in 0...n { lead = lead?.next }            // n + 1 steps: lead is n + 1 ahead
    while let node = lead, let next = trail.next {
        lead = node.next
        trail = next
    }
    trail.next = trail.next?.next                   // skip the nth node from the end
    return dummy.next
}
```

`0...n` is n + 1 steps, one more than n, so `trail` stops *before* the node to remove rather than on it. Returning `dummy.next`, not `head`, is what makes the "remove the first node" case work.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, five more (removing the last node, removing the first of five, a two-node list with n = 1, repeated values, n equal to the length of a 30-node list), and every n for 1,000 random lists checked against `Array.remove(at:)`.
:::

::: Walk it through
**`6 → 7 → 8 → 9 → 10`, n = 2** (`D` is the placeholder)

| Stage | Lead on | Trail on |
|---|---|---|
| start | D | D |
| after 3 steps of lead alone | 8 | D |
| both step | 9 | 6 |
| both step | 10 | 7 |
| both step | nothing | 8 |

Trail is on 8, so 8 is linked to 10 and 9 is gone: `6 → 7 → 8 → 10`.

**`1 → 2`, n = 2** — lead takes three steps from `D`: 1, 2, nothing. The second loop doesn't run, so trail is still on `D`. `D` is linked past 1 to 2, and `dummy.next` is the node 2.
:::

::: The Swift trap
**Returning `head` hands back the deleted node.** When the removed node is the first one, the code never touches the caller's `head` variable: it still refers to the node 1, and since that node still links to 2, returning `head` gives back `1 → 2` unchanged, with no crash to warn you. In Swift the removal itself is complete once nothing points at the node — ARC frees it, there is no `delete` — but only if *nothing* still holds it, and `head` does until it goes out of scope. Return `dummy.next`.
:::

::: What they ask next
- **"Two passes are fine?"** → Count the length L, then walk L − n nodes from the placeholder and skip the next one; same O(L), and a fine first answer to improve from.
- **"What if n can be larger than the length?"** → Check during the head start: when n equals the length, `lead` becomes `nil` on exactly the last of its n + 1 steps; if it is already `nil` with steps still to take, n is too large — return the list unchanged or throw, and say which.
- **"Delete a node when you are given only that node, not the head."** → Copy the next node's value into it and skip the next node; impossible for the last node, which is why the problem promises it isn't.
:::
