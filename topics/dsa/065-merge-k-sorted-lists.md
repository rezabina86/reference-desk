---
title: 55 · Merge K Sorted Lists
summary: Given several linked lists that are each already in ascending order, join them into one ascending linked list.
group: Heap
minutes: 35
sources:
- LeetCode 23 · Merge k Sorted Lists | https://leetcode.com/problems/merge-k-sorted-lists/
- Swift Collections · Heap | https://github.com/apple/swift-collections/blob/main/Documentation/Heap.md
---

*Hard · optional · G*

**Optional.** Above the bar most German loops set; do it if the topic's mediums went well.

You get an array of singly linked lists. Each list is sorted from smallest to largest, but the lists know nothing about each other. Return the head of one list that contains every node from all of them, sorted from smallest to largest. Some lists may be empty, and so may the array itself. Reusing the existing nodes is expected; you don't need to copy values into new ones.

| Lists | Answer |
|---|---|
| `[1 → 4 → 7, 2 → 5, 3 → 6 → 9]` | `1 → 2 → 3 → 4 → 5 → 6 → 7 → 9` |
| `[]` | empty — no lists at all |
| `[empty, 0, empty]` | `0` — empty lists mixed in |

Constraints that matter: up to 10,000 lists and 10,000 nodes in total, values between −10,000 and 10,000. Merging the lists one into the next is O(k · N) for k lists and N nodes; the target is O(N log k).

