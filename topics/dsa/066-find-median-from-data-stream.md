---
title: 56 · Find Median from Data Stream
summary: Build an object that accepts numbers one at a time and can report, after any of them, the middle value of everything it has received.
group: Heap
minutes: 35
sources:
- LeetCode 295 · Find Median from Data Stream | https://leetcode.com/problems/find-median-from-data-stream/
- Swift Collections · Heap | https://github.com/apple/swift-collections/blob/main/Documentation/Heap.md
---

*Hard · optional · G*

**Optional.** Above the bar most German loops set; do it if the topic's mediums went well.

Design a type with two operations. `addNum` receives one integer. `findMedian` returns the median of all integers received so far, as a `Double`: the middle value once they are sorted, or the average of the two middle values when there is an even number of them. Calls can be mixed in any order, and `findMedian` is only called after at least one number has arrived.

| Numbers added, in order | Median after each |
|---|---|
| `5, 15, 1, 3` | `5.0, 10.0, 5.0, 4.0` |
| `-4, -4` | `-4.0, -4.0` — duplicates and negatives |
| `2, 1` | `2.0, 1.5` — the average of two integers isn't an integer |

Constraints that matter: up to 50,000 calls, values between −100,000 and 100,000. Keeping a sorted array costs O(n) per insert (finding the place is O(log n), shifting is O(n)); the target is O(log n) per `addNum` and O(1) per `findMedian`.

::: Starter code and tests
Each test case adds the numbers one by one and compares the list of medians reported after each. Neither starter includes a heap: writing one is part of the exercise, or paste the one from the [heap primer](#/dsa/heap).

In an Xcode test target:

```swift
import Testing

struct FindMedianFromDataStreamTests {

    @Test(arguments: [
        ([5, 15, 1, 3], [5.0, 10.0, 5.0, 4.0]),
        ([-4, -4], [-4.0, -4.0]),
        ([2, 1], [2.0, 1.5]),
    ])
    func reportsTheMedianAfterEveryNumberAdded(numbers: [Int], expected: [Double]) {
        let finder = MedianFinder()
        var medians: [Double] = []
        for number in numbers {
            finder.addNum(number)
            medians.append(finder.findMedian())
        }
        #expect(medians == expected)
    }

    // MARK: - Privates
    private final class MedianFinder {
        func addNum(_ number: Int) {}
        func findMedian() -> Double { 0 }
    }
}
```

In a playground:

```swift
final class MedianFinder {
    func addNum(_ number: Int) {}
    func findMedian() -> Double { 0 } // your solution
}

let cases: [([Int], [Double])] = [
    ([5, 15, 1, 3], [5.0, 10.0, 5.0, 4.0]),
    ([-4, -4], [-4.0, -4.0]),
    ([2, 1], [2.0, 1.5]),
]
for (numbers, expected) in cases {
    let finder = MedianFinder()
    var medians: [Double] = []
    for number in numbers {
        finder.addNum(number)
        medians.append(finder.findMedian())
    }
    print(medians == expected ? "PASS" : "FAIL", numbers, "→", medians, "expected", expected)
}
```
:::

::: Pattern and cue
**Two heaps facing each other.** The cue is *"median"* plus *one number at a time*: you never need the whole order, only the largest of the lower half and the smallest of the upper half. A max-heap holds the lower half, a min-heap the upper half, and the median sits on their tops.
:::

::: Approach
Split everything received into a lower half and an upper half. Keep the lower half in a max-heap, so its largest value is on top, and the upper half in a min-heap, so its smallest is on top. Two rules hold after every insert: every value in the lower half is at most every value in the upper half, and the lower half has either the same number of values as the upper half or exactly one more. To insert, put the new number into the lower half, move the lower half's top across to the upper half (which keeps the first rule), and if the upper half is now bigger, move its top back. Then the median is the lower top when the count is odd, or the average of the two tops when it is even.

Time O(log n) per `addNum`: at most three heap operations. O(1) per `findMedian`: two peeks. Space O(n): every number is stored once.
:::

::: Swift solution
```swift
final class MedianFinder {
    private var lowerHalf = Heap<Int>(by: >)     // largest of the lower half on top
    private var upperHalf = Heap<Int>(by: <)     // smallest of the upper half on top

    func addNum(_ number: Int) {
        lowerHalf.push(number)
        upperHalf.push(lowerHalf.pop()!)         // the largest low value crosses over
        if upperHalf.count > lowerHalf.count {
            lowerHalf.push(upperHalf.pop()!)     // lower half keeps the extra one
        }
    }

    func findMedian() -> Double {
        if lowerHalf.count > upperHalf.count {
            return Double(lowerHalf.peek!)
        }
        return (Double(lowerHalf.peek!) + Double(upperHalf.peek!)) / 2
    }
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

Routing every number through the lower half and across is what keeps the halves ordered without comparing anything yourself: whatever crosses is the largest of the lower half, so it can't be smaller than anything left behind. The force-unwraps are safe because each heap has just received a push.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, six more (a single number, an ascending run, a descending run, all values equal, the extremes −100,000 and 100,000 together, and `-3, 0`, whose −1.5 must not be truncated toward zero), and 1,000 random streams where the median after every insert was checked against sorting everything received so far.
:::

::: Walk it through
**`5, 15, 1, 3`**

| Add | Lower half (max on top) | Upper half (min on top) | Median |
|---|---|---|---|
| 5 | 5 → crosses → back: `5` | — | 5.0 (odd: lower top) |
| 15 | `5, 15` → 15 crosses: `5` | `15` | (5 + 15) / 2 = 10.0 |
| 1 | `5, 1` → 5 crosses → upper has 2, lower 1 → 5 back: `5, 1` | `15` | 5.0 |
| 3 | `5, 3, 1` → 5 crosses: `3, 1` | `5, 15` | (3 + 5) / 2 = 4.0 |

**`2, 1`** — after 2, the lower half holds 2: median 2.0. Adding 1: lower becomes `2, 1`, its top 2 crosses, sizes are equal, median (1 + 2) / 2 = 1.5. The half is the edge case this example exists for.
:::

::: The Swift trap
**Divide after converting, not before.** `Double((low + high) / 2)` does the division in `Int`, which truncates toward zero: `(1 + 2) / 2` is `1`, so the median of `1, 2` comes out `1.0`, and `(-3 + 0) / 2` is `-1` where `-1.5` was right. Convert each top to `Double` first, then add and divide, as above. With these limits the `Int` sum can't overflow, but if values could reach `Int.max / 2`, the `Int` addition would trap where the `Double` addition wouldn't.

Comparing `[Double]` with `==` in the test is safe here because every expected median is a whole number or a half, which `Double` represents exactly.
:::

::: What they ask next
- **"Every value is between 0 and 100."** → Keep 101 counters instead of heaps; walk them to the middle position on `findMedian`: O(1) to add, O(100) to query.
- **"Only the last w numbers count: a sliding-window median."** → The two heaps plus lazy deletion (remember which values have left the window, and discard them when they reach a top), or a balanced tree / sorted multiset. O(n log w).
- **"Why must the lower half hold the extra value, not either one?"** → So that the odd-count median is always in one known place. Picking a side is arbitrary; being consistent is what makes `findMedian` O(1) with no branching on which heap.
:::
