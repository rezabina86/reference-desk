---
title: 32 · Merge Two Sorted Lists
summary: Combine two linked lists that are each in ascending order into one ascending list, reusing their nodes.
group: Linked list
minutes: 15
sources:
- LeetCode 21 · Merge Two Sorted Lists | https://leetcode.com/problems/merge-two-sorted-lists/
---

*Easy · G*

You get the first nodes of two singly linked lists, each sorted from smallest to largest. Join them into a single list that is also sorted, by relinking the nodes you were given rather than creating new ones, and return its first node. Either list, or both, may be empty.

| First list | Second list | Answer |
|---|---|---|
| `1 → 4 → 6` | `2 → 4 → 9` | `1 → 2 → 4 → 4 → 6 → 9` |
| empty | `0 → 3` | `0 → 3` |
| empty | empty | empty |

Constraints that matter: up to 50 nodes in each list, values from −100 to 100, duplicates allowed. The target is O(n + m) time and O(1) extra memory.

::: Starter code and tests
In an Xcode test target:

```swift
import Testing

struct MergeTwoSortedListsTests {

    @Test(arguments: [
        ([1, 4, 6], [2, 4, 9], [1, 2, 4, 4, 6, 9]),
        ([], [0, 3], [0, 3]),
        ([], [], []),
    ])
    func returnsOneSortedListHoldingEveryNode(first: [Int], second: [Int], expected: [Int]) {
        #expect(values(of: mergeTwoLists(makeList(first), makeList(second))) == expected)
    }

    // MARK: - Privates
    private func mergeTwoLists(_ list1: ListNode?, _ list2: ListNode?) -> ListNode? {
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

func mergeTwoLists(_ list1: ListNode?, _ list2: ListNode?) -> ListNode? {
    nil // your solution
}

let cases: [([Int], [Int], [Int])] = [
    ([1, 4, 6], [2, 4, 9], [1, 2, 4, 4, 6, 9]),
    ([], [0, 3], [0, 3]),
    ([], [], []),
]
for (first, second, expected) in cases {
    let got = values(of: mergeTwoLists(makeList(first), makeList(second)))
    print(got == expected ? "PASS" : "FAIL", first, second, "→", got, "expected", expected)
}
```
:::

::: Pattern and cue
**Dummy head with two pointers.** The cue is *"merge"* plus *"sorted"*: compare the two fronts, take the smaller, repeat. Because you don't know which list supplies the first node, you build behind a throwaway node and never special-case the start.
:::

::: Approach
Make a placeholder node to hang the result on, and keep a finger on the last node of the result so far. While both lists still have nodes, compare their first nodes, attach the smaller one to the end of the result, and move that list on by one. When one list runs out, the other is already sorted and every node left in it is at least as big as everything attached, so attach the whole remainder in one step. The answer starts right after the placeholder.

Time O(n + m): each node is attached once. Space O(1): the placeholder and a few references; the nodes are reused.
:::

::: Swift solution
```swift
func mergeTwoLists(_ list1: ListNode?, _ list2: ListNode?) -> ListNode? {
    let dummy = ListNode(0)
    var tail = dummy
    var first = list1
    var second = list2

    while let a = first, let b = second {
        if a.value <= b.value {
            tail.next = a
            tail = a
            first = a.next
        } else {
            tail.next = b
            tail = b
            second = b.next
        }
    }
    tail.next = first ?? second     // one list is used up; hang the rest on as it is
    return dummy.next
}
```

`first ?? second` attaches whichever list still has nodes, or nothing when both are empty. `<=` takes from the first list on a tie, so equal values keep their original order: the merge is stable.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, five more (first list empty, all values equal, one list entirely smaller than the other, negative values, single nodes), a check that the result reuses the input nodes, and 2,000 random sorted pairs checked against sorting both arrays together.
:::

::: Walk it through
**`1 → 4 → 6` and `2 → 4 → 9`**

| Step | Front of first | Front of second | Take | Result so far |
|---|---|---|---|---|
| 1 | 1 | 2 | 1 (first) | `1` |
| 2 | 4 | 2 | 2 (second) | `1 → 2` |
| 3 | 4 | 4 | 4 (first, tie) | `1 → 2 → 4` |
| 4 | 6 | 4 | 4 (second) | `1 → 2 → 4 → 4` |
| 5 | 6 | 9 | 6 (first) | `1 → 2 → 4 → 4 → 6` |
| 6 | nothing | 9 | attach the rest | `1 → 2 → 4 → 4 → 6 → 9` |

**Empty and `0 → 3`** — the loop needs both lists, so it doesn't run. `first ?? second` is the second list, which is attached whole: `0 → 3`.
:::

::: The Swift trap
**The inputs are gone afterwards.** Arrays in Swift are values, so a Swift engineer expects `merge(a, b)` to leave `a` and `b` alone. `ListNode` is a class: the merge relinks the very nodes the caller holds. After the first example, the caller's `list1` still points at the node 1, which now continues `1 → 2 → 4 → 4 → 6 → 9`, and `list2` points at the node 2 in the middle of it. That's what the problem asks for, but if the caller needs the originals, copy them first, which costs O(n + m) new nodes. Say which one you're doing.
:::

::: What they ask next
- **"Merge k sorted lists."** → A min-heap of the k fronts gives O(N log k); without a heap in the standard library, merge the lists in pairs, round after round, with this function: also O(N log k).
- **"Do it recursively."** → The smaller front's `next` becomes the merge of the rest; O(n + m) stack frames, so the loop is safer for long lists.
- **"Two sorted arrays, merge into the first, which has room at the end."** → Fill from the back with two indices, largest first, so nothing is overwritten before it's read.
:::
