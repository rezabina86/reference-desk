---
title: 53 · K Closest Points to Origin
summary: Given points on a flat grid and a count k, return the k points that lie nearest to the centre (0, 0).
group: Heap
minutes: 25
sources:
- LeetCode 973 · K Closest Points to Origin | https://leetcode.com/problems/k-closest-points-to-origin/
- Swift Collections · Heap | https://github.com/apple/swift-collections/blob/main/Documentation/Heap.md
---

*Medium · G*

You get a list of points, each given as `[x, y]` with integer coordinates, and a number k. Distance is the ordinary straight-line distance to the origin `(0, 0)`. Return the k points closest to the origin. The answer is guaranteed to be unique as a set of points, and you may return them in any order.

| Points | k | Answer |
|---|---|---|
| `[[3, 4], [1, -1], [-2, 2]]` | `2` | `[[1, -1], [-2, 2]]` — distances 5, about 1.41, about 2.83 |
| `[[1, 0], [0, -1], [2, 2]]` | `2` | `[[1, 0], [0, -1]]` — two points tie at distance 1, and both make the cut |
| `[[0, 0]]` | `1` | `[[0, 0]]` — a point on the origin, distance 0 |

Constraints that matter: up to 10,000 points, coordinates between −10,000 and 10,000, and 1 ≤ k ≤ the number of points. Sorting by distance is O(n log n); the target is O(n log k), which matters when k is much smaller than n. Because order is free, the Xcode test sorts your answer before comparing.

::: Starter code and tests
Neither starter includes a heap: writing one is part of the exercise, or paste the one from the [heap primer](#/dsa/heap). The answer may come back in any order, so both starters sort it before comparing.

In an Xcode test target:

```swift
import Testing

struct KClosestPointsToOriginTests {

    @Test(arguments: [
        ([[3, 4], [1, -1], [-2, 2]], 2, [[1, -1], [-2, 2]]),
        ([[1, 0], [0, -1], [2, 2]], 2, [[1, 0], [0, -1]]),
        ([[0, 0]], 1, [[0, 0]]),
    ])
    func returnsTheKPointsNearestTheOrigin(points: [[Int]], k: Int, expected: [[Int]]) {
        #expect(sortedPoints(kClosest(points, k)) == sortedPoints(expected))
    }

    // MARK: - Privates
    private func kClosest(_ points: [[Int]], _ k: Int) -> [[Int]] {
        []
    }

    private func sortedPoints(_ points: [[Int]]) -> [[Int]] {
        points.sorted { $0.lexicographicallyPrecedes($1) }
    }
}
```

In a playground:

```swift
func kClosest(_ points: [[Int]], _ k: Int) -> [[Int]] {
    [] // your solution
}

func sortedPoints(_ points: [[Int]]) -> [[Int]] {
    points.sorted { $0.lexicographicallyPrecedes($1) }
}

let cases: [([[Int]], Int, [[Int]])] = [
    ([[3, 4], [1, -1], [-2, 2]], 2, [[1, -1], [-2, 2]]),
    ([[1, 0], [0, -1], [2, 2]], 2, [[1, 0], [0, -1]]),
    ([[0, 0]], 1, [[0, 0]]),
]
for (points, k, expected) in cases {
    let got = kClosest(points, k)
    let pass = sortedPoints(got) == sortedPoints(expected)
    print(pass ? "PASS" : "FAIL", points, k, "→", got, "expected", expected)
}
```
:::

::: Pattern and cue
**Heap of size k, ordered by distance.** The cue is *"the k closest"*: a top-k selection where only the k winners matter, not their order or the order of the losers. Keep the k nearest seen so far in a heap whose top is the *farthest* of them, so the next closer point can replace it in O(log k).
:::

::: Approach
Work with the squared distance, x² + y²: it ranks points exactly as the real distance does and stays a whole number. Go through the points one at a time, adding each to a group of the k nearest so far. When the group grows to k + 1, the farthest member leaves. Keep the group in a max-heap by squared distance so the farthest member is always on top. After the last point, the group is the answer.

Time O(n log k): one push per point and at most one pop, on a heap of at most k + 1 items. Space O(k). Sorting all points by distance and taking the first k is O(n log n) and a sound first answer.
:::

::: Swift solution
```swift
func kClosest(_ points: [[Int]], _ k: Int) -> [[Int]] {
    func squaredDistance(_ point: [Int]) -> Int { point[0] * point[0] + point[1] * point[1] }

    var farthestOnTop = Heap<[Int]>(by: { squaredDistance($0) > squaredDistance($1) })
    for point in points {
        farthestOnTop.push(point)
        if farthestOnTop.count > k {
            _ = farthestOnTop.pop()                 // drop the farthest of the k + 1
        }
    }

    var result: [[Int]] = []
    while let point = farthestOnTop.pop() { result.append(point) }
    return result
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

The comparator is `>` on squared distance: a max-heap, because the point you want to throw out is the farthest one. `squaredDistance` is a nested function that captures nothing, so the escaping closure can call it freely.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, five more (k equal to the number of points, points with negative coordinates only, several points at the same distance inside the cut, points on the axes, a point at the coordinate limit 10,000), and 2,000 random point sets checked against sorting by distance (comparing the multiset of distances, so ties at the cut-off can't cause a false failure).
:::

::: Walk it through
**`[[3, 4], [1, -1], [-2, 2]]`, k = 2** — squared distances 25, 2, 8.

| Point | Squared distance | Heap after push (farthest first) | Over k? | Heap after |
|---|---|---|---|---|
| [3, 4] | 25 | 25 | no | 25 |
| [1, −1] | 2 | 25, 2 | no | 25, 2 |
| [−2, 2] | 8 | 25, 2, 8 | yes, pop [3, 4] | 8, 2 |

Draining the heap gives `[[-2, 2], [1, -1]]`; sorted for the comparison it equals the expected answer.

**`[[0, 0]]`, k = 1** — one push, never over k, one pop when draining. Distance 0 needs no special case.
:::

::: The Swift trap
**Don't reach for `sqrt`.** `(Double(x * x + y * y)).squareRoot()` turns exact integers into floating-point values, so every comparison now carries rounding you'd have to argue is harmless, and each one costs a square root. It buys nothing: the square root keeps the order of non-negative numbers, so the squared distances rank the points identically. Compare `x * x + y * y` as `Int`. At these limits it is at most 2 × 10⁸, nowhere near `Int.max`; if coordinates could reach 3 × 10⁹, the squares would trap on overflow, because Swift's `Int` arithmetic traps instead of wrapping.

And `[[Int]]` has no `.sorted()`: `[Int]` isn't `Comparable`, so the test sorts with `lexicographicallyPrecedes`.
:::

::: What they ask next
- **"Can you do better than O(n log k)?"** → Quickselect on squared distance: partition until the k nearest are in the first k slots. O(n) on average, O(n²) worst case, and it reorders the input.
- **"Points arrive as a stream."** → The heap answer already works on a stream: it only ever holds k points.
- **"Return them nearest first."** → Pop the max-heap into an array and reverse it, or sort the k results: O(k log k) on top.
:::
