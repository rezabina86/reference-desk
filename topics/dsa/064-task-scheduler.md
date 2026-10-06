---
title: 54 · Task Scheduler
summary: Given a list of labelled jobs and a rest period that must pass between two jobs with the same label, find the shortest total time to finish them all.
group: Heap
minutes: 25
sources:
- LeetCode 621 · Task Scheduler | https://leetcode.com/problems/task-scheduler/
- Swift language guide · Optional binding in conditions | https://docs.swift.org/swift-book/documentation/the-swift-programming-language/thebasics/#Optional-Binding
---

*Medium · G*

A machine runs jobs, one per time unit. Each job is labelled with a capital letter, and the list may hold the same label many times. After running a job with some label, the machine must let at least n time units pass before running that label again; in between it may run other labels or sit idle. Jobs can run in any order. Return the smallest number of time units, idle ones included, needed to run every job.

| Jobs | n | Answer |
|---|---|---|
| `A A A B B C` | `2` | `7` — `A B C A B · A`, one idle unit |
| `X Y Z` | `3` | `3` — every label runs once, nothing ever waits |
| `Q Q Q Q` | `1` | `7` — `Q · Q · Q · Q`, an idle unit between each pair |

Constraints that matter: up to 10,000 jobs, labels `A`–`Z`, and 0 ≤ n ≤ 100. Trying every order is hopeless; the target is O(m) for m jobs, with a heap or with a short counting argument.

