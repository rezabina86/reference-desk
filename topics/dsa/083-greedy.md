---
title: Greedy — the idea
summary: How to solve a problem in one pass by making the choice that looks best right now and never revisiting it, and how to tell when that is safe.
group: Greedy
minutes: 8
sources:
- Wikipedia · Greedy algorithm | https://en.wikipedia.org/wiki/Greedy_algorithm
- Wikipedia · Maximum subarray problem (Kadane's algorithm) | https://en.wikipedia.org/wiki/Maximum_subarray_problem
---

A greedy algorithm walks through the input once and, at every step, takes the choice that is best **right now** — never backtracking, never comparing whole plans. When it works, it's the shortest and fastest solution there is. The hard part isn't the code; it's being sure the local choice can't paint you into a corner.

## When to reach for it

- *"Maximum"* or *"minimum"* of something you can build up item by item: *"largest sum"*, *"fewest jumps"*, *"most you can keep"*.
- *"Can you reach"* the end, *"is it possible"*, with moves that only go forward.
- A **one-pass** target: the constraints say 100,000 items and O(n) is expected.
- After a sort, the order makes one option obviously best: *"earliest ending"*, *"smallest first"*.

## The idea in plain words

Think of driving across a country, stopping for fuel. A sensible rule is: keep going, and at each town ask only "can I make it to the next one?" You don't plan the whole route in advance, and for this problem you don't need to — the best you can do from any town depends only on how much fuel you have, not on how you got there.

That's the condition that makes greedy work: **the past can be summed up in one or two numbers**, and the best next move depends only on those numbers. For the largest sum of a run of numbers, the summary is "the best sum of a run ending right here". For reaching the end of a row of squares, it's "the farthest square I can reach so far". Each new item updates the summary with one simple choice, and the answer falls out at the end.

When greedy fails, it fails quietly: it returns a plausible but wrong number. So say why the local choice is safe — usually "any better plan could be swapped to make this choice without getting worse" — or test it against a brute force on small inputs.

## The template in Swift

```swift
// Shape A — running best: the best answer that ends exactly here either extends the
// previous one or starts fresh at this item. Keep the best seen anywhere.
func bestRun(_ values: [Int], combine: (Int, Int) -> Int) -> Int {
    var endingHere = values[0]                   // assumes at least one value
    var best = values[0]
    for value in values.dropFirst() {
        endingHere = max(value, combine(endingHere, value))   // extend, or restart here
        best = max(best, endingHere)
    }
    return best
}

// Shape B — farthest frontier: walk forward while you're still inside what's reachable,
// pushing the frontier as far as each position allows.
func canReachEnd(_ maxStep: [Int]) -> Bool {
    var frontier = 0
    for (index, step) in maxStep.enumerated() {
        if index > frontier { return false }     // a gap nothing can jump
        frontier = max(frontier, index + step)
    }
    return true
}

// Shape C — sort, then take what fits: order the items so the locally best one comes
// first, then keep each item that is compatible with what you already kept.
func keepGreedily<Item>(_ items: [Item], by key: (Item) -> Int, fits: (Item, Item?) -> Bool) -> [Item] {
    var kept: [Item] = []
    for item in items.sorted(by: { key($0) < key($1) }) where fits(item, kept.last) {
        kept.append(item)
    }
    return kept
}
```

`bestRun(values, combine: +)` is the largest sum of a contiguous run; `keepGreedily` with `key` = end time and `fits` = "starts at or after the last kept end" is interval scheduling.

## Variations

- **Extend or restart.** The best thing ending at position *i* is built from the best ending at *i* − 1, or begins fresh at *i*. Maximum Subarray (Kadane's algorithm).
- **Push a frontier.** Track the farthest point reachable and fail as soon as you stand beyond it. Jump Game.
- **Sort, then pick.** Sort by the key that makes the first choice safe, then keep what fits. Non-overlapping Intervals in the previous topic is this shape.

## Complexity

Shapes A and B are one pass with a couple of variables: **O(n) time, O(1) space**. Shape C pays for the sort: **O(n log n) time**, O(n) for the sorted copy. That's the appeal — dynamic-programming solutions to the same problems are often O(n²) or need O(n) extra memory.

## Swift traps

- **`Int.min` as a starting value can trap.** Starting a running sum at `Int.min` and adding a negative number overflows, and Swift stops the program instead of wrapping around as C does. Start from the first element instead.
- **A range in a `for` loop is fixed when the loop starts.** `for i in 0...reach` doesn't grow when `reach` grows inside the body; the frontier pattern needs a loop over all indices with an explicit check, or a `while`.
- **`values[0]` on an empty array crashes.** Both shapes A and B read the first element or rely on there being one; check the statement's minimum size and say it.
- **`dropFirst()` is a free slice**, not a copy, so `for value in values.dropFirst()` costs nothing extra.

## The problems in this topic

- [70 · Maximum Subarray](#/dsa/maximum-subarray) — Medium
- [71 · Jump Game](#/dsa/jump-game) — Medium
