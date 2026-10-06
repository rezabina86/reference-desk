---
title: Stack — the idea
summary: How to spot a problem where the most recent unfinished thing is always the next one to deal with, and the two shapes the code takes.
group: Stack
minutes: 8
sources:
- Swift standard library · Array.popLast() | https://developer.apple.com/documentation/swift/array/poplast()
- Swift standard library · Array.removeLast() | https://developer.apple.com/documentation/swift/array/removelast()
---

## When to reach for it

- **Matching pairs** — brackets, tags, "every opener has a closer in the right order".
- **Nesting** — something inside something inside something: `2[a3[b]]`, folders, nested calls.
- **"Evaluate"** an expression written with the operator after its operands.
- **"Next greater"**, "next warmer", "how many days until" — for each item, the first later item that beats it.
- **Undo, back, history** — the last thing done is the first thing undone.
- **"In constant time, also report the minimum"** — a stack that carries extra information per entry.

## The idea in plain words

Think of a stack of plates. You can only put a plate on top, and you can only take the top plate off. Whatever went on last comes off first.

That sounds limiting, but it matches a very common situation: you start something, get interrupted by something smaller, finish the smaller thing, and then go back to exactly where you were. Opening a bracket, then another, then closing: the closer always belongs to the most recent bracket still open. The stack is the list of things you've started and not finished, with the newest on top.

The second shape is a waiting line that only ever looks at its newest member. Walking through daily temperatures, every day joins a pile of "days still waiting for a warmer one". When a warm day arrives, it settles every colder day at the top of the pile at once, then joins the pile itself. Because the colder days get removed as soon as something beats them, the pile always runs from warmest at the bottom to coldest at the top. That is a **monotonic stack**.

## The template in Swift

```swift
// A stack is an array used from one end only.
func stackBasics() {
    var stack: [Int] = []
    stack.append(4)                      // push: O(1) amortised
    stack.append(9)
    let top = stack.last                 // peek: Optional, nil when empty
    let popped = stack.popLast()         // pop: Optional, nil when empty
    _ = (top, popped)
}

/// For each value, the index of the next strictly greater value to its right, or -1.
func nextGreaterIndex(_ values: [Int]) -> [Int] {
    var answer = [Int](repeating: -1, count: values.count)
    var waiting: [Int] = []              // indices still looking; their values never increase bottom to top
    for (index, value) in values.enumerated() {
        while let last = waiting.last, values[last] < value {
            answer[last] = index         // `value` is the first greater one `last` has met
            waiting.removeLast()
        }
        waiting.append(index)
    }
    return answer
}
```

## Variations

- **Match and cancel.** Push openers; a closer must match the top, which is popped. At the end the stack must be empty. → Valid Parentheses.
- **Operand stack.** Push numbers; an operator pops two, combines them and pushes the result. → Evaluate Reverse Polish Notation.
- **Stack of saved context.** Each entry carries more than one value: the value and the minimum so far, or the text built before a `[` and how many times to repeat what comes next. → Min Stack, Decode String.
- **Monotonic stack.** Keep indices whose values only go one way; a new item pops everything it beats and answers their question. → Daily Temperatures.

## Complexity

Push, pop and peek are O(1) (push is amortised: the array occasionally doubles its storage). A single pass that pushes each item once and pops it at most once is O(n) in total, even with a `while` loop inside the `for` — the inner loop can't pop more items than were pushed. Space is O(n) in the worst case, when nothing is ever popped.

## Swift traps

- **There's no `Stack` type, and you don't need one.** `Array` with `append`, `last` and `popLast()` is the stack. Wrapping it in a struct is fine in a design question; in a function it's noise.
- **`removeLast()` traps on an empty array; `popLast()` returns `nil`.** Use `popLast()` whenever the input can be malformed (a closer with nothing open), and `removeLast()` only where emptiness is impossible by construction.
- **Push indices, not values, when you need distances.** The monotonic stack almost always stores positions; the value is one subscript away, the position can't be recovered from the value.
- **Recursion is a hidden stack.** A recursive solution to a nesting problem uses the call stack instead of an array. It's correct, but deep enough input (tens of thousands of levels) can overflow it; the explicit array can't.

## The problems in this topic

- [21 · Valid Parentheses](#/dsa/valid-parentheses) — Easy
- [22 · Min Stack](#/dsa/min-stack) — Medium
- [23 · Evaluate Reverse Polish Notation](#/dsa/evaluate-reverse-polish-notation) — Medium
- [24 · Daily Temperatures](#/dsa/daily-temperatures) — Medium
- [25 · Decode String](#/dsa/decode-string) — Medium