::: Starter code and tests
Lists are passed to the test as arrays and built inside it. Neither starter includes a heap: writing one is part of the exercise, or paste the one from the [heap primer](#/dsa/heap).

In an Xcode test target:

```swift
import Testing

struct MergeKSortedListsTests {

    @Test(arguments: [
        ([[1, 4, 7], [2, 5], [3, 6, 9]], [1, 2, 3, 4, 5, 6, 7, 9]),
        ([], []),
        ([[], [0], []], [0]),
    ] as [([[Int]], [Int])])
    func joinsEveryListIntoOneAscendingList(lists: [[Int]], expected: [Int]) {
        #expect(values(of: mergeKLists(lists.map(makeList))) == expected)
    }

    // MARK: - Privates
    private func mergeKLists(_ lists: [ListNode?]) -> ListNode? {
        nil
    }
}

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

func mergeKLists(_ lists: [ListNode?]) -> ListNode? {
    nil // your solution
}

let cases: [([[Int]], [Int])] = [
    ([[1, 4, 7], [2, 5], [3, 6, 9]], [1, 2, 3, 4, 5, 6, 7, 9]),
    ([], []),
    ([[], [0], []], [0]),
]
for (lists, expected) in cases {
    let got = values(of: mergeKLists(lists.map(makeList)))
    print(got == expected ? "PASS" : "FAIL", lists, "→", got, "expected", expected)
}
```
:::

::: Pattern and cue
**Min-heap of the k fronts.** The cue is *"k sorted"* sources that must become one sorted output: the next node overall is always the smallest of the k current fronts, and "smallest of k, over and over, while the k change" is what a heap does in O(log k).
:::

::: Approach
Put the first node of every non-empty list into a min-heap ordered by value. Then repeat: take the smallest node out of the heap, attach it to the end of the result, and if that node has a successor in its own list, put the successor into the heap. When the heap is empty, every node has been attached exactly once, in ascending order. A placeholder node in front of the result saves a special case for the first attachment.

Time O(N log k): each of the N nodes goes into the heap once and comes out once, and the heap never holds more than k nodes. Space O(k) for the heap; the result reuses the existing nodes.
:::

::: Swift solution
The function below uses the `ListNode` from the starter.

```swift
func mergeKLists(_ lists: [ListNode?]) -> ListNode? {
    var smallestOnTop = Heap<ListNode>(by: { $0.value < $1.value })
    for case let head? in lists { smallestOnTop.push(head) }     // skip the empty lists

    let placeholder = ListNode(0)
    var tail = placeholder
    while let node = smallestOnTop.pop() {
        tail.next = node
        tail = node
        if let next = node.next { smallestOnTop.push(next) }
    }
    return placeholder.next
}

// The primer's Heap, pasted so this block compiles on its own.
struct Heap<Element> {
    private var elements: [Element] = []
    private let isHigherPriority: (Element, Element) -> Bool

    init(by isHigherPriority: @escaping (Element, Element) -> Bool) {
        self.isHigherPriority = isHigherPriority
    }

    var count: Int { elements.count }
    var isEmpty: Bool { elements.isEmpty }
    var peek: Element? { elements.first }

    mutating func push(_ element: Element) {
        elements.append(element)
        var child = elements.count - 1
        while child > 0 {
            let parent = (child - 1) / 2
            guard isHigherPriority(elements[child], elements[parent]) else { break }
            elements.swapAt(child, parent)
            child = parent
        }
    }

    mutating func pop() -> Element? {
        guard !elements.isEmpty else { return nil }
        elements.swapAt(0, elements.count - 1)
        let top = elements.removeLast()
        var parent = 0
        while true {
            let left = 2 * parent + 1
            let right = left + 1
            var first = parent
            if left < elements.count, isHigherPriority(elements[left], elements[first]) { first = left }
            if right < elements.count, isHigherPriority(elements[right], elements[first]) { first = right }
            if first == parent { break }
            elements.swapAt(parent, first)
            parent = first
        }
        return top
    }
}
```

`for case let head? in lists` iterates only the non-nil heads, so empty lists never reach the heap. The heap stores the nodes themselves and compares them by `value` through the closure; `ListNode` doesn't need to be `Comparable`.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, five more (a single list, all lists empty, duplicates across lists, negative values, one long list next to many one-node lists), and 2,000 random sets of sorted lists checked against concatenating every value and sorting.
:::

::: Walk it through
**`[1 → 4 → 7, 2 → 5, 3 → 6 → 9]`**

| Step | Heap before (values) | Pop | Push its successor | Result so far |
|---|---|---|---|---|
| 1 | 1, 2, 3 | 1 | 4 | 1 |
| 2 | 2, 3, 4 | 2 | 5 | 1 2 |
| 3 | 3, 4, 5 | 3 | 6 | 1 2 3 |
| 4 | 4, 5, 6 | 4 | 7 | 1 2 3 4 |
| 5 | 5, 6, 7 | 5 | — | 1 2 3 4 5 |
| 6 | 6, 7 | 6 | 9 | 1 2 3 4 5 6 |
| 7 | 7, 9 | 7 | — | 1 2 3 4 5 6 7 |
| 8 | 9 | 9 | — | 1 2 3 4 5 6 7 9 |

The heap never holds more than three nodes, one per list.

**`[empty, 0, empty]`** — only the `0` node enters the heap; one pop, no successor, and the placeholder's `next` is that node.
:::

::: The Swift trap
**The recursive two-list merge that reads so nicely elsewhere can overflow the stack.** The textbook version (`a.next = merge(a.next, b)`) uses one stack frame per node it attaches. Measured on Swift 6.4 in a debug build: merging two lists of 5,000 nodes each crashes on a secondary thread, whose stack is 512 KB, and two lists of 50,000 crash even on the main thread's 8 MB. Interview inputs reach 10,000 nodes, and test runners and background queues don't run on the main thread. If you write the divide-and-conquer follow-up, write its two-list merge as a loop with a placeholder node, like the heap version above.
:::

::: What they ask next
- **"Do it without a heap."** → Divide and conquer: merge lists in pairs (0 with 1, 2 with 3, …), then merge the results in pairs, until one list remains. log k rounds, each touching all N nodes: O(N log k) time, O(1) extra space with an iterative two-list merge.
- **"Why not merge them one at a time into a growing result?"** → The growing result is re-walked for every new list: O(k · N) in total, which is 10,000 × 10,000 at these limits.
- **"The sources are huge sorted files on disk, not lists."** → The same heap of fronts is the merge step of an external sort: keep one buffered reader per file and k values in memory.
:::
