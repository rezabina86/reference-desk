---
title: Intervals — the idea
summary: How to handle lists of start-and-end pairs — merging, inserting, trimming and counting overlaps — by sorting them first and sweeping once.
group: Intervals
minutes: 8
sources:
- Swift standard library · sorted(by:) | https://developer.apple.com/documentation/swift/array/sorted(by:)
- Wikipedia · Interval scheduling | https://en.wikipedia.org/wiki/Interval_scheduling
---

An interval is a pair: a start and an end. Calendar events, booked time slots, ranges of pages, video segments to keep. Interval problems ask how a list of them overlaps, and almost all of them yield to the same two moves: **sort**, then **sweep** left to right once, keeping a little state.

## When to reach for it

- The input is a list of **`[start, end]` pairs**.
- *"Overlapping"*, *"merge"*, *"insert into"*, *"conflicts"*, *"free time"*.
- *"Meetings"*, *"rooms"*, *"bookings"*, *"how many at the same time"*.
- *"Remove the fewest so that none overlap"* — a sort plus a greedy choice.

## The idea in plain words

Imagine a pile of paper calendar entries thrown on a desk in no order. Asking "which ones clash?" is hard while they're scattered. Lay them out in order of start time and it becomes easy: you only ever have to compare each entry with the ones just before it. If an entry starts before the previous block has ended, they overlap; if it starts after, everything before it is finished business and you never look back.

That's the whole trick. Sorting costs a little up front, and in exchange every later decision only needs to know about the most recent block — its end time — instead of every interval seen so far.

One detail decides half the bugs: do two intervals that **touch** — one ends at 5, the next starts at 5 — overlap? For closed ranges like page spans, yes, and they merge. For meetings, no: a meeting that ends at 10 frees the room for one starting at 10. Every statement in this topic picks one; read for it and say it out loud.

## The template in Swift

```swift
// Sort by start, then sweep, keeping the block currently being built.
// Here: merge every group of overlapping (or touching) intervals.
func mergeSweep(_ intervals: [[Int]]) -> [[Int]] {
    let sorted = intervals.sorted { $0[0] < $1[0] }       // by start; a copy, the input stays as it was
    var result: [[Int]] = []
    for interval in sorted {
        if let last = result.last, interval[0] <= last[1] {   // starts before the open block ends
            result[result.count - 1][1] = max(last[1], interval[1])
        } else {
            result.append(interval)                         // a gap: start a new block
        }
    }
    return result
}

// The other sweep: split intervals into start and end events and count what's open at once.
// Ends are exclusive here, so an interval ending at t doesn't clash with one starting at t.
func maxOpenAtOnce(_ intervals: [[Int]]) -> Int {
    let starts = intervals.map { $0[0] }.sorted()
    let ends = intervals.map { $0[1] }.sorted()
    var open = 0, best = 0, e = 0
    for start in starts {
        while e < ends.count && ends[e] <= start { open -= 1; e += 1 }   // close what has ended
        open += 1
        best = max(best, open)
    }
    return best
}
```

## Variations

- **Merge everything that overlaps.** Sort by start, extend the last block or open a new one. Merge Intervals.
- **Already sorted, add one.** No sort needed: copy the intervals that end before the new one, absorb those that overlap it, copy the rest. Insert Interval, O(n).
- **Keep as many as possible without overlap.** Sort by **end** and always keep the interval that finishes first — it leaves the most room for the rest. Non-overlapping Intervals.
- **How many at once.** Treat starts and ends as separate events and sweep through time, counting what's open. Meeting Rooms II.

## Complexity

The sort dominates: **O(n log n) time**. The sweep after it is O(n), because each interval is looked at once. Space is **O(n)** for the sorted copy and the result. When the input arrives already sorted, as in Insert Interval, the whole thing is O(n).

## Swift traps

- **Parameters are constants.** `intervals.sort { … }` on a function parameter doesn't compile; use `sorted`, which returns a new array, or write `var intervals = intervals` first.
- **`result.last` is read-only.** `result.last![1] = 7` is a compile error ("'last' is a get-only property"). Write through the index: `result[result.count - 1][1] = 7`.
- **No array destructuring.** `let [start, end] = interval` isn't Swift. Read `interval[0]` and `interval[1]`, or map the input into a small `struct Interval { let start: Int; let end: Int }` at the start, which makes the rest of the code read better.
- **No `Heap` in the standard library.** The textbook Meeting Rooms solution uses a min-heap of end times. In Swift the two-sorted-arrays sweep above does the same job with nothing to hand-roll.
- **Index bounds trap.** A loop like `while i < intervals.count && intervals[i][1] < start` must check the bound first; Swift crashes on an out-of-range index rather than reading garbage.

## The problems in this topic

- [66 · Insert Interval](#/dsa/insert-interval) — Medium
- [67 · Merge Intervals](#/dsa/merge-intervals) — Medium
- [68 · Non-overlapping Intervals](#/dsa/non-overlapping-intervals) — Medium
- [69 · Meeting Rooms II](#/dsa/meeting-rooms-ii) — Medium
