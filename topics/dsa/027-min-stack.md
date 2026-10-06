---
title: 22 · Min Stack
summary: Build a stack of integers that can also report its smallest element at any moment, with every operation in constant time.
group: Stack
minutes: 25
sources:
- LeetCode 155 · Min Stack | https://leetcode.com/problems/min-stack/
- The Swift Programming Language · Methods (mutating) | https://docs.swift.org/swift-book/documentation/the-swift-programming-language/methods/
---

*Medium · G*

Design a stack of integers with four operations: push a value, pop the top value, read the top value, and read the smallest value currently in the stack. All four must take constant time — reading the minimum may not scan the stack. You can assume pop, top and minimum are only called when the stack isn't empty.

The tests replay a list of operations — `"push 6"`, `"pop"`, `"top"`, `"min"` — and collect what each `top` and `min` returned.

| Operations | Reads |
|---|---|
| push 6, push 2, push 9, min, pop, pop, min, top | `[2, 6, 6]` — once 2 is popped, the minimum goes back to 6 |
| push 4, push 4, pop, min | `[4]` — a duplicate minimum, popped once; the edge case |
| push -1, push 3, push -5, min, pop, min, top | `[-5, -1, 3]` |

Constraints that matter: up to 30,000 operations, values anywhere in the 32-bit range. Scanning for the minimum on each read is O(n) per read; the target is O(1) for every operation.

::: Starter code and tests
In an Xcode test target:

```swift
import Testing

struct MinStackTests {

    @Test(arguments: [
        (["push 6", "push 2", "push 9", "min", "pop", "pop", "min", "top"], [2, 6, 6]),
        (["push 4", "push 4", "pop", "min"], [4]),
        (["push -1", "push 3", "push -5", "min", "pop", "min", "top"], [-5, -1, 3]),
    ])
    func reportsTopAndMinimumAfterEveryOperation(operations: [String], expected: [Int]) {
        #expect(run(operations) == expected)
    }

    // MARK: - Privates
    /// Replays "push x", "pop", "top" and "min", and returns what each "top" and "min" read.
    private func run(_ operations: [String]) -> [Int] {
        var stack = MinStack()
        var reads: [Int] = []
        for operation in operations {
            let parts = operation.split(separator: " ")
            switch parts[0] {
            case "push": stack.push(Int(parts[1])!)
            case "pop": stack.pop()
            case "top": reads.append(stack.top)
            default: reads.append(stack.minimum)
            }
        }
        return reads
    }
}

private struct MinStack {
    mutating func push(_ value: Int) {}
    mutating func pop() {}
    var top: Int { 0 }
    var minimum: Int { 0 }
}
```

In a playground:

```swift
struct MinStack {
    mutating func push(_ value: Int) {} // your solution
    mutating func pop() {}
    var top: Int { 0 }
    var minimum: Int { 0 }
}

func run(_ operations: [String]) -> [Int] {
    var stack = MinStack()
    var reads: [Int] = []
    for operation in operations {
        let parts = operation.split(separator: " ")
        switch parts[0] {
        case "push": stack.push(Int(parts[1])!)
        case "pop": stack.pop()
        case "top": reads.append(stack.top)
        default: reads.append(stack.minimum)
        }
    }
    return reads
}

let cases: [([String], [Int])] = [
    (["push 6", "push 2", "push 9", "min", "pop", "pop", "min", "top"], [2, 6, 6]),
    (["push 4", "push 4", "pop", "min"], [4]),
    (["push -1", "push 3", "push -5", "min", "pop", "min", "top"], [-5, -1, 3]),
]
for (operations, expected) in cases {
    let got = run(operations)
    print(got == expected ? "PASS" : "FAIL", operations, "→", got, "expected", expected)
}
```
:::

::: Pattern and cue
**Stack of saved context.** The cue is *"retrieve the minimum in constant time"* on a structure that only changes at the top. The minimum below any entry never changes while that entry is on the stack, so each entry can carry "the minimum of everything up to and including me" from the moment it's pushed.
:::

::: Approach
Store pairs instead of plain values: the value, and the smallest value in the stack at the moment it was pushed. Pushing compares the new value with the minimum stored in the current top and keeps the smaller one; on an empty stack the new value is its own minimum. Popping just removes the top pair, and the pair underneath already knows the minimum of what's left — nothing has to be recomputed. Reading the top or the minimum reads one field of the top pair.

Time O(1) for every operation. Space O(n): one extra integer per entry.
:::

::: Swift solution
```swift
struct MinStack {
    private var entries: [(value: Int, minimum: Int)] = []

    mutating func push(_ value: Int) {
        let minimum = entries.last.map { min($0.minimum, value) } ?? value
        entries.append((value, minimum))
    }

    mutating func pop() {
        entries.removeLast()
    }

    var top: Int { entries.last!.value }

    var minimum: Int { entries.last!.minimum }
}
```

The push line is the whole idea: the new entry's minimum is the smaller of its own value and the minimum already stored on top, or just its value when the stack is empty. `removeLast()` and the force unwraps are safe here only because the statement promises no reads on an empty stack — say that out loud.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, three more (a single push read back, a duplicate minimum pushed twice and popped once, a strictly decreasing push then pops), and 2,000 random push/pop sequences checked after every step against a plain array's `last` and `min()`.
:::

::: Walk it through
**push 6, push 2, push 9, min, pop, pop, min, top**

| Operation | Stack (value, minimum), bottom → top | Read |
|---|---|---|
| push 6 | (6, 6) | |
| push 2 | (6, 6) (2, 2) | |
| push 9 | (6, 6) (2, 2) (9, 2) | |
| min | same | 2 |
| pop | (6, 6) (2, 2) | |
| pop | (6, 6) | |
| min | same | 6 |
| top | same | 6 |

Reads `[2, 6, 6]`. After the second pop, nothing is recomputed: the entry for 6 has carried "minimum 6" since it was pushed.

**push 4, push 4, pop, min** — both entries are (4, 4). Popping one leaves (4, 4), so the minimum is still 4. The classic two-stack version, which only pushes onto the minimum stack when a value is *strictly* smaller, breaks exactly here: it records one 4, pops it with the first pop, and then has no minimum at all.
:::

::: The Swift trap
**Naming the property `min` breaks the call to `min` inside the type.** `var min: Int` reads well at the call site, but inside the struct the name `min` now refers to the property, so `min($0.minimum, value)` stops compiling: Swift reports that `min` refers to the member rather than the global function. Write `Swift.min(...)`, or name the property `minimum` as here. The second thing to say: as a struct, `push` and `pop` must be `mutating`, so a stack declared with `let` can't be pushed — that's the value semantics working, not a bug. LeetCode's own template uses a `class`; either is fine if you say why.
:::

::: What they ask next
- **"Use less memory when the minimum rarely changes."** → Keep a second stack that only grows when a value is less than *or equal to* the current minimum, and pop it when the popped value equals its top. The "or equal" is what keeps duplicates correct.
- **"Also support max."** → Store a third field per entry, the maximum so far; the same argument applies.
- **"Can you do it with a single integer of extra state?"** → Yes, by pushing encoded differences from the current minimum, but it overflows on 32-bit extremes unless the differences are stored in a wider type; mention it, don't lead with it.
:::
