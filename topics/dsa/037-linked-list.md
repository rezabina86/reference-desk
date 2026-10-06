---
title: Linked list — the idea
summary: How to rewire a chain of nodes safely, the two helpers that remove most special cases, and the Swift details that make lists different from arrays.
group: Linked list
minutes: 8
sources:
- The Swift Programming Language · Automatic Reference Counting | https://docs.swift.org/swift-book/documentation/the-swift-programming-language/automaticreferencecounting/
- The Swift Programming Language · Identity Operators | https://docs.swift.org/swift-book/documentation/the-swift-programming-language/classesandstructures/#Identity-Operators
---

Linked-list problems rarely ask you to *choose* a list. The input already is one, and the question is how to change its links without losing any of it. A handful of moves covers every problem in this topic.

## When to reach for it

- The statement hands you **"the head of a linked list"** — the work is rewiring, not picking a data structure.
- **"Reverse"**, **"reorder"**, **"merge"**, **"in place"** on a list → walk it once, changing `next` as you go.
- **"Cycle"**, **"loops back"**, **"middle"**, **"nth from the end"** → two pointers moving at different speeds, or with a fixed gap.
- A design problem that needs **"remove from the middle"** or **"move to the front"** in O(1) → a doubly linked list, usually with a dictionary beside it.

## The idea in plain words

Think of a train. Each car is coupled only to the car behind it. You can't jump to the seventh car; you walk from the engine, car by car. What a train is good at is recoupling: taking a car out of the middle or turning a stretch around means changing a couple of couplings, with nothing to shift along, unlike seats in a row.

Every problem here is the same question: which couplings change, and in which order, so that no part of the train is left behind on the track. The rule that prevents the classic bug: before you uncouple a car, hold on to the one behind it.

## The template in Swift

The node and the two helpers every chapter in this topic uses, then the three moves.

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

// 1. Rewire in place: save next, flip the link, step forward.
func reversed(_ head: ListNode?) -> ListNode? {
    var previous: ListNode? = nil
    var current = head
    while let node = current {
        let next = node.next        // hold on to the rest of the train first
        node.next = previous
        previous = node
        current = next
    }
    return previous
}

// 2. Dummy head: a throwaway node in front, so the real first node is not a special case.
func removingOdds(_ head: ListNode?) -> ListNode? {
    let dummy = ListNode(0, head)
    var tail = dummy
    while let next = tail.next {
        if next.value % 2 == 0 {
            tail = next                 // keep it, move on
        } else {
            tail.next = next.next       // skip it, even if it was the head
        }
    }
    return dummy.next
}

// 3. Fast and slow: one pointer moves two steps for every one step of the other.
/// The middle node; for an even length, the second of the two middles.
func middle(of head: ListNode?) -> ListNode? {
    var slow = head
    var fast = head
    while let step = fast?.next {
        slow = slow?.next
        fast = step.next
    }
    return slow
}
```

When fast runs off the end, slow is halfway. If the list loops, fast never runs off the end, and it eventually lands on slow from behind: that is how a cycle is detected with no extra memory.

## Variations

- **Rewire in place.** Reverse a list, or a part of it; reorder it. Always: save `next`, change the link, then step.
- **Build a chain behind a dummy head.** Merge two lists, add two numbers digit by digit, delete a node that might be the first one. Keep a `tail` that you append to and return `dummy.next`.
- **Two pointers at different speeds, or with a gap.** Twice the speed finds the middle or a cycle; a lead of n nodes finds the nth node from the end in one pass.
- **Doubly linked list plus a dictionary.** The dictionary finds a node in O(1), the `prev` and `next` links remove or move it in O(1). This is the LRU cache.

## Complexity

Each move walks the list once: O(n) time. The extra memory is a few references and at most one dummy node: O(1). The recursive versions of these moves are shorter to write but use one stack frame per node, which is O(n) space.

## Swift traps

- **A node has to be a class.** `struct ListNode { var next: ListNode? }` doesn't compile: *"value type 'ListNode' cannot have a stored property that recursively contains it"*. An `indirect enum` list compiles but can't be rewired in place. Every move above relies on two variables pointing at the same node.
- **Compare nodes with `===`, not `==`.** `ListNode` is not `Equatable`, so `==` doesn't compile, and you want "the same node" anyway, not "the same value". To put nodes in a `Set`, store `ObjectIdentifier(node)`.
- **ARC frees what nothing points at, and never frees a loop.** Skipping a node with `tail.next = next.next` is a complete delete: no `free`. But a list that loops back is a strong reference cycle and leaks, and a doubly linked list needs `weak` (or `unowned`) on `prev`, or every pair of neighbours keeps each other alive.
- **Recursion has a real ceiling.** One stack frame per node: in a debug build (Swift 6.4), a recursive reversal crashed between 30,000 and 40,000 nodes on the 8 MB main thread, and below 3,000 nodes on a background thread's 512 KB stack — where Swift Testing and GCD run code. That is inside some LeetCode limits. Write the loop, and offer the recursion as the short version with its limit said out loud.
- **There is no linked list in the standard library.** In app code you use `Array`, or `Deque` from swift-collections. These problems are about the moves, and the node type is part of the problem.

## The problems in this topic

- [31 · Reverse Linked List](#/dsa/reverse-linked-list) — Easy
- [32 · Merge Two Sorted Lists](#/dsa/merge-two-sorted-lists) — Easy
- [33 · Linked List Cycle](#/dsa/linked-list-cycle) — Easy
- [34 · Add Two Numbers](#/dsa/add-two-numbers) — Medium
- [35 · Reorder List](#/dsa/reorder-list) — Medium
- [36 · Remove Nth Node From End of List](#/dsa/remove-nth-node-from-end-of-list) — Medium
- [37 · LRU Cache](#/dsa/lru-cache) — Medium
