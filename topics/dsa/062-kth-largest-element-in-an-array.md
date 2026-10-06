---
title: 52 · Kth Largest Element in an Array
summary: Given a list of numbers and a position k, return the number that would sit kth from the top if the list were sorted from largest to smallest.
group: Heap
minutes: 25
sources:
- LeetCode 215 · Kth Largest Element in an Array | https://leetcode.com/problems/kth-largest-element-in-an-array/
- Swift Collections · Heap | https://github.com/apple/swift-collections/blob/main/Documentation/Heap.md
---

*Medium*

You get an array of integers and a number k. Imagine the array sorted from largest to smallest and return the value at position k, counting from 1. Duplicates keep their places: in `[9, 9, 7]` the first largest is 9 and so is the second. The array is not sorted, and you may not assume anything about its order.

| Numbers | k | Answer |
|---|---|---|
| `[7, 2, 9, 4, 9, 1]` | `2` | `9` — the two 9s are first and second |
| `[5]` | `1` | `5` — one number, it is the largest |
| `[3, -2, 8, 0]` | `4` | `-2` — k equal to the length means the smallest |

Constraints that matter: up to 100,000 numbers between −10,000 and 10,000, and 1 ≤ k ≤ the length. Sorting answers it in O(n log n). The interviewer is waiting for "can you do better without sorting everything?" — O(n log k) with a heap, or O(n) on average with quickselect.

::: Starter code and tests
Neither starter includes a heap: writing one is part of the exercise, or paste the one from the [heap primer](#/dsa/heap).

In an Xcode test target:

```swift
import Testing

struct KthLargestElementTests {

    @Test(arguments: [
        ([7, 2, 9, 4, 9, 1], 2, 9),
        ([5], 1, 5),
        ([3, -2, 8, 0], 4, -2),
    ])
    func returnsTheValueAtPositionKCountingFromTheLargest(numbers: [Int], k: Int, expected: Int) {
        #expect(findKthLargest(numbers, k) == expected)
    }

    // MARK: - Privates
    private func findKthLargest(_ numbers: [Int], _ k: Int) -> Int {
        0
    }
}
```

In a playground:

```swift
func findKthLargest(_ numbers: [Int], _ k: Int) -> Int {
    0 // your solution
}

let cases: [([Int], Int, Int)] = [
    ([7, 2, 9, 4, 9, 1], 2, 9),
    ([5], 1, 5),
    ([3, -2, 8, 0], 4, -2),
]
for (numbers, k, expected) in cases {
    let got = findKthLargest(numbers, k)
    print(got == expected ? "PASS" : "FAIL", numbers, k, "→", got, "expected", expected)
}
```
:::

::: Pattern and cue
**Heap of size k.** The cue is *"kth largest"* in an unsorted array: you need the k biggest values and nothing else about the order. Keep the k largest seen so far in a heap whose top is the *smallest* of them; that top is the answer once every number has passed through.
:::

::: Approach
Go through the numbers one at a time and keep a small group of the k largest seen so far. Each new number joins the group; if the group now has more than k members, the smallest member leaves. The smallest member is the one to watch, so keep the group in a min-heap, which hands it over cheaply. After the last number, the group holds exactly the k largest values, and the smallest of those is the kth largest.

Time O(n log k): n pushes and at most n pops, each on a heap of at most k + 1 items. Space O(k) for the heap. Sorting is O(n log n) time and a fine first answer to say before you optimise; quickselect is O(n) on average, discussed below.
:::

::: Swift solution
```swift
func findKthLargest(_ numbers: [Int], _ k: Int) -> Int {
    var smallestOnTop = Heap<Int>(by: <)          // a min-heap holding the k largest so far
    for number in numbers {
        smallestOnTop.push(number)
        if smallestOnTop.count > k {
            _ = smallestOnTop.pop()                // evict the weakest of the k + 1
        }
    }
    return smallestOnTop.peek!                     // safe: 1 ≤ k ≤ numbers.count
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

The `by: <` is the line that decides everything: to keep the *largest* values you evict the *smallest*, so the heap has the smallest on top. The sort answer, to say first: `numbers.sorted(by: >)[k - 1]`.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, six more (all values equal, k = 1, negatives only, a long run of duplicates around the cut-off, a sorted and a reverse-sorted input), and 2,000 random arrays checked against `sorted(by: >)[k - 1]`.
:::

::: Walk it through
**`[7, 2, 9, 4, 9, 1]`, k = 2**

| Number | Heap after push | Over k? | Heap after | Top |
|---|---|---|---|---|
| 7 | 7 | no | 7 | 7 |
| 2 | 2, 7 | no | 2, 7 | 2 |
| 9 | 2, 7, 9 | yes, pop 2 | 7, 9 | 7 |
| 4 | 4, 7, 9 | yes, pop 4 | 7, 9 | 7 |
| 9 | 7, 9, 9 | yes, pop 7 | 9, 9 | 9 |
| 1 | 1, 9, 9 | yes, pop 1 | 9, 9 | 9 |

Answer 9. The second 9 pushes the 7 out: duplicates count as separate values, which is what the statement asks.

**`[3, -2, 8, 0]`, k = 4** — the heap never goes over four items, so nothing is evicted. Its top is the smallest of all four, −2. When k equals the length, the kth largest is the minimum.
:::

::: The Swift trap
**The off-by-one lives in the sort answer, and the direction bug lives in the heap answer.** `numbers.sorted()[k]` reads the (k + 1)th *smallest*: wrong twice. The kth largest is `sorted(by: >)[k - 1]`, or `sorted()[numbers.count - k]`. In the heap version, `Heap<Int>(by: >)` compiles, runs and returns a number from the array, just not the right one: a max-heap that evicts its top throws away the largest values and leaves the kth *smallest*. Naming the variable `smallestOnTop` is how you catch it while typing.
:::

::: What they ask next
- **"Can you do it in O(n)?"** → Quickselect: partition around a pivot as in quicksort, then recurse only into the side that holds position n − k. O(n) on average, O(n²) worst case; a random pivot makes the worst case unlikely. Say it, and say the heap is the safer code to write live.
- **"The numbers arrive as a stream; report the kth largest after each one."** → The same min-heap of size k, kept between calls: push, evict if over k, return the top. O(log k) per number.
- **"The kth largest *distinct* value."** → Put the numbers in a `Set` first, or skip a push when the value is already in the heap (track the heap's contents in a set).
:::
