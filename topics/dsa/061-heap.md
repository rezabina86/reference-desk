---
title: Heap — the idea
summary: A structure that always hands you the smallest (or largest) item it holds, cheaply, even while items keep arriving.
group: Heap
minutes: 10
sources:
- Swift Collections · Heap | https://github.com/apple/swift-collections/blob/main/Documentation/Heap.md
- Wikipedia · Binary heap | https://en.wikipedia.org/wiki/Binary_heap
- Swift standard library · MutableCollection.swapAt(_:_:) | https://developer.apple.com/documentation/swift/mutablecollection/swapat(_:_:)
---

Sorting puts *everything* in order. Many problems only ever need *the next one*: the smallest, the largest, the most urgent. A heap keeps just enough order to answer that question in O(1) and to absorb a new item or remove the top in O(log n). When the input is big and k is small, that difference is the whole problem.

## When to reach for it

- **"k largest"**, **"k smallest"**, **"k closest"**, **"top k"** — keep only k items and throw away the rest as you go.
- **"Kth largest / smallest"** — the kth is the top of a heap that holds the k best.
- **"Merge k sorted …"** — the next item overall is the smallest of the k fronts.
- **A stream**: numbers arrive one at a time and you must answer after each one (running median, running top k).
- **"Most frequent first"**, **"schedule the most urgent next"** — repeatedly take the best remaining item, change it, put it back.

## The idea in plain words

Think of a hospital waiting room run by triage. Nobody keeps the whole room sorted from most to least urgent; that would mean re-sorting every time someone walks in. The nurse only needs to know who is *most* urgent right now. A new patient is compared with a few others and settles into place; when the most urgent one is called in, a few comparisons decide who is next. That partial order is a heap.

In code, a binary heap is an array read as a tree: the item at position `i` has children at `2i + 1` and `2i + 2`, and every parent ranks ahead of its children. So the best item is always at position 0. **Push** puts the new item at the end and lets it climb past parents it beats. **Pop** takes position 0, moves the last item into the hole, and lets it sink below children that beat it. Each climb or sink is one level per step, and the tree has log n levels.

## The template in Swift

The standard library has no heap, so write this one once and know it by heart. The comparator decides the direction: `<` puts the smallest on top (a min-heap), `>` the largest (a max-heap).

```swift
struct Heap<Element> {
    private var elements: [Element] = []
    private let isHigherPriority: (Element, Element) -> Bool   // true: the first belongs nearer the top

    init(by isHigherPriority: @escaping (Element, Element) -> Bool) {
        self.isHigherPriority = isHigherPriority
    }

    var count: Int { elements.count }
    var isEmpty: Bool { elements.isEmpty }
    var peek: Element? { elements.first }                       // the top, O(1)

    mutating func push(_ element: Element) {                    // O(log n)
        elements.append(element)
        var child = elements.count - 1
        while child > 0 {                                       // climb while it beats its parent
            let parent = (child - 1) / 2
            guard isHigherPriority(elements[child], elements[parent]) else { break }
            elements.swapAt(child, parent)
            child = parent
        }
    }

    mutating func pop() -> Element? {                           // O(log n)
        guard !elements.isEmpty else { return nil }
        elements.swapAt(0, elements.count - 1)                  // move the top to the end, where removing is O(1)
        let top = elements.removeLast()
        var parent = 0
        while true {                                            // sink while a child beats it
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

Using it: `var smallestOnTop = Heap<Int>(by: <)`, then `push`, `peek`, `pop`. For a heap of anything else — points, list nodes, tuples — pass a closure that compares the field you care about: `Heap<[Int]>(by: { $0[0] < $1[0] })`.

The heap chapters paste this same struct into their solutions, so each one compiles on its own.

## Variations

- **Keep the k best, evict the worst.** To find the k *largest*, keep a *min*-heap of size k: its top is the weakest of the current best, the one to throw out when something better arrives. Kth Largest, K Closest Points. The direction feels backwards the first time; say why out loud.
- **Merge k fronts.** Put the first item of each sorted source in a min-heap; pop the smallest, push the next item from the same source. Merge K Sorted Lists.
- **Take the best, update it, put it back.** Pop the most urgent, do one unit of work on it, push it back if anything is left. Task Scheduler.
- **Two heaps facing each other.** A max-heap for the lower half and a min-heap for the upper half, kept within one item of the same size, so the middle is always at one of the two tops. Find Median from Data Stream.

## Complexity

`push` and `pop` are O(log n): one swap per level, and a tree of n items has about log₂ n levels. `peek` is O(1). Space is O(n) for the array, or O(k) when you cap the heap at k items, which is the point of the "keep k" variation: n pushes into a heap of size k cost O(n log k).

Building a heap from n items by pushing them one by one is O(n log n). There is an O(n) bottom-up build (sink every parent from the last one up to the root); worth knowing exists, rarely worth writing in an interview.

## Swift traps

- **There is no `Heap` or `PriorityQueue` in the standard library.** The production answer is `Heap` from Apple's [swift-collections](https://github.com/apple/swift-collections) package (`import HeapModule`), a min-max heap of `Comparable` elements with both `popMin()` and `popMax()`; but a shared editor or a fresh playground won't have it. Say that, then write the struct above: about 40 lines, five minutes once practised.
- **`sorted()` followed by `removeFirst()` is not a heap.** `removeFirst()` on an `Array` is O(n), and re-sorting after every insert is O(n log n). Both quietly turn an O(n log k) answer into O(n²) or worse.
- **The comparator direction is the classic bug.** `Heap<Int>(by: <)` keeps the *smallest* on top. Getting it backwards compiles and runs and returns a plausible wrong answer. Name the variable after what sits on top (`smallestOnTop`, `farthestOnTop`) and the bug becomes visible.
- **Tuples aren't `Comparable` or `Hashable`.** Swift-collections' `Heap` needs `Comparable` elements, so a `(distance, point)` tuple won't go in; a small `struct` with a `<` will, or use the closure-based heap above.
- **The closure makes the struct non-`Sendable`.** Fine inside a function; if a heap must cross actors, store a comparator that is `@Sendable`, or use swift-collections' `Heap` with `Comparable` elements.

## The problems in this topic

- [52 · Kth Largest Element in an Array](#/dsa/kth-largest-element-in-an-array) — Medium
- [53 · K Closest Points to Origin](#/dsa/k-closest-points-to-origin) — Medium
- [54 · Task Scheduler](#/dsa/task-scheduler) — Medium
- [55 · Merge K Sorted Lists](#/dsa/merge-k-sorted-lists) — Hard, optional
- [56 · Find Median from Data Stream](#/dsa/find-median-from-data-stream) — Hard, optional