::: Starter code and tests
Neither starter includes a heap: writing one is part of the exercise, or paste the one from the [heap primer](#/dsa/heap).

In an Xcode test target:

```swift
import Testing

struct TaskSchedulerTests {

    @Test(arguments: [
        (["A", "A", "A", "B", "B", "C"], 2, 7),
        (["X", "Y", "Z"], 3, 3),
        (["Q", "Q", "Q", "Q"], 1, 7),
    ] as [([Character], Int, Int)])
    func returnsTheFewestTimeUnitsIncludingIdleOnes(tasks: [Character], n: Int, expected: Int) {
        #expect(leastInterval(tasks, n) == expected)
    }

    // MARK: - Privates
    private func leastInterval(_ tasks: [Character], _ n: Int) -> Int {
        0
    }
}
```

In a playground:

```swift
func leastInterval(_ tasks: [Character], _ n: Int) -> Int {
    0 // your solution
}

let cases: [([Character], Int, Int)] = [
    (["A", "A", "A", "B", "B", "C"], 2, 7),
    (["X", "Y", "Z"], 3, 3),
    (["Q", "Q", "Q", "Q"], 1, 7),
]
for (tasks, n, expected) in cases {
    let got = leastInterval(tasks, n)
    print(got == expected ? "PASS" : "FAIL", String(tasks), n, "→", got, "expected", expected)
}
```
:::

::: Pattern and cue
**Greedy with a max-heap of counts.** The cue is a cooldown between *repeats of the same kind*, plus *"fewest units"*: the labels with the most jobs left are the ones that will force idle time, so they should run as early and as often as the cooldown allows. "Always take the one with the most left, then put it back" is a max-heap.
:::

::: Approach
Count how many jobs each label has; the letters themselves no longer matter, only the counts. Work in rounds of n + 1 time units: within one round no label can repeat, and after it every label used in the round is allowed again. In each round, take the labels with the most jobs left, up to n + 1 of them, run one job of each, and put back the ones that still have jobs. A round costs the full n + 1 units, idle included, unless it was the last one, which costs only the jobs it actually ran.

Time O(m), m the number of jobs: there are at most 26 labels, so each heap operation is O(log 26), a constant, and there is one pop per job run. Space O(1): at most 26 counts. The counting formula below is also O(m) and O(1) and shorter, but the heap version is the one you can derive and explain in the room.
:::

::: Swift solution
```swift
func leastInterval(_ tasks: [Character], _ n: Int) -> Int {
    var countByLabel: [Character: Int] = [:]
    for task in tasks { countByLabel[task, default: 0] += 1 }

    var mostLeftOnTop = Heap<Int>(by: >)
    for count in countByLabel.values { mostLeftOnTop.push(count) }

    var time = 0
    while !mostLeftOnTop.isEmpty {
        var stillLeft: [Int] = []
        var ran = 0
        while ran < n + 1, let count = mostLeftOnTop.pop() {   // check the slot BEFORE popping
            if count > 1 { stillLeft.append(count - 1) }
            ran += 1
        }
        for count in stillLeft { mostLeftOnTop.push(count) }
        time += mostLeftOnTop.isEmpty ? ran : n + 1             // the last round pays no trailing idle
    }
    return time
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

The round ends either when it is full (`ran == n + 1`) or when the heap runs dry; in the second case the rest of the round is idle time, paid for only if more jobs are still waiting.

The counting shortcut, worth knowing once you can explain the heap: the label with the highest count `top` forces `top − 1` full rounds of n + 1 units plus a final round holding every label that ties for that count. If there are so many labels that no idle unit is ever needed, the answer is simply the number of jobs.

```swift
func leastIntervalByCounting(_ tasks: [Character], _ n: Int) -> Int {
    var countByLabel: [Character: Int] = [:]
    for task in tasks { countByLabel[task, default: 0] += 1 }
    let top = countByLabel.values.max() ?? 0
    let labelsAtTop = countByLabel.values.filter { $0 == top }.count
    return max(tasks.count, (top - 1) * (n + 1) + labelsAtTop)
}
```

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, five more (an empty list, n = 0, a single job, many labels so that no idling is needed, two labels tying for the top count), 2,000 small random job lists checked three ways (the heap version, the counting formula, and an exhaustive search over every possible schedule), and 500 larger ones checked heap against formula.
:::

::: Walk it through
**`A A A B B C`, n = 2** — counts 3, 2, 1. Rounds hold n + 1 = 3 units.

| Round | Popped | Put back | Heap after | Units added | Time |
|---|---|---|---|---|---|
| 1 | 3 (A), 2 (B), 1 (C) | 2, 1 | 2, 1 | 3 (full) | 3 |
| 2 | 2 (A), 1 (B) | 1 | 1 | 3 (two jobs + one idle) | 6 |
| 3 | 1 (A) | — | empty | 1 (last round, no trailing idle) | 7 |

Answer 7: `A B C | A B · | A`.

**`X Y Z`, n = 3** — one round of up to four slots; it pops 1, 1, 1, runs out after three, puts nothing back, and the heap is empty, so the round costs 3, not 4. Answer 3.
:::

::: The Swift trap
**The order of the conditions in `while ran < n + 1, let count = mostLeftOnTop.pop()` matters.** Swift evaluates a condition list left to right and stops at the first failure. Written the other way round, `while let count = mostLeftOnTop.pop(), ran < n + 1`, the loop pops one more count when the round is already full, then the `ran` check fails and that popped count is dropped on the floor: a label vanishes with jobs still to run, and the answer comes out too small: `A A B B C C` with n = 1 gives 4 instead of 6. None of the three examples above catches it, because none has more labels than a round has slots. Put the cheap check that has no side effect first, the pop last.

Smaller one: `["A", "B"]` on its own is a `[String]`. The test needs `as [([Character], Int, Int)]` so the literals become `Character`s.
:::

::: What they ask next
- **"Return an actual schedule, not just its length."** → Pop labels instead of bare counts (a heap of `(count, label)` pairs ordered by count), and append each round's labels, then idle markers if the round isn't full and jobs remain.
- **"Jobs must run in the given order; the cooldown still applies."** → No heap: walk the list and keep a dictionary of the earliest time each label may run again; jump the clock forward when a job has to wait. O(m).
- **"Why is the greedy choice right?"** → The label with the most jobs left is the one that can force idle time later; delaying it can only add idle units, never remove them. The counting formula is the same argument written as arithmetic.
:::
